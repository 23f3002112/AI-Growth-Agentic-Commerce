"""
Synthetic Merchant Catalog Generator — Track 01: AI Growth & Agentic Commerce
Razorpay AI Buildathon 2026

Generates a realistic merchant product catalog (like a mid-size D2C fashion/
electronics store) with variants, stock levels, and pricing. This is the raw
input that catalog/schema.py converts into an agent-readable format.

Usage:
    python generate_catalog.py --n 60 --seed 7
"""

import argparse
import json
import random

CATEGORIES = {
    "Apparel": {
        "products": ["Cotton T-Shirt", "Denim Jacket", "Formal Shirt", "Hoodie", "Chinos", "Kurta"],
        "variants": {"size": ["S", "M", "L", "XL"], "color": ["Black", "White", "Navy", "Olive", "Maroon"]},
        "price_range": (599, 3499),
    },
    "Footwear": {
        "products": ["Running Shoes", "Sneakers", "Sandals", "Formal Shoes"],
        "variants": {"size": ["6", "7", "8", "9", "10"], "color": ["Black", "White", "Grey"]},
        "price_range": (999, 5999),
    },
    "Electronics": {
        "products": ["Wireless Earbuds", "Bluetooth Speaker", "Smart Watch", "Power Bank"],
        "variants": {"color": ["Black", "White", "Blue"]},
        "price_range": (799, 8999),
    },
    "Home & Kitchen": {
        "products": ["Ceramic Mug Set", "Non-stick Pan", "Table Lamp"],
        "variants": {"color": ["White", "Black", "Grey", "Blue"]},
        "price_range": (299, 3999),
    },
}


def generate_catalog(n, seed):
    rng = random.Random(seed)
    catalog = []
    product_id_counter = 1000

    for _ in range(n):
        category = rng.choice(list(CATEGORIES.keys()))
        cat_info = CATEGORIES[category]
        base_name = rng.choice(cat_info["products"])
        product_id_counter += 1
        product_id = f"PROD{product_id_counter}"

        base_price = round(rng.uniform(*cat_info["price_range"]), -1) + 9  # e.g. 1299, 899

        variants = []
        variant_dims = cat_info["variants"]
        dim_names = list(variant_dims.keys())

        # Build variant combinations (limited so catalog stays realistic in size)
        if len(dim_names) == 2:
            combos = [(s, c) for s in variant_dims[dim_names[0]] for c in variant_dims[dim_names[1]]]
            rng.shuffle(combos)
            combos = combos[: rng.randint(3, 6)]
            for combo in combos:
                variants.append({
                    "sku": f"{product_id}-{combo[0]}-{combo[1][:3].upper()}",
                    dim_names[0]: combo[0],
                    dim_names[1]: combo[1],
                    "price": base_price + rng.choice([0, 0, 100, -50]),
                    "stock": rng.choice([0, 0, 2, 5, 12, 30, 50]),  # some intentionally out of stock
                })
        else:
            values = variant_dims[dim_names[0]]
            for v in rng.sample(values, k=min(len(values), rng.randint(2, 3))):
                variants.append({
                    "sku": f"{product_id}-{v[:3].upper()}",
                    dim_names[0]: v,
                    "price": base_price + rng.choice([0, 0, 200, -100]),
                    "stock": rng.choice([0, 0, 3, 10, 25]),
                })

        catalog.append({
            "product_id": product_id,
            "name": base_name,
            "category": category,
            "description": f"{base_name} - {category.lower()} item, comfortable and durable, "
                            f"suitable for daily wear." if category in ("Apparel", "Footwear")
                            else f"{base_name} with premium build quality and excellent features.",
            "base_price": base_price,
            "currency": "INR",
            "variants": variants,
            "rating": round(rng.uniform(3.5, 4.9), 1),
            "return_window_days": rng.choice([7, 10, 15]),
        })

    return catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--outfile", type=str, default="merchant_catalog_raw.json")
    parser.add_argument("--report", action="store_true", help="Print catalog distribution stats")
    args = parser.parse_args()

    catalog = generate_catalog(args.n, args.seed)
    with open(args.outfile, "w") as f:
        json.dump(catalog, f, indent=2)

    total_variants = sum(len(p["variants"]) for p in catalog)
    out_of_stock = sum(1 for p in catalog for v in p["variants"] if v["stock"] == 0)
    
    if args.report:
        print("\n--- Catalog Report ---")
        cat_stats = {}
        for p in catalog:
            c = p["category"]
            if c not in cat_stats:
                cat_stats[c] = {"products": 0, "variants": 0, "oos": 0, "total_price": 0}
            cat_stats[c]["products"] += 1
            cat_stats[c]["variants"] += len(p["variants"])
            cat_stats[c]["oos"] += sum(1 for v in p["variants"] if v["stock"] == 0)
            cat_stats[c]["total_price"] += p["base_price"]
        
        for c, stats in cat_stats.items():
            avg_price = stats["total_price"] / stats["products"] if stats["products"] > 0 else 0
            print(f"Category: {c}")
            print(f"  Products: {stats['products']}")
            print(f"  Variants: {stats['variants']}")
            print(f"  Out-of-stock: {stats['oos']}")
            print(f"  Avg Price: INR {avg_price:.2f}")
        print("----------------------\n")

    print(f"Generated {len(catalog)} products, {total_variants} total variants")
    print(f"Out-of-stock variants (intentional, for failure-handling demo): {out_of_stock}")
    print(f"Written to: {args.outfile}")
