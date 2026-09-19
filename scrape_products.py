#!/usr/bin/env python3
"""
Scrape all Happy Homes product pages to extract color, material, dimensions, and features.
Uses concurrent.futures with 15 workers for parallel requests.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

INPUT_FILE = "/Users/claw/.openclaw/workspace/bunkbedworld/products.json"
OUTPUT_FILE = "/Users/claw/.openclaw/workspace/bunkbedworld/products.json"

# Load existing products
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f"Loaded {len(products)} products")

def fetch_product_page(url):
    """Fetch a product page and return its HTML text."""
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
        })
        resp = urlopen(req, timeout=30)
        html = resp.read().decode('utf-8', errors='replace')
        return (url, html, None)
    except Exception as e:
        return (url, None, str(e))

def strip_html(html):
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_product_info(html_text):
    """Extract product info from the cleaned page text."""
    info = {
        'color': '',
        'material': '',
        'dimensions': '',
        'description': '',
        'sold_out': False
    }

    if not html_text:
        return info

    # Check if product is sold out
    if re.search(r'Sold\s*out', html_text, re.I):
        info['sold_out'] = True

    # Find the product details area - start from "Item Name" or "Item Number"
    detail_start = None
    for keyword in ['Item Name', 'Item Number']:
        idx = html_text.find(keyword)
        if idx >= 0:
            detail_start = idx
            break

    if detail_start is None:
        return info

    # Get text from detail start to "Facebook" or "Quantity" (end of product info area)
    detail_end = None
    for end_key in ['Facebook', 'Quantity', 'Buy Now', 'socialize']:
        idx = html_text.find(end_key, detail_start)
        if idx >= 0:
            detail_end = idx + 100  # include a bit
            break
    if detail_end is None:
        detail_end = 2000  # just take enough

    detail_text = html_text[detail_start:detail_end].strip()
    detail_text = re.sub(r'\s+', ' ', detail_text)

    # Extract Color
    color_match = re.search(r'Color:\s*([^\d\n][^R]*?)(?=\s*(?:Material|Dimensions|Features|\*{1,3}|Retail Code|Facebook|SKU))', detail_text)
    if color_match:
        color = color_match.group(1).strip()
        # If color is too long, it's probably not right
        if len(color) < 40:
            info['color'] = color

    # Extract Material
    material_match = re.search(r'Material:\s*([^:\n]*?)(?=\s*(?:Color|Dimensions|Features|\*|Retail Code|\-\s))', detail_text)
    if not material_match:
        material_match = re.search(r'Material:\s*([^:\n]+)', detail_text)
    if material_match:
        mat = material_match.group(1).strip()
        if len(mat) < 50:
            info['material'] = mat

    # Extract dimensions - multiple patterns
    dims_parts = []
    for dim_keyword in ['Dimensions:', 'Dimension:', 'Dimensions']:
        # Pattern 1: "Dimensions: value" followed by more dimension lines
        dim_matches = re.finditer(
            r'''(?:Dimensions?:?|(?:Sofa|Loveseat|Chair|Ottoman|Bed|Twin|Full|Queen|King|RAF|LAF|Storage|Trundle|Left|Right))'''
            r'''[:\s]*(\d+\.?\d*["'']?\s*[xX×]\s*\d+\.?\d*["'']?\s*[xX××⁠]\s*\d+\.?\d*["'']?(?:\s*[xX]\s*\d+\.?\d*["'']?)?)|'''
            r'''(\d+["'']?\s*[xX×]\s*\d+["'']?(?:\s*[xX]\s*\d+["'']?)?)''',
            detail_text
        )
        for m in dim_matches:
            val = m.group(0).strip()
            if len(val) > 5 and val not in dims_parts:
                dims_parts.append(val)

    # Also check for dimension lines preceding them
    # Pattern like "63Lx30W" or "87.5\" x 39\" x 41.25\""
    dim_pattern = r'(\d+["\']?\s*[xX×]\s*\d+["\']?(?:\s*[xX×]\s*\d+["\']?)?(?:\s*[xX×]\s*\d+["\']?)?)'
    for m in re.finditer(dim_pattern, detail_text):
        val = m.group(1).strip()
        if len(val) > 5 and val not in dims_parts:
            dims_parts.append(val)

    if dims_parts:
        info['dimensions'] = '; '.join(dims_parts)

    # Extract description/features
    # Collect descriptive lines
    desc_lines = []
    
    # Lines wrapped in ***...*** or *...* that aren't dimensions
    for m in re.finditer(r'\*{1,3}([^*]+)\*{1,3}', detail_text):
        line = m.group(1).strip()
        # Skip if it's just a dimension label
        if re.match(r'^[\d"]+.*[xX×]', line):
            continue
        if line and len(line) > 3 and line not in desc_lines:
            desc_lines.append(line)
    
    # Lines starting with "- " (bullet points)
    for m in re.finditer(r'-\s+([^-].*?)(?=\s*-\s+|\s*(?:Retail Code|Facebook|Quantity|$))', detail_text + ' '):
        line = m.group(1).strip()
        if line and len(line) > 3 and line not in desc_lines:
            # Skip lines that are clearly SKU/Retail/Codes
            if not re.match(r'^(?:Retail Code|SKU|Item Number|Item Name|Color|Material|Dimensions)$', line, re.I):
                desc_lines.append(line)

    # "Features includes" text
    features_match = re.search(r'Features\s+(?:includes|include)?\s*[:\-]?\s*(.+?)(?=\s*(?:Retail Code|Facebook|Quantity|$))', detail_text)
    if features_match:
        feat_text = features_match.group(1).strip()
        if feat_text and len(feat_text) > 5:
            desc_lines.append(feat_text)

    # "Description:" text
    desc_match = re.search(r'Description:\s*(.+?)(?=\s*(?:Dimensions?|Features|Retail Code|Facebook|Quantity|$))', detail_text)
    if desc_match:
        desc_text = desc_match.group(1).strip()
        if desc_text and len(desc_text) > 5:
            desc_lines.append(desc_text)

    # Lines that look like feature descriptions (not labels we already extracted)
    # e.g. "*** Oversized Set***" from the raw text
    # Check for bold/emphasized text between *** markers already covered above
    
    if desc_lines:
        # Deduplicate
        seen = set()
        unique_lines = []
        for line in desc_lines:
            if line.lower() not in seen:
                seen.add(line.lower())
                unique_lines.append(line)
        info['description'] = '\n'.join(unique_lines)

    return info


def process_products():
    """Main processing function."""
    results = {}
    urls = []
    id_to_product = {}
    
    for product in products:
        pid = product['id']
        url = product['page']
        urls.append((pid, url))
        id_to_product[pid] = product

    total = len(urls)
    completed = 0
    failed = 0
    start_time = time.time()

    print(f"\nStarting to scrape {total} product pages with 15 concurrent workers...\n")

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_map = {}
        for pid, url in urls:
            future = executor.submit(fetch_product_page, url)
            future_map[future] = (pid, url)

        for future in as_completed(future_map):
            pid, url = future_map[future]
            url_result, html, error = future.result()

            completed += 1
            if error:
                print(f"[FAIL] {pid} ({completed}/{total}): {error[:60]}")
                failed += 1
            else:
                text = strip_html(html)
                info = extract_product_info(text)
                results[pid] = info

                # Nice progress display
                if completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = total - completed
                    eta = remaining / rate if rate > 0 else 0
                    print(f"[OK] {completed}/{total} in {elapsed:.0f}s ({rate:.1f}/s, ETA {eta:.0f}s)")

    # Update products with extracted data
    updated_count = 0
    for product in products:
        pid = product['id']
        if pid in results:
            info = results[pid]
            had_data = any([info['color'], info['material'], info['dimensions'], info['description']])
            if had_data or info['sold_out']:
                if info['sold_out']:
                    product['sold_out'] = True
                    updated_count += 1
                    print(f"  Sold out: {product.get('name', product['id'])} ({product.get('page', '')})")
                if info['color']:
                    product['color'] = info['color']
                if info['material']:
                    product['material'] = info['material']
                if info['dimensions']:
                    product['dimensions'] = info['dimensions']
                if info['description']:
                    product['description'] = info['description']

    elapsed = time.time() - start_time
    print(f"\n=== COMPLETE ===")
    print(f"Total: {total} | Updated: {updated_count} | Failed: {failed} | Time: {elapsed:.0f}s")
    if total > 0:
        print(f"Rate: {total/elapsed:.1f} pages/sec")

    # Write updated products
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    print(f"Written to {OUTPUT_FILE}")
    return products


if __name__ == '__main__':
    process_products()