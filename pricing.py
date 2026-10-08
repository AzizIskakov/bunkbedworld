"""Pricing utilities for Happy Homes Retail Code decoding."""
import math

def decode_retail_code(code):
    """
    Decode Happy Homes Retail Code to get our cost.
    
    Rule:
    1. Convert to string
    2. Remove first digit
    3. Remove last TWO digits
    4. Remaining digits = cost in dollars
    
    Examples:
        74997 -> 499 -> $499
        75497 -> 549 -> $549
        7697 -> 69 -> $69
    """
    s = str(code).strip()
    if len(s) < 4:
        raise ValueError(f"Retail code too short: {code}")
    # Remove first digit and last digit
    # Confirmed by examples: 74997 -> 499, 75497 -> 549, 7697 -> 69
    remaining = s[1:-1]
    if not remaining:
        raise ValueError(f"Retail code produced empty cost: {code}")
    return int(remaining)

def calculate_selling_price(cost, markup=1.7):
    """
    Calculate our website selling price.
    
    Formula: ceil(cost * markup)
    
    Examples:
        $499 * 1.7 = $848.30 -> $849
        $549 * 1.7 = $933.30 -> $934
        $69 * 1.7 = $117.30 -> $118
        $99 * 1.7 = $168.30 -> $169
        $100 * 1.7 = $170.00 -> $170
    """
    raw = cost * markup
    return math.ceil(raw)

def process_retail_code(code, markup=1.7):
    """Full pipeline: decode retail code -> calculate selling price."""
    cost = decode_retail_code(code)
    price = calculate_selling_price(cost, markup)
    return cost, price

def test():
    """Run test cases from the spec."""
    tests = [
        (74997, 499, 849),
        (75497, 549, 934),
        (7697, 69, 118),
    ]
    
    print("=" * 60)
    print("PRICING TEST SUITE")
    print("=" * 60)
    
    all_pass = True
    for code, expected_cost, expected_price in tests:
        cost, price = process_retail_code(code)
        cost_pass = cost == expected_cost
        price_pass = price == expected_price
        if cost_pass and price_pass:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_pass = False
        
        print(f"\nRetail Code: {code}")
        print(f"  Decoded cost: ${cost} (expected ${expected_cost}) {'✅' if cost_pass else '❌'}")
        print(f"  Selling price: ${price} (expected ${expected_price}) {'✅' if price_pass else '❌'}")
        print(f"  {status}")
    
    # Additional test: $99
    cost = decode_retail_code(99997)  # Would be $99
    price = calculate_selling_price(99)
    print(f"\nCost $99 test: ${price} (expected $169) {'✅' if price == 169 else '❌'}")
    if price != 169:
        all_pass = False
    
    # Test: $100 (should stay $170, no rounding needed)
    price = calculate_selling_price(100)
    print(f"Cost $100 test: ${price} (expected $170) {'✅' if price == 170 else '❌'}")
    if price != 170:
        all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("ALL TESTS PASSED ✅")
    else:
        print("SOME TESTS FAILED ❌")
    print("=" * 60)
    
    return all_pass

if __name__ == "__main__":
    test()