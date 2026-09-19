#!/usr/bin/env python3
"""Re-scrape multi-size products (beds, mattresses) for per-size prices."""

import json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

INPUT = "/Users/claw/.openclaw/workspace/bunkbedworld/products.json"

with open(INPUT) as f:
    products = json.load(f)

# Only re-scrape products that mention sizes in name or are beds/mattresses etc
multi_cats = ['Beds', 'Bedrooms', 'Mattresses', 'Bunk Beds', 'Daybeds']
targets = [p for p in products if p['category'] in multi_cats]
print(f"Re-scraping {len(targets)} multi-size products")

def fetch(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urlopen(req, timeout=30)
        html = resp.read().decode('utf-8', errors='replace')
        # Strip HTML and normalize
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        return None

def parse_size_prices(text):
    """Extract per-size prices from Retail Code section.
    Format: Retail Code\nSize: CodeNumber\nSize: CodeNumber"""
    if not text:
        return None
    
    # Find "Retail Code" section
    rc_idx = text.find('Retail Code')
    if rc_idx < 0:
        return None
    
    # Look for "Size: Number" patterns after Retail Code
    section = text[rc_idx:rc_idx + 500]
    
    # Pattern: Word: 5-digit-number
    # Sizes: Queen, King, Twin, Full, Twin/Full (for bunk beds), etc.
    size_patterns = re.findall(r'(Queen|King|Twin|Full|Twin/Full|Queen/King|Twin/Twin|Full/Full|Queen/Queen)\s*:\s*(\d{4,6})', section)
    
    if size_patterns:
        results = {}
        for size, code in size_patterns:
            # Parse the code: remove first and last digit
            digits = code.strip()
            if len(digits) >= 4:
                cost = int(digits[1:-1])
                sell = round(cost * 1.7)
                results[size] = {'cost': cost, 'sell': sell}
        if results:
            return results
    
    # Try generic pattern: any word followed by colon and digits
    generic = re.findall(r'(\w[\w\s/]+?):\s*(\d{4,6})(?:\s|$)', section)
    if generic:
        results = {}
        for size_name, code in generic:
            size_name = size_name.strip()
            if size_name.lower() in ['queen', 'king', 'twin', 'full', 'twin/full', 'queen/king', 'twin/twin', 'full/full', 'queen/queen', 'twin/full bunkbed', 'full bunkbed']:
                digits = code.strip()
                if len(digits) >= 4:
                    cost = int(digits[1:-1])
                    sell = round(cost * 1.7)
                    results[size_name] = {'cost': cost, 'sell': sell}
        if results:
            return results
    
    # Fallback: single Retail Code
    single = re.search(r'Retail Code[:\s]*(\d+)', section)
    if single:
        code = single.group(1)
        if len(code) >= 4:
            cost = int(code[1:-1])
            sell = round(cost * 1.7)
            return {'__single__': {'cost': cost, 'sell': sell}}
    
    return None

urls = [(p['id'], p['page']) for p in targets]
total = len(urls)
start = time.time()

with ThreadPoolExecutor(max_workers=12) as ex:
    futmap = {ex.submit(fetch, url): (pid, url) for pid, url in urls}
    updated_count = 0
    size_count = 0
    
    for i, fut in enumerate(as_completed(futmap), 1):
        pid, url = futmap[fut]
        html_text = fut.result()
        prices = parse_size_prices(html_text) if html_text else None
        
        # Find and update product
        for p in products:
            if p['id'] == pid:
                if prices:
                    p['size_prices'] = prices
                    # Update sell_price to the "single" or first size for backward compat
                    if '__single__' in prices and len(prices) == 1:
                        p['sell_price'] = prices['__single__']['sell']
                        p['cost_price'] = prices['__single__']['cost']
                    updated_count += 1
                    if len(prices) > 1 or '__single__' not in prices:
                        size_count += 1
                break
        
        if i % 30 == 0 or i == total:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  {i}/{total} ({rate:.1f}/s) | multi-size: {size_count}")

elapsed = time.time() - start
print(f"\nDone in {elapsed:.0f}s")
print(f"Updated: {updated_count}")
print(f"Multi-size (multiple entries): {size_count}")

# Clean up __single__ key - flatten it
for p in products:
    sp = p.get('size_prices', {})
    if '__single__' in sp and len(sp) == 1:
        p['sell_price'] = sp['__single__']['sell']
        p['cost_price'] = sp['__single__']['cost']
        del p['size_prices']

with open(INPUT, 'w') as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

# Final stats
with_prices = [p for p in products if p.get('sell_price')]
with_sizes = [p for p in products if p.get('size_prices')]
print(f"\nFinal stats:")
print(f"  Total products: {len(products)}")
print(f"  With sell_price: {len(with_prices)}")
print(f"  With size_prices: {len(with_sizes)}")
print(f"  Total with any price: {len(with_prices) + len(with_sizes)}")
