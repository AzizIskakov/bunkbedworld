#!/usr/bin/env python3
"""
Scrape Happy Homes product pages to fill in missing fields.
Uses urllib for direct HTML fetch, regex for extraction.
"""
import json, re, sys, time, os
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html import unescape

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), 'products.json')
BATCH_SIZE = 50
DELAY = 0.5

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Dimension pattern: lines containing measurements
DIM_PATTERN = re.compile(
    r'(?:'
    # Standard: 72"L x 34" x 37H
    r'\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:L|W|D|H|Width|Depth|Height|Deep|Length)\s*\.?\s*)?(?:[xX\u00d7]\s*\d+(?:\.\d+)?["\'\u201d\u2033]?\s*(?:(?:W|D|H|L|Width|Depth|Height)\s*\.?\s*)?){1,2}'
    r'|'
    # Compact: 63Lx30W or 63x57x36H
    r'\d+(?:["\'\u201d\u2033])?\s*(?:L|W|D|H)?\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?(?:\s*[xX\u00d7]\s*\d+(?:["\'\u201d\u2033])?\s*(?:W|D|H|L)?)?'
    r'|'
    # Width x Depth x Height word format
    r'(?:Width|Depth|Height|Length|Deep)\s*:?\s*\d+(?:\.\d+)?["\'\u201d\u2033]?'
    r')'
)


def is_dimension_line(line):
    """Check if a line looks like a dimension/measurement."""
    return bool(DIM_PATTERN.search(line))


def fetch_html(url):
    """Fetch raw HTML from a product page URL."""
    req = Request(url, headers={'User-Agent': USER_AGENT})
    resp = urlopen(req, timeout=30)
    html = resp.read().decode('utf-8', errors='replace')
    resp.close()
    return html


def extract_product_details(html):
    """Extract structured fields from Happy Homes product page HTML."""
    result = {}

    # Extract page title
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if m:
        result['page_title'] = unescape(m.group(1).strip())

    # Find the product description section
    desc_match = re.search(
        r'<div[^>]*id="wsite-com-product-short-description"[^>]*>.*?<div class="paragraph">(.*?)</div>',
        html, re.DOTALL | re.IGNORECASE
    )

    if not desc_match:
        return result

    content_html = desc_match.group(1)

    # Extract clean text lines from the paragraph
    # Each <p> becomes a line, each <li> becomes a line
    clean_text = re.sub(r'<br\s*/?>', '\n', content_html)
    clean_text = re.sub(r'</p>', '\n', clean_text)
    clean_text = re.sub(r'</li>', '\n', clean_text)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = unescape(clean_text)

    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    if not lines:
        return result

    result['lines'] = lines  # for debugging

    # Remove zero-width spaces
    lines = [l.replace('\u200b', '') for l in lines]

    # Extract labeled fields
    for label, key in [('Item Name', 'item_name'), ('Color', 'color'), ('Material', 'material')]:
        for line in lines:
            m = re.search(r'^{}:\s*(.*)$'.format(label), line, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val:
                    result[key] = val
                break

    # Find Dimensions block
    dim_start_idx = None
    dim_value_line = False
    for i, line in enumerate(lines):
        m = re.search(r'^(?:Dimensions?):\s*(.*)$', line, re.IGNORECASE)
        if m:
            dim_start_idx = i
            dim_value = m.group(1).strip()
            if dim_value:
                # Value is on the same line
                result['dimensions'] = dim_value
                dim_value_line = True
            break

    # Find description content (everything between last known label and Retail Code)
    # This handles pages without explicit 'Dimensions:' label
    def collect_content_after(start_idx):
        """Collect content lines from start_idx until Retail Code."""
        dim_lines = []
        desc_lines = []
        in_desc = False
        for line in lines[start_idx + 1:]:
            if re.search(r'^Retail Code', line, re.IGNORECASE):
                break
            if not line:
                continue
            if not in_desc:
                if is_dimension_line(line):
                    dim_lines.append(line)
                    continue
                if re.match(r'^\d+[xX]\d+', line):
                    dim_lines.append(line)
                    continue
                in_desc = True
                desc_lines.append(line)
            else:
                desc_lines.append(line)
        return dim_lines, desc_lines

    # Collect dimension lines and description lines
    if dim_start_idx is not None and not dim_value_line:
        dim_lines, desc_lines = collect_content_after(dim_start_idx)
        if dim_lines:
            result['dimensions'] = '\n'.join(dim_lines)
        if desc_lines:
            result['description'] = '\n'.join(desc_lines)

    # If no Dimensions label found but we have Color/Material, collect description after last known label
    if 'dimensions' not in result and 'description' not in result:
        # Find the last label index (Item Name, Color, or Material)
        last_label_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'^(?:Item Name|Color|Material):', line, re.IGNORECASE):
                last_label_idx = i
        if last_label_idx >= 0:
            dim_lines, desc_lines = collect_content_after(last_label_idx)
            if dim_lines:
                result['dimensions'] = '\n'.join(dim_lines)
            if desc_lines:
                result['description'] = '\n'.join(desc_lines)

    # Also try to extract name from <h1> or product name section
    for pat in [
        r'<h1[^>]*class="wsite-com-title"[^>]*>(.*?)</h1>',
        r'<div[^>]*id="wsite-com-product-title"[^>]*>(.*?)</div>',
    ]:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            val = unescape(re.sub(r'<[^>]+>', '', m.group(1)).strip())
            if val:
                result['product_name'] = val
                break

    return result


def update_product(p, details):
    """Update a single product with extracted data. Returns True if changed."""
    changed = False
    for field, key in [('color', 'color'), ('material', 'material'),
                       ('dimensions', 'dimensions'), ('description', 'description')]:
        if key in details and details[key]:
            existing = p.get(field, '')
            if not existing or not str(existing).strip():
                p[field] = details[key]
                changed = True
    return changed


def save_products(data):
    """Save products to JSON file."""
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def count_incomplete(products):
    """Count products missing any required fields."""
    count = 0
    for p in products:
        for field in ['description', 'dimensions', 'color', 'material']:
            val = p.get(field)
            if not val or str(val).strip() == '':
                count += 1
                break
    return count


def main():
    with open(PRODUCTS_FILE) as f:
        data = json.load(f)
    products = data if isinstance(data, list) else data['products']

    # Build incomplete index list
    incomplete = []
    for i, p in enumerate(products):
        for field in ['description', 'dimensions', 'color', 'material']:
            val = p.get(field)
            if not val or str(val).strip() == '':
                incomplete.append(i)
                break

    total = len(incomplete)
    print(f'Total products: {len(products)}')
    print(f'Products needing scrape: {total}')
    print(f'Complete products: {len(products) - total}')

    if not incomplete:
        print('All products complete!')
        return

    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE
    all_updated = 0
    fetch_count = 0

    for batch_num in range(batch_count):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch_indices = incomplete[batch_start:batch_end]

        print(f'\n--- Batch {batch_num + 1}/{batch_count} (indices {batch_start + 1}-{batch_end}) ---')

        batch_results = []
        for idx in batch_indices:
            p = products[idx]
            url = p.get('page', '')
            if not url:
                print(f'  [{idx}] No URL -> skip')
                continue

            name = p.get('name', '?')
            print(f'  [{idx}] {name[:50]}', end=' ')
            sys.stdout.flush()

            try:
                html = fetch_html(url)
                fetch_count += 1
                details = extract_product_details(html)

                if not details:
                    print('-> (no data)')
                    batch_results.append((idx, {}))
                    continue

                # Check what we extracted
                got = []
                for key in ['color', 'material', 'dimensions', 'description']:
                    if key in details:
                        got.append(key)
                print(f'-> {", ".join(got) if got else "nothing"}')
                batch_results.append((idx, details))

            except HTTPError as e:
                print(f'-> HTTP {e.code}')
                batch_results.append((idx, {}))
            except Exception as e:
                print(f'-> Error: {e}')
                batch_results.append((idx, {}))
                import traceback
                traceback.print_exc()

            time.sleep(DELAY)

        # Update products
        batch_updated = 0
        for idx, details in batch_results:
            if update_product(products[idx], details):
                batch_updated += 1

        all_updated += batch_updated
        print(f'  Updated: {batch_updated} in this batch')
        save_products(data)
        remaining = count_incomplete(products)
        print(f'  Remaining incomplete: {remaining}/{total}')
        print(f'  Total fetches so far: {fetch_count}')

    print(f'\n========== COMPLETE ==========')
    print(f'Total products updated: {all_updated}')
    print(f'Remaining incomplete: {count_incomplete(products)}')
    print(f'Total HTTP fetches: {fetch_count}')


if __name__ == '__main__':
    main()