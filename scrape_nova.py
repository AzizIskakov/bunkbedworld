#!/usr/bin/env python3
"""Scrape Nova Furniture products from Shopify API and merge into products.json"""

import json, urllib.request, sys, os, math

BASE_URL = "https://www.novafurniture.us"
PRODUCTS_JSON = os.path.join(os.path.dirname(__file__), "products.json")

def fetch_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def fetch_all_products():
    """Fetch all products from Shopify JSON API (paginated)"""
    all_products = []
    page = 1
    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"
        print(f"  Fetching page {page}...")
        data = fetch_json(url)
        products = data.get("products", [])
        if not products:
            break
        all_products.extend(products)
        print(f"    Got {len(products)} products")
        page += 1
        if page > 10:  # safety limit
            break
    return all_products

def is_in_stock(product):
    """Check if product is in stock (available AND not backordered/ETA)"""
    v = product["variants"][0]
    title = product["title"]
    
    # If variant says not available, skip
    if not v.get("available", True):
        return False
    
    # If title has [ETA: or [SPECIAL], it's backordered or special - skip
    if "[ETA:" in title or "[SPECIAL]" in title:
        return False
    
    # If the site collection listing shows "Out of Stock" (check via title pattern)
    # Some products have inventory_quantity = 0 but available = True (pre-order)
    inv_qty = v.get("inventory_quantity")
    if inv_qty is not None and inv_qty == 0:
        return False
    
    return True

def transform(product, idx):
    """Transform Shopify product to our format"""
    v = product["variants"][0]
    title = product["title"].strip()
    
    # Clean title - remove extra spaces
    name = " ".join(title.split())
    
    # Image URL - use first image, convert to HTTPS
    img = ""
    if product["images"]:
        img = product["images"][0]["src"]
        if img.startswith("//"):
            img = "https:" + img
    
    # Product page URL
    handle = product["handle"]
    page = f"{BASE_URL}/products/{handle}"
    
    # Category - map product_type
    category = product.get("product_type", "Uncategorized") or "Uncategorized"
    
    # Price - Shopify already gives us the vendor price
    cost_price = float(v["price"])
    
    # Our sell price = vendor price × 1.7
    sell_price = round(cost_price * 1.7, 2)
    
    # ID - use 'n' prefix for Nova
    item_id = f"n{idx + 1:04d}"
    
    return {
        "id": item_id,
        "name": name,
        "image": img,
        "page": page,
        "category": category,
        # We don't have these from the API directly, leave empty
        "color": "",
        "material": "",
        "dimensions": "",
        "description": "",
        "cost_price": cost_price,
        "sell_price": sell_price,
        "vendor": "Nova Furniture"
    }

def main():
    print("=" * 50)
    print("NOVA FURNITURE SCRAPER")
    print("=" * 50)
    
    # Step 1: Fetch all products
    print("\n📦 Fetching all products from Nova Furniture...")
    all_products = fetch_all_products()
    print(f"\n  Total products fetched: {len(all_products)}")
    
    # Step 2: Filter in-stock
    print("\n🔍 Filtering in-stock products...")
    in_stock = [p for p in all_products if is_in_stock(p)]
    out_of_stock = len(all_products) - len(in_stock)
    print(f"  In stock: {len(in_stock)}")
    print(f"  Out of stock / backordered: {out_of_stock}")
    
    # Step 3: Transform to our format
    print("\n🔄 Transforming to our format...")
    nova_products = [transform(p, i) for i, p in enumerate(in_stock)]
    
    # Print first 5 as sample
    print("\n  Sample transformed products:")
    for p in nova_products[:5]:
        print(f"    {p['id']}: {p['name']} — ${p['cost_price']} → ${p['sell_price']}")
    
    # Step 4: Merge with existing products
    print("\n🔗 Merging with existing products...")
    if os.path.exists(PRODUCTS_JSON):
        with open(PRODUCTS_JSON, 'r') as f:
            existing = json.load(f)
        print(f"  Existing products: {len(existing)}")
    else:
        existing = []
        print(f"  Existing products: 0 (new file)")
    
    # Find max existing ID for Happy Homes products
    max_happy_id = 0
    for p in existing:
        if p.get("vendor") == "Happy Homes":
            pid = p["id"]
            if pid.startswith("p"):
                try:
                    num = int(pid[1:])
                    if num > max_happy_id:
                        max_happy_id = num
                except ValueError:
                    pass
    
    # Find max Nova ID
    max_nova_id = 0
    for p in existing:
        if p.get("vendor") == "Nova Furniture":
            pid = p["id"]
            if pid.startswith("n"):
                try:
                    num = int(pid[1:])
                    if num > max_nova_id:
                        max_nova_id = num
                except ValueError:
                    pass
    
    print(f"  Max Happy Homes ID: p{max_happy_id}")
    print(f"  Max Nova Furniture ID: n{max_nova_id:04d}")
    
    # Remove old Nova products (we'll re-add fresh ones)
    old_nova_count = 0
    merged = [p for p in existing if p.get("vendor") != "Nova Furniture"]
    old_nova_count = len(existing) - len(merged)
    if old_nova_count > 0:
        print(f"  Removed {old_nova_count} old Nova Furniture entries (replacing with fresh data)")
    
    # Assign IDs starting after max
    start_idx = max_nova_id + 1
    for i, p in enumerate(nova_products):
        p["id"] = f"n{start_idx + i:04d}"
    
    # Add new Nova products
    merged.extend(nova_products)
    
    # Step 5: Save
    print(f"\n💾 Saving {len(merged)} products ({len(nova_products)} Nova + {len(merged) - len(nova_products)} Happy Homes)...")
    with open(PRODUCTS_JSON, 'w') as f:
        json.dump(merged, f, indent=2)
    
    print("\n✅ Done!")
    print(f"  Happy Homes products: {len(merged) - len(nova_products)}")
    print(f"  Nova Furniture products: {len(nova_products)}")
    print(f"  Total: {len(merged)}")
    
    # Summary by category
    print("\n📊 Nova products by category:")
    cats = {}
    for p in nova_products:
        c = p["category"]
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    
    # Price range
    prices = [p["sell_price"] for p in nova_products]
    if prices:
        print(f"\n💰 Price range: ${min(prices):.2f} - ${max(prices):.2f}")
        print(f"   Average sell price: ${sum(prices)/len(prices):.2f}")
    
    print("\n📋 Products saved to products.json")
    print("   Ready to deploy! 🚀")

if __name__ == "__main__":
    main()