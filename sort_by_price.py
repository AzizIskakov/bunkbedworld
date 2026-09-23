#!/usr/bin/env python3
"""Sort products.json: group by category (first-appearance order), cheapest first within each category.
Run after any price change so the site displays categories sorted by price.
Usage: python3 sort_by_price.py
"""
import json
import sys

PATH = "products.json"


def effective_price(p):
    """Display price used for sorting: min size sell, else sell_price. None if unpriced."""
    if p.get("size_prices"):
        vals = [v.get("sell") for v in p["size_prices"].values() if isinstance(v, dict) and v.get("sell")]
        if vals:
            return min(vals)
    sp = p.get("sell_price")
    return sp if isinstance(sp, (int, float)) and sp > 0 else None


def main():
    with open(PATH) as f:
        data = json.load(f)

    cat_order = []
    for p in data:
        c = p.get("category") or "Uncategorized"
        if c not in cat_order:
            cat_order.append(c)

    def sort_key(p):
        c = p.get("category") or "Uncategorized"
        ep = effective_price(p)
        # unpriced items go last within their category
        has_price = 0 if ep is not None else 1
        return (cat_order.index(c), has_price, ep if ep is not None else 0, p.get("id", ""))

    data.sort(key=sort_key)

    with open(PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Sorted {len(data)} products across {len(cat_order)} categories (cheapest first).")


if __name__ == "__main__":
    main()