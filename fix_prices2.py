#!/usr/bin/env python3
"""Fix $0 prices — uses improved pricing extraction strategy."""
import json, re, urllib.request, time, sys

with open('products.json') as f:
    products = json.load(f)

zeros = [p for p in products if p.get('price', 0) == 0]
print(f"Products to fix: {len(zeros)}", flush=True)

fixed = 0
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
        
        cost_prices = []
        
        # Strategy 1: bed-size prefixed
        for m in re.finditer(r'(?:Queen|King|Full|Twin|CK|Cal\s*King|Twin\s*XL)[^:\n]*:\s*-?\s*(7\d{3,4}7)', clean_text, re.IGNORECASE):
            code = m.group(1).strip()
            if len(code) >= 5 and code[0] == '7' and code[-1] == '7':
                vc = int(code[1:-1])
                if 0 < vc < 9999:
                    cost_prices.append(vc)
        
        # Strategy 2: Retail Code: marker
        if not cost_prices:
            m = re.search(r'Retail\s*Code[:\s]+(7\d+?7)\b', clean_text, re.IGNORECASE)
            if m:
                code = m.group(1).strip()
                if len(code) >= 5 and code[0] == '7' and code[-1] == '7':
                    vc = int(code[1:-1])
                    if 0 < vc < 9999:
                        cost_prices.append(vc)
        
        # Strategy 3: fallback (filter > 100)
        if not cost_prices:
            for m in re.finditer(r'(7\d{3,4}7)', clean_text):
                code = m.group(1)
                if len(code) >= 5 and code[0] == '7' and code[-1] == '7':
                    vc = int(code[1:-1])
                    if 100 < vc < 9999:
                        cost_prices.append(vc)
        
        if cost_prices:
            cp = min(cost_prices)
            r = int(round(cp * 1.7))
            ld = r % 10
            if ld != 9:
                r = r - ld + 9
            if r < 9: r = 9
            p['price'] = r
            fixed += 1
            print(f"  [{i+1}/{len(zeros)}] {p['id']}: cost ${cp} -> sell ${r}", flush=True)
        else:
            print(f"  [{i+1}/{len(zeros)}] {p['id']}: STILL NO PRICE", flush=True)
        
        if (i+1) % 20 == 0:
            with open('products.json', 'w') as f:
                json.dump(products, f, indent=2)
            print(f"  Saved at {i+1}/{len(zeros)} (fixed={fixed})", flush=True)
        
    except Exception as e:
        error_msg = str(e)[:80]
        print(f"  [{i+1}/{len(zeros)}] {p['id']}: Error - {error_msg}", flush=True)
    
    time.sleep(0.25)

with open('products.json', 'w') as f:
    json.dump(products, f, indent=2)
print(f"\nDone: {fixed} fixed out of {len(zeros)}", flush=True)