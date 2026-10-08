#!/usr/bin/env python3
"""Happy Homes product scraper - fetches product data, images, decodes pricing."""

import json
import math
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
HAPPY_HOMES_BASE = "https://www.happyhomesindustries.com"
IMAGE_DIR = Path("images")
OUTPUT_FILE = "products_new.json"
MARKUP = 1.7

# ── Pricing ─────────────────────────────────────────────────────────────────
def decode_retail_code(code):
    """Decode Happy Homes Retail Code (strip first + last digit)."""
    s = str(code).strip()
    if len(s) < 4:
        raise ValueError(f"Retail code too short: {code}")
    remaining = s[1:-1]
    if not remaining:
        raise ValueError(f"Retail code produced empty cost: {code}")
    return int(remaining)

def calc_selling_price(cost, markup=MARKUP):
    """Calculate website price: ceil(cost * markup)."""
    return math.ceil(cost * markup)

def process_price(retail_code, markup=MARKUP):
    """Full pipeline: retail code -> cost -> selling price."""
    cost = decode_retail_code(retail_code)
    price = calc_selling_price(cost, markup)
    return cost, price

# ── Scraper ──────────────────────────────────────────────────────────────────
import urllib.request

def fetch_page(url):
    """Fetch a URL and return text."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8', errors='replace')

def extract_product_data(url):
    """Scrape a Happy Homes product page and return structured data."""
    html = fetch_page(url)
    
    data = {
        'id': '',
        'name': '',
        'sku': '',
        'supplier_url': url,
        'category': '',
        'department': '',
        'description': '',
        'specifications': '',
        'color': '',
        'material': '',
        'dimensions': '',
        'retail_codes': [],
        'prices': [],
        'from_price': 0,
        'image_urls': [],
        'available': True,
        'status': ''
    }
    
    # Extract product ID from URL
    m = re.search(r'/store/p(\d+)/', url)
    if m:
        data['id'] = f"p{m.group(1)}"
    
    # Extract page title
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m:
        title = m.group(1).strip()
        if ' - ' in title:
            data['name'] = title.split(' - ')[-1]
        else:
            data['name'] = title
    
    # Extract SKU from the product page
    m = re.search(r'<b class="wsite-com-product-title">SKU:</b>\s*<span[^>]*>([^<]+)', html)
    if m:
        data['sku'] = m.group(1).strip()
    
    # Extract Item Number / Item Name
    m = re.search(r'Item (?:Number|Name):\s*([^<]+)', html)
    if m:
        data['sku'] = data['sku'] or m.group(1).strip()
    
    # Check availability
    if 'Sold out' in html or 'Out of Stock' in html:
        data['available'] = False
        data['status'] = 'sold_out'
    
    # Extract description from the paragraph div
    desc_match = re.search(r'<div class="paragraph">(.*?)</div>', html, re.DOTALL)
    if desc_match:
        desc_html = desc_match.group(1)
        # Clean HTML tags
        desc_text = re.sub(r'<[^>]+>', '\n', desc_html)
        desc_text = re.sub(r'\n\s*\n', '\n', desc_text).strip()
        data['description'] = desc_text
    
    # Extract Retail Code(s)
    retail_codes = re.findall(r'Retail Code:\s*(\d+)', html)
    # Also check for multi-line patterns
    if not retail_codes:
        retail_codes = re.findall(r'Retail Code[^:]*:\s*(\d+)', html)
    
    for code_str in retail_codes:
        code = int(code_str)
        try:
            cost, price = process_price(code)
            data['retail_codes'].append({
                'code': code,
                'cost': cost,
                'price': price
            })
            data['prices'].append({
                'label': 'Standard',
                'price': price,
                'retail_code': code,
                'cost': cost
            })
        except ValueError:
            pass
    
    # Extract dimensions
    m = re.search(r'Dimension[s]?:\s*([^<]+)', html)
    if m:
        data['dimensions'] = m.group(1).strip()
    
    # Extract material
    m = re.search(r'Material:\s*([^<]+)', html)
    if m:
        data['material'] = m.group(1).strip()
    
    # Extract color
    m = re.search(r'Color:\s*([^<]+)', html)
    if m:
        data['color'] = m.group(1).strip()
    
    # Extract ALL product images
    # Product images are in form: /uploads/4/0/5/2/40528873/s....jpeg
    img_patterns = re.findall(
        r'(/uploads/4/0/5/2/40528873/[^\s"\'?]+\.(?:jpe?g|png|webp))',
        html
    )
    
    seen = set()
    for img_path in img_patterns:
        if img_path in seen:
            continue
        seen.add(img_path)
        
        # Build full URL - Happy Homes serves from their domain
        full_url = HAPPY_HOMES_BASE + img_path
        
        # Skip non-product images (logo, etc)
        fname = os.path.basename(img_path).lower()
        if 'industries' in fname or 'happy-homes' in fname:
            continue
        if 'magic-edit' in fname or 'img-' in fname:
            continue
            
        data['image_urls'].append(full_url)
    
    # Deduplicate image URLs
    data['image_urls'] = list(dict.fromkeys(data['image_urls']))
    
    # Calculate from price
    if data['prices']:
        data['from_price'] = min(p['price'] for p in data['prices'])
    
    # Extract specifications (everything between description and Retail Code)
    if data['description']:
        lines = data['description'].split('\n')
        spec_lines = [l for l in lines if l.strip() and 'Retail Code' not in l]
        data['specifications'] = '\n'.join(spec_lines)
    
    return data

def download_image(url, dest_path):
    """Download an image if it doesn't exist."""
    if os.path.exists(dest_path):
        return True
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        print(f"  ⚠️  Failed to download {url}: {e}")
        return False

def scrape_product(url, category='', department=''):
    """Scrape a product and download its images."""
    print(f"\n📦 Scraping: {url}")
    data = extract_product_data(url)
    
    data['category'] = category
    data['department'] = department
    
    if not data['available']:
        print(f"  ❌ SOLD OUT - skipping")
        data['available'] = False
        return data
    
    print(f"  Name: {data['name']}")
    print(f"  SKU: {data['sku']}")
    print(f"  Retail Codes: {[rc['code'] for rc in data['retail_codes']]}")
    price_strs = [f'${p["price"]}' for p in data['prices']]
    print(f"  Prices: {price_strs}")
    if data['from_price']:
        print(f"  From: ${data['from_price']}")
    print(f"  Images found: {len(data['image_urls'])}")
    
    # Download images
    downloaded = 0
    for i, img_url in enumerate(data['image_urls']):
        ext = os.path.splitext(urllib.parse.urlparse(img_url).path)[1] or '.jpg'
        safe_name = data['id'] or data['sku'].lower().replace(' ', '-') or f"prod-{i}"
        fname = f"happy-{safe_name}-{i+1}{ext}"
        dest = IMAGE_DIR / fname
        if download_image(img_url, str(dest)):
            downloaded += 1
            # Update image path to local
            data['image_urls'][i] = f"/images/{fname}"
        else:
            data['image_urls'][i] = ''
    
    data['images_downloaded'] = downloaded
    print(f"  Images downloaded: {downloaded}/{len(data['image_urls'])}")
    
    return data

def get_sold_out_status(url):
    """Quick check if a Happy Homes product is sold out."""
    try:
        html = fetch_page(url)
        # Check for sold indicators
        if re.search(r'\bSold out\b', html, re.IGNORECASE):
            return True
        # Also check product page for "Unavailable" in price area
        if 'Unavailable' in html:
            return True
        return False
    except:
        return None  # Uncertain

if __name__ == '__main__':
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    # Test product URLs
    test_products = [
        ('https://www.happyhomesindustries.com/store/p926/B100_Platform-_Queen%2C_King.html',
         'Beds', 'Bed Room'),
    ]
    
    results = []
    for url, cat, dept in test_products:
        data = scrape_product(url, cat, dept)
        results.append(data)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📝 Saved {len(results)} products to {OUTPUT_FILE}")