#!/usr/bin/env python3
"""Fix $0 prices by re-fetching only affected product pages with the improved regex."""
import json, re, urllib.request, time, sys, os

# Load current products
with open('products.json') as f:
    products = json.load(f)

zeros = [p for p in products if p.get('price', 0) == 0]
print(f"Products to fix: {len(zeros)}")

fixed = 0
errors = 0
for i, p in enumerate(zeros):
    url = p.get('page', '')
    if not url:
        continue
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        
        clean_text = re.sub(r'<[^>]+>', ' ', html)
        clean_text = re.sub(r'&nbsp;|\s+', ' ', clean_text).strip()
        
        # First look for Retail Code section
        retail_raw = ""
        rm = re.search(r'Retail\s*Code:(.*?)(?=$)', clean_text, re.IGNORECASE | re.DOTALL)
        if rm:
            retail_raw = rm.group(1).strip()
        
        cost_prices = []
        # Try bed-size-prefixed codes first (in retail_raw)
        for m in re.finditer(r'(?:Queen|King|Full|Twin|CK|Cal\s*King|Twin\s*XL)[^:\n]*:\s*-?\s*(7\d{3,4}7)', retail_raw, re.IGNORECASE):
            code = m.group(1).strip()
            if code[0] == '7' and code[-1] == '7':
                cost_prices.append(int(code[1:-1]))
        
        # Fallback: any 7XXX7 in retail_raw
        if not cost_prices:
            for m in re.finditer(r'(7\d{3,4}7)', retail_raw):
                code = m.group(1)
                if len(code) >= 5 and code[0] == '7' and code[-1] == '7':
                    vc = int(code[1:-1])
                    if 0 < vc < 9999:
                        cost_prices.append(vc)
        
        # Final fallback: search full clean_text
        if not cost_prices:
            for m in re.finditer(r'(7\d{3,4}7)', clean_text):
                code = m.group(1)
                if len(code) >= 5 and code[0] == '7' and code[-1] == '7':
                    vc = int(code[1:-1])
                    if 0 < vc < 9999:
                        cost_prices.append(vc)
        
        if cost_prices:
            cost_price = min(cost_prices)
            raw = cost_price * 1.7
            r = int(round(raw))
            ld = r % 10
            if ld != 9:
                r = r - ld + 9
            if r < 9:
                r = 9
            p['price'] = r
            p['cost_price'] = cost_price
            fixed += 1
            print(f"  [{i+1}/{len(zeros)}] {p['id']}: ${p['price']} (cost ${cost_price})")
        else:
            print(f"  [{i+1}/{len(zeros)}] {p['id']}: STILL NO PRICE FOUND")
            errors += 1
        
    except Exception as e:
        print(f"  [{i+1}/{len(zeros)}] {p['id']}: Error - {e}")
        errors += 1
    
    # Rate limit
    time.sleep(0.3)

print(f"\nDone: {fixed} fixed, {errors} still $0")
with open('products.json', 'w') as f:
    json.dump(products, f, indent=2)
print("products.json saved!")