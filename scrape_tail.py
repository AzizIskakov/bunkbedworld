#!/usr/bin/env python3
"""Process the 51 tail products (731-789) that haven't been fetched."""
import json, re, sys, time
from urllib.request import urlopen, Request
from html import unescape

PRODUCTS_FILE = '/Users/claw/.openclaw/workspace/bunkbedworld/products.json'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
DELAY = 0.4

DIM_PATTERN = re.compile(
    r'(?:\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:L|W|D|H|Width|Depth|Height|Deep|Length)\s*\.?\s*)?'
    r'(?:[xX\u00d7]\s*\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:W|D|H|L|Width|Depth|Height)\s*\.?\s*)?){1,2}'
    r'|'
    r'\d+(?:["\'\u201d\u2033])?\s*(?:L|W|D|H)?\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?'
    r'(?:\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?)?)'
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
    m = re.search(r'<div[^>]*id="wsite-com-product-short-description"[^>]*>.*?<div class="paragraph">(.*?)</div>',
                  html, re.DOTALL | re.IGNORECASE)
    if not m: return result
    ch = m.group(1)
    clean = re.sub(r'<br\s*/?>', '\n', ch)
    clean = re.sub(r'</p>', '\n', clean)
    clean = re.sub(r'</li>', '\n', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = unescape(clean)
    lines = [l.strip().replace('\u200b', '') for l in clean.split('\n') if l.strip()]
    if not lines: return result

    for label, key in [('Item Name', 'item_name'), ('Color', 'color'), ('Material', 'material')]:
        for line in lines:
            m2 = re.search(r'^{}:\s*(.*)$'.format(label), line, re.IGNORECASE)
            if m2 and m2.group(1).strip():
                result[key] = m2.group(1).strip()
                break

    dim_start = None
    dim_same = None
    for i, line in enumerate(lines):
        m2 = re.search(r'^(?:Dimensions?):\s*(.*)$', line, re.IGNORECASE)
        if m2:
            dim_start = i
            v = m2.group(1).strip()
            dim_same = v if v else None
            break

    def collect_from(si):
        dims, desc, in_desc = [], [], False
        for ln in lines[si+1:]:
            if re.search(r'^Retail Code', ln, re.IGNORECASE): break
            if not ln: continue
            if not in_desc:
                if is_dim_line(ln) or re.match(r'^\d+[xX]\d+', ln):
                    dims.append(ln)
                    continue
                in_desc = True
                desc.append(ln)
            else:
                desc.append(ln)
        return dims, desc

    if dim_start is not None and dim_same is None:
        dims, desc = collect_from(dim_start)
        if dims: result['dimensions'] = '\n'.join(dims)
        if desc: result['description'] = '\n'.join(desc)
    elif dim_same:
        result['dimensions'] = dim_same

    if 'dimensions' not in result and 'description' not in result:
        last_label = -1
        for i, ln in enumerate(lines):
            if re.search(r'^(?:Item Name|Color|Material):', ln, re.IGNORECASE):
                last_label = i
        if last_label >= 0:
            dims, desc = collect_from(last_label)
            if dims: result['dimensions'] = '\n'.join(dims)
            if desc: result['description'] = '\n'.join(desc)

    return result

# Load
with open(PRODUCTS_FILE) as f:
    data = json.load(f)
products = data if isinstance(data, list) else data['products']

indices = list(range(731, 790))
updated = 0
fetches = 0

for i, idx in enumerate(indices):
    p = products[idx]
    name = p.get('name', '?')
    url = p.get('page', '')
    print(f'  [{i+1}/{len(indices)}] [{idx}] {name[:55]}', end=' ')
    sys.stdout.flush()

    if not url:
        print('-> No URL')
        continue

    try:
        html = fetch_html(url)
        fetches += 1
        details = extract(html)
        got = [k for k in ['color', 'material', 'dimensions', 'description'] if k in details]
        label = ', '.join(got) if got else 'nothing'
        print(f'-> {label}')

        changed = False
        for field, key in [('color', 'color'), ('material', 'material'),
                           ('dimensions', 'dimensions'), ('description', 'description')]:
            if key in details and details[key]:
                existing = p.get(field, '')
                if not existing or str(existing).strip() in ('', 'None'):
                    p[field] = details[key]
                    changed = True
        if changed:
            updated += 1
    except Exception as e:
        print(f'-> Error: {e}')

    time.sleep(DELAY)

with open(PRODUCTS_FILE, 'w') as f:
    json.dump(data, f, indent=2)

remaining = 0
for p in products:
    for f in ['description', 'dimensions', 'color', 'material']:
        if not p.get(f) or str(p.get(f, '')).strip() in ('', 'None'):
            remaining += 1
            break

print(f'\n=== COMPLETE ===')
print(f'Fetched: {fetches}')
print(f'Updated products: {updated}')
print(f'Remaining incomplete: {remaining}/{len(products)}')