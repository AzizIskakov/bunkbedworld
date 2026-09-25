#!/usr/bin/env python3
"""Reorganize product categories per Oz's instructions."""

import json, os

PRODUCTS_JSON = os.path.join(os.path.dirname(__file__), "products.json")

with open(PRODUCTS_JSON) as f:
    products = json.load(f)

# ========================================
# Step 1: Rename "Barstools" → "Barstools & Chairs" globally
# ========================================
for p in products:
    if p.get("category") == "Barstools":
        p["category"] = "Barstools & Chairs"

# ========================================
# Step 2: Nova Furniture category mapping
# ========================================
# Priority rule: check explicit mapping first, then existing categories, then create new.

# Explicit mappings as Oz specified
NOVA_MAP = {
    # Sectionals → Stationary Sectionals
    "Nova Sectional": "Stationary Sectionals",
    "Sectional": "Stationary Sectionals",
    "Chaise": "Stationary Sectionals",
    
    # Sofas
    "Nova Sofa": "Sofas",
    "Sofa": "Sofas",
    
    # Sofa & Loveseat sets
    "Nova Sofa & Loveseat": "Sofa & Loveseat sets",
    "Sofa & Loveseat": "Sofa & Loveseat sets",
    "Nova Loveseat": "Sofa & Loveseat sets",
    "Loveseat": "Sofa & Loveseat sets",
    
    # Coffee Tables → Occasional Tables
    "Nova Coffee Table": "Occasional Tables",
    "Coffee Table": "Occasional Tables",
    
    # Dining → Dining Rooms
    "Dining Table": "Dining Rooms",
    "Dining Chair": "Dining Rooms",
    "Dining Bench": "Dining Rooms",
    "Counter Height Table": "Dining Rooms",
    "Counter Height Set": "Dining Rooms",
    "Counter Height Chair": "Dining Rooms",
    
    # Chairs & Stools → Barstools & Chairs
    "Nova Chair": "Barstools & Chairs",
    "Chair": "Barstools & Chairs",
    "Nova Stool": "Barstools & Chairs",
    
    # Beds
    "Queen Bed": "Beds",
    "King Bed": "Beds",
    "Full Bed": "Beds",
    "Twin Bed": "Beds",
    
    # Mattresses
    "Twin Mattress": "Mattresses",
    "King Mattress": "Mattresses",
    
    # Bedroom furniture
    "Bedroom Set": "Bedrooms",
    "Nova Bedroom Set": "Bedrooms",
    "Nightstand": "Bedrooms",
    "Dresser": "Bedrooms",
    "Chest": "Bedrooms",
    
    # Accessories / misc
    "Bedroom Mirror": "Vanities & Mirrors",
    "Area Rug": "Accessories",
    "Ottoman": "Accessories",
    "Nova Ottoman": "Accessories",
    "Pieces": "Accessories",
    "_Preset": "Uncategorized",
    "No Image": "Uncategorized",
    "Duplicated": "Uncategorized",
    "Special Order": "Uncategorized",
    
    # Recliners
    "Recliner": "Recliners & Lift Chairs",
    "Power Reclining Sofa": "Reclining Sofa & Loveseats",
    "Power Reclining Loveseat": "Reclining Sofa & Loveseats",
    "Reclining Loveseat": "Reclining Sofa & Loveseats",
    
    # Bookcase
    "Bookcase": "Office & Bookcase",
}

# Apply Nova mapping
mapped_count = 0
new_categories_created = set()

for p in products:
    if p.get("vendor") != "Nova Furniture":
        continue
    
    cat = p.get("category", "Uncategorized")
    
    if cat in NOVA_MAP:
        new_cat = NOVA_MAP[cat]
        p["category"] = new_cat
        mapped_count += 1
    else:
        # "For rest create new category" - but clean up the name
        # Strip "Nova " prefix if present
        if cat.startswith("Nova "):
            new_cat = cat[5:]  # Remove "Nova " prefix
        else:
            new_cat = cat
        
        # Capitalize nicely
        new_cat = new_cat.strip()
        if new_cat and new_cat[0].isalpha():
            new_cat = new_cat[0].upper() + new_cat[1:]
        
        p["category"] = new_cat
        new_categories_created.add(new_cat)

print(f"Mapped {mapped_count} Nova products to existing categories")
print(f"Created {len(new_categories_created)} new categories: {sorted(new_categories_created)}")

# ========================================
# Step 3: Show final category breakdown
# ========================================
cats = {}
vendors = {}
for p in products:
    v = p.get("vendor", "Unknown")
    c = p.get("category", "Uncategorized")
    key = (v, c)
    vendors[key] = vendors.get(key, 0) + 1
    cats[c] = cats.get(c, 0) + 1

print(f"\n=== FINAL CATEGORY BREAKDOWN ===")
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    hh = vendors.get(("Happy Homes", c), 0)
    nv = vendors.get(("Nova Furniture", c), 0)
    print(f"  {c}: {n} total ({hh} HH + {nv} Nova)")

print(f"\nTotal products: {len(products)}")

# Save
with open(PRODUCTS_JSON, 'w') as f:
    json.dump(products, f, indent=2)

print("\n✅ products.json updated with reorganized categories!")