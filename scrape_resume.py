#!/usr/bin/env python3
"""
Resume scrape: process remaining incomplete products in smaller batches.
"""
import json, re, sys, time, os
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html import unescape

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), 'products.json')
BATCH_SIZE = 40
DELAY = 0.4

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

DIM_PATTERN = re.compile(
    r'(?:'
    r'\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:L|W|D|H|Width|Depth|Height|Deep|Length)\s*\.?\s*)?(?:[xX\u00d7]\s*\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:W|D|H|L|Width|Depth|Height)\s*\.?\s*)?){1,2}'
    r'|'
    r'\d+(?:["\'\u201d\u2033])?\s*(?:L|W|D|H)?\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?(?:\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?)?'
    r')'
)

def is_dim_line(line):
    if not line: return False
    if DIM_PATTERN.search(line): return True
    if re.match(r'^\d+[xX]\d+', line): return True
    return False

def fetch_html(url):
    req = Request(url, headers={'User-Agent': USER_AGENT})
    resp = urlopen(req, timeout=30)
    html = resp.read().decode('utf-8', errors='replace')
    resp.close()
    return html

def extract(html):
    result = {}
    desc_match = re.search(r'<div[^>]*id="wsite-com-product-short-description"[^>]*>.*?<div class="paragraph">(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if not desc_match: return result

    ch = desc_match.group(1)
    clean = re.sub(r'<br\s*/?>', '\n', ch)
    clean = re.sub(r'</p>', '\n', clean)
    clean = re.sub(r'</li>', '\n', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = unescape(clean)
    lines = [l.strip().replace('\u200b','') for l in clean.split('\n') if l.strip()]
    if not lines: return result

    for label, key in [('Item Name', 'item_name'), ('Color', 'color'), ('Material', 'material')]:
        for line in lines:
            m = re.search(r'^{}:\s*(.*)$'.format(label), line, re.IGNORECASE)
            if m and m.group(1).strip(): result[key] = m.group(1).strip(); break

    dim_start = None
    dim_same = None
    for i, line in enumerate(lines):
        m = re.search(r'^(?:Dimensions?):\s*(.*)$', line, re.IGNORECASE)
        if m:
            dim_start = i
            val = m.group(1).strip()
            if val: dim_same = val
            break

    def collect_from(start_idx):
        dims, desc, in_desc = [], [], False
        for line in lines[start_idx+1:]:
            if re.search(r'^Retail Code', line, re.IGNORECASE): break
            if not line: continue
            if not in_desc:
                if is_dim_line(line): dims.append(line); continue
                if re.match(r'^\d+[xX]\d+', line): dims.append(line); continue
                in_desc = True; desc.append(line)
            else: desc.append(line)
        return dims, desc

    if dim_start is not None and dim_same is None:
        dims, desc = collect_from(dim_start)
        if dims: result['dimensions'] = '\n'.join(dims)
        if desc: result['description'] = '\n'.join(desc)
    elif dim_same:
        result['dimensions'] = dim_same

    if 'dimensions' not in result and 'description' not in result:
        last_label = -1
        for i, line in enumerate(lines):
            if re.search(r'^(?:Item Name|Color|Material):', line, re.IGNORECASE): last_label = i
        if last_label >= 0:
            dims, desc = collect_from(last_label)
            if dims: result['dimensions'] = '\n'.join(dims)
            if desc: result['description'] = '\n'.join(desc)

    return result

def update_product(p, details):
    changed = False
    for field, key in [('color','color'),('material','material'),('dimensions','dimensions'),('description','description')]:
        if key in details and details[key]:
            existing = p.get(field, '')
            if not existing or not str(existing).strip():
                p[field] = details[key]
                changed = True
    return changed

with open(PRODUCTS_FILE) as f:
    data = json.load(f)
products = data if isinstance(data, list) else data['products']

incomplete = []
for i, p in enumerate(products):
    for field in ['description','dimensions','color','material']:
        val = p.get(field)
        if not val or str(val).strip() == '':
            incomplete.append(i); break

total = len(incomplete)
print(f'Total: {len(products)}, Incomplete: {total}')

if not incomplete:
    print('All done!')
    sys.exit(0)

batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE
all_updated = 0
fetches = 0

for batch_num in range(batch_count):
    batch_start = batch_num * BATCH_SIZE
    batch_end = min(batch_start + BATCH_SIZE, total)
    batch_indices = incomplete[batch_start:batch_end]
    print(f'\n--- Batch {batch_num+1}/{batch_count} (idx {batch_start+1}-{batch_end}) ---')
    
    batch_results = []
    for idx in batch_indices:
        p = products[idx]
        url = p.get('page','')
        if not url: print(f'  [{idx}] No URL'); continue
        name = p.get('name','?')
        print(f'  [{idx}] {name[:50]}', end=' ')
        sys.stdout.flush()
        try:
            html = fetch_html(url); fetches += 1
            details = extract(html)
            got = [k for k in ['color','material','dimensions','description'] if k in details]
            print(f'-> {", ".join(got) if got else "nothing"}')
            batch_results.append((idx, details))
        except Exception as e:
            print(f'-> Error: {e}')
            batch_results.append((idx, {}))
        time.sleep(DELAY)

    batch_upd = sum(1 for idx, d in batch_results if update_product(products[idx], d))
    all_updated += batch_upd
    with open(PRODUCTS_FILE, 'w') as f: json.dump(data, f, indent=2)
    
    remaining = 0
    for p in products:
        for f in ['description','dimensions','color','material']:
            if not p.get(f,'').strip(): remaining += 1; break
    print(f'  Updated: {batch_upd}/{len(batch_indices)}, Remaining: {remaining}/{total}, Fetches: {fetches}')

print(f'\n=== DONE: Updated {all_updated}, Remaining: {remaining} ===')