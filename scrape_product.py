#!/usr/bin/env python3
"""
Product page scraper for Happy Homes product pages.
Extracts: Item Name, Color, Material, Dimensions, Description, Retail Code
"""
import json, re, sys, time, os
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), 'products.json')

def fetch_page_text(url):
    """Fetch a product page and extract readable text."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    req = urlopen(url)
    html = req.read().decode('utf-8', errors='replace')
    req.close()
    
    # Extract visible text from HTML - simple approach
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
    
    # Extract text between tags, preserving line breaks
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    
    # Normalize whitespace
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    
    return '\n'.join(lines)


def extract_fields(text):
    """Extract structured fields from Happy Homes product page text."""
    result = {}
    
    # Extract Item Name
    m = re.search(r'Item\s*Name:\s*(.*?)$', text, re.IGNORECASE | re.MULTILINE)
    if m:
        result['item_name'] = m.group(1).strip()
    
    # Extract Color
    m = re.search(r'Color:\s*(.*?)$', text, re.IGNORECASE | re.MULTILINE)
    if m:
        result['color'] = m.group(1).strip()
    
    # Extract Material
    m = re.search(r'Material:\s*(.*?)$', text, re.IGNORECASE | re.MULTILINE)
    if m:
        result['material'] = m.group(1).strip()
    
    # Extract Dimensions block (everything between "Dimensions:" line and "Retail Code:" or next section)
    dim_match = re.search(
        r'Dimensions:\s*\n((?:(?!Retail Code|Item Name|Color|Material|Description).*\n?)*)',
        text, re.IGNORECASE | re.MULTILINE
    )
    if dim_match:
        dim_text = dim_match.group(1).strip()
        if dim_text:
            result['dimensions'] = dim_text
    
    # If no "Dimensions:" label found, try to find dimension-like text
    if 'dimensions' not in result:
        # Look for patterns like numbers followed by x or " followed by H at end
        dim_lines = []
        for line in text.split('\n'):
            if re.search(r'\d+["\']?\s*x\s*\d+', line, re.IGNORECASE):
                dim_lines.append(line)
        if dim_lines:
            result['dimensions'] = '\n'.join(dim_lines)
    
    # Extract description - text between dimensions and Retail Code
    # Pattern: after dimensions info and before Retail Code
    desc_match = re.search(
        r'(?:Dimensions:.*?|(?:63x57x36H|\d+["\']?\s*[x×LWH].*?))\n(.*?)(?=Retail Code)',
        text, re.IGNORECASE | re.DOTALL
    )
    if not desc_match:
        # Try simpler: text between Material line (or last detail line) and Retail Code
        desc_match = re.search(
            r'(?:Material:.*?\n|Color:.*?\n)(.*?)(?=Retail Code)',
            text, re.IGNORECASE | re.DOTALL
        )
    if desc_match:
        desc = desc_match.group(1).strip()
        # Remove any dimension lines from description
        desc_lines = [l for l in desc.split('\n') if not re.search(r'\d+["\']?\s*x\s*\d+', l)]
        desc = '\n'.join(desc_lines).strip()
        if desc:
            result['description'] = desc
    
    # Extract Retail Code
    m = re.search(r'Retail\s*Code:\s*(.*?)$', text, re.IGNORECASE | re.MULTILINE)
    if m:
        result['retail_code'] = m.group(1).strip()
    
    return result


def main():
    with open(PRODUCTS_FILE) as f:
        data = json.load(f)
    products = data if isinstance(data, list) else data.get('products', [])
    
    # Find incomplete products
    incomplete = []
    for i, p in enumerate(products):
        for field in ['description', 'dimensions', 'color', 'material']:
            val = p.get(field)
            if not val or str(val).strip() == '':
                incomplete.append(i)
                break
    
    print(f'Total products: {len(products)}')
    print(f'Incomplete: {len(incomplete)}')
    
    if incomplete:
        print(f'First incomplete index: {incomplete[0]}')
        print(f'Product: {products[incomplete[0]].get("name")} - {products[incomplete[0]].get("page")}')


if __name__ == '__main__':
    main()