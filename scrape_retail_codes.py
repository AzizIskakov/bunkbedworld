#!/usr/bin/env python3
"""Scrape Retail Code from each product page and calculate prices."""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

INPUT = "/Users/claw/.openclaw/workspace/bunkbedworld/products.json"

with open(INPUT) as f:
    products = json.load(f)

print(f"Loaded {len(products)} products")

def fetch(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urlopen(req, timeout=30)
        html = resp.read().decode('utf-8', errors='replace')
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        # Find Retail Code
        m = re.search(r'Retail Code[:\s]*(\d+)', text)
        if m:
            return m.group(1)
        return None
    except:
        return None

def parse_price(retail_code):
    """Extract cost from retail code. Rule: between first and last digit is the price."""
    if not retail_code:
        return None
    digits = retail_code.strip()
    if len(digits) <= 3:
        # Short code - it IS the price
        try:
            return int(digits)
        except:
            return None
    # Remove first and last digit, what remains is the price
    # E.g., "77997" -> "799" -> $799
    mid = digits[1:-1]
    if mid:
        try:
            return int(mid)
        except:
            return None
    return None

urls = [(p['id'], p['page']) for p in products]
total = len(urls)
results = {}
start = time.time()

with ThreadPoolExecutor(max_workers=15) as ex:
    futmap = {ex.submit(fetch, url): (pid, url) for pid, url in urls}
    for i, fut in enumerate(as_completed(futmap), 1):
        pid, url = futmap[fut]
        code = fut.result()
        results[pid] = code
        if i % 100 == 0:
            print(f"  {i}/{total} ({i/time.time()-start:.1f}/s)")

updated = 0
for p in products:
    pid = p['id']
    code = results.get(pid)
    if code:
        cost = parse_price(code)
        if cost:
            p['cost_price'] = cost
            p['sell_price'] = round(cost * 1.7)
            updated += 1

elapsed = time.time() - start
print(f"\nDone in {elapsed:.0f}s | Found codes: {sum(1 for c in results.values() if c)} | Prices calculated: {updated}")
print(f"Total entries with prices: {len([p for p in products if p.get('sell_price')])}")

with open(INPUT, 'w') as f:
    json.dump(products, f, indent=2, ensure_ascii=False)
print("Saved to products.json")
