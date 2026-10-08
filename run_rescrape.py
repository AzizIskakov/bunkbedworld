#!/usr/bin/env python3
"""Fast rescrape: fetch Happy Homes product pages, extract data + pricing, skip image downloads."""

import json, re, sys, time, os, math
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from html import unescape

HAPPY_BASE = "https://www.happyhomesindustries.com"
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
PRODUCTS_FILE = 'products.json'
INVENTORY_FILE = 'happy_homes_inventory.json'

# ── Pricing ──────────────────────────────────────────────────────────────────
def decode_retail_code(code):
    s = str(code).strip()
    remaining = s[1:-1]
    return int(remaining)

def calc_selling_price(cost):
    return math.ceil(cost * 1.7)

# ── Helpers ──────────────────────────────────────────────────────────────────
def fetch_html(url, retries=3):
    for attempt in range(retries):
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            resp = urlopen(req, timeout=30)
            html = resp.read().decode('utf-8', errors='replace')
            resp.close()
            return html
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ❌ Failed: {e}")
                return None
            time.sleep(2 ** attempt)

def extract_product_id(url):
    m = re.search(r'/store/p(\d+)/', url)
    return f"p{m.group(1)}" if m else ""

def extract_title(html):
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m:
        name = unescape(m.group(1).strip())
        name = re.sub(r'\s*[-–|]\s*Happy Homes.*$', '', name, re.IGNORECASE).strip()
        return name
    return ""

def extract_retail_codes(html):
    """Extract all Retail Code numbers from HTML."""
    codes = []
    # Direct "Retail Code: XXXXX"
    for m in re.finditer(r'Retail Code[^:]*:\s*(\d+)', html):
        code_str = m.group(1)
        if code_str.startswith('7') and len(code_str) >= 4:
            codes.append(code_str)
    return codes

def extract_description(html):
    """Extract description fields."""
    result = {'color': '', 'material': '', 'dimensions': '', 'description': ''}
    
    # Find product description div
    m = re.search(r'<div class="paragraph">(.*?)</div>', html, re.DOTALL)
    if not m:
        return result
    
    text = re.sub(r'<br\s*/?>', '\n', m.group(1))
    text = re.sub(r'</(?:p|li|div)>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    color = ''
    material = ''
    dimensions = []
    desc_lines = []
    
    for line in lines:
        cm = re.match(r'^Color:\s*(.+)', line, re.IGNORECASE)
        if cm: color = cm.group(1).strip(); continue
        mm = re.match(r'^Material:\s*(.+)', line, re.IGNORECASE)
        if mm: material = mm.group(1).strip(); continue
        dm = re.match(r'^Dimensions?:?\s*(.*)', line, re.IGNORECASE)
        if dm:
            if dm.group(1).strip():
                dimensions.append(dm.group(1).strip())
            continue
        if dimensions and re.match(r'^(?:Queen|King|Twin|Full|\d+)', line, re.IGNORECASE):
            dimensions.append(line)
            continue
        if dimensions and (line.startswith('-') or line.startswith('•')):
            dimensions.append(line)
            continue
        desc_lines.append(line)
    
    result['color'] = color
    result['material'] = material
    result['dimensions'] = '\n'.join(dimensions) if dimensions else ''
    result['description'] = '\n'.join(desc_lines)
    return result

def extract_images(html):
    """Extract product image URLs (don't download, just record)."""
    urls = []
    for m in re.finditer(r'(/uploads/[^"\'?\s]+\.(?:jpe?g|png|webp))', html):
        url = HAPPY_BASE + m.group(1)
        fname = os.path.basename(m.group(1)).lower()
        if 'industries' in fname or 'happy-homes' in fname or 'magic-edit' in fname:
            continue
        urls.append(url)
    # Dedupe
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

def is_sold_out(html):
    return bool(re.search(r'\bSold out\b', html, re.IGNORECASE)) or 'Unavailable' in html

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("🚀 BunkBedWorld Fast Rescrape")
    print("=" * 50)
    
    # Load existing products
    existing = {}
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE) as f:
            for p in json.load(f):
                existing[p['id']] = p
    
    # Load URLs from inventory tracker
    with open(INVENTORY_FILE) as f:
        inventory = json.load(f)
    
    urls = list(inventory.get('current_urls', []))
    print(f"📦 Products in inventory: {len(urls)}")
    print(f"📦 Existing products.json: {len(existing)}")
    
    special_ids = ['p1838', 'p790', 'p548', 'b0001']
    
    results = []
    processed = 0
    failed = 0
    sold_out = 0
    
    for url in urls:
        pid = extract_product_id(url)
        if not pid:
            processed += 1
            continue
        
        # Preserve special BBW items - keep existing data
        if pid in special_ids and pid in existing:
            results.append(existing[pid])
            processed += 1
            print(f"  🛡️ Preserved special item: {pid}")
            continue
        
        print(f"  [{processed+1}/{len(urls)}] {pid}", end='', flush=True)
        
        html = fetch_html(url)
        if not html:
            failed += 1
            # Keep existing data if we have it
            if pid in existing:
                results.append(existing[pid])
                print(f" → kept existing")
            else:
                print(f" → ❌ failed")
            processed += 1
            continue
        
        if is_sold_out(html):
            sold_out += 1
            print(f" → sold out")
            processed += 1
            continue
        
        name = extract_title(html)
        if not name:
            name = existing.get(pid, {}).get('name', pid)
        
        # Extract pricing
        prices = []
        codes = extract_retail_codes(html)
        for code_str in codes:
            try:
                cost = decode_retail_code(code_str)
                price = calc_selling_price(cost)
                prices.append(price)
            except (ValueError, IndexError):
                pass
        
        # If no retail codes found, try to keep existing price
        if not prices:
            if pid in existing and existing[pid].get('price', 0) > 0:
                price = existing[pid]['price']
                print(f" → kept existing price ${price}", end='', flush=True)
            else:
                price = 0
                print(f" → ⚠️  no price", end='', flush=True)
        else:
            price = min(prices)
        
        desc_data = extract_description(html)
        img_urls = extract_images(html)
        
        # Map existing image paths
        images = []
        if pid in existing:
            existing_imgs = existing[pid].get('images', [existing[pid].get('image', '')])
            for img in existing_imgs:
                if img:
                    images.append(img)
        
        # Determine category from URL
        category = 'Accessories'
        cat_map = {
            '/c24/': 'Sleepers & Futons', '/c23/': 'Stationary Sofa & Loveseats',
            '/c21/': 'Stationary Sectionals', '/c19/': 'Reclining Sofa & Loveseats',
            '/c32/': 'Reclining Sectionals', '/c10/': 'Recliners & Lift Chairs',
            '/c14/': 'Occasional Tables', '/c11/': 'TV Stands',
            '/c22/': 'Accessories', '/c25/': 'Office & Bookcase',
            '/c30/': 'Beds', '/c7/': 'Bedrooms',
            '/c31/': 'Daybeds', '/c17/': 'Mattresses',
            '/c29/': 'Vanities & Mirrors', '/c8/': 'Dining Rooms',
            '/c28/': 'Barstools',
        }
        for pat, cat in cat_map.items():
            if pat in url:
                category = cat
                break
        
        product = {
            'id': pid,
            'name': name,
            'image': images[0] if images else '',
            'page': url,
            'category': category,
            'color': desc_data['color'],
            'material': desc_data['material'],
            'dimensions': desc_data['dimensions'],
            'description': desc_data['description'],
            'vendor': 'Happy Homes',
            'price': price,
        }
        if len(images) > 1:
            product['images'] = images
        
        results.append(product)
        print(f" → ${price}")

        
        processed += 1
        time.sleep(0.2)  # Be nice to server
    
    # Sort results by ID for consistency
    results.sort(key=lambda p: p['id'])
    
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ Complete!")
    print(f"  Total processed: {processed}")
    print(f"  Products saved:  {len(results)}")
    print(f"  Failed:          {failed}")
    print(f"  Sold out:        {sold_out}")
    print(f"  Special kept:    {len([r for r in results if r['id'] in special_ids])}")
    print(f"  Saved to:        {PRODUCTS_FILE}")

if __name__ == '__main__':
    main()