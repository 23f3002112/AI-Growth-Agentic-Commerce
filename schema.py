"""
Agent-Readable Catalog Schema — Track 01 Direction: "Agent-Readable Catalog"
Razorpay AI Buildathon 2026

Converts a raw merchant catalog (catalog/generate_catalog.py output) into a
structured, machine-readable format an external AI buyer agent can query and
reason over directly — inspired by the shape of emerging agentic-commerce
protocols (schema.org Product/Offer conventions + a simple discovery
endpoint), NOT any specific proprietary protocol spec.

This is the foundation every other Track 01 direction (checkout, upsell,
campaigns) builds on top of.
"""

import json


def to_agent_readable(raw_catalog: list) -> dict:
    """
    Converts the raw catalog into a structured format with:
      - a flat, queryable variant-level index (what an AI buyer actually needs)
      - explicit availability signals (so an agent never has to guess stock)
      - explicit capability flags (what actions are even possible on this item)
    """
    entries = []
    for product in raw_catalog:
        for variant in product["variants"]:
            entries.append({
                "sku": variant["sku"],
                "product_id": product["product_id"],
                "name": product["name"],
                "category": product["category"],
                "description": product["description"],
                "attributes": {k: v for k, v in variant.items()
                               if k not in ("sku", "price", "stock")},
                "price": {"amount": variant["price"], "currency": product["currency"]},
                "availability": {
                    "in_stock": variant["stock"] > 0,
                    "quantity": variant["stock"],
                    "status": "IN_STOCK" if variant["stock"] > 5
                               else ("LOW_STOCK" if variant["stock"] > 0 else "OUT_OF_STOCK"),
                },
                "capabilities": {
                    "purchasable": variant["stock"] > 0,
                    "returnable": True,
                    "return_window_days": product["return_window_days"],
                },
                "rating": product["rating"],
            })

    return {
        "schema_version": "1.0",
        "merchant": {
            "name": "Demo Merchant Pvt Ltd",
            "supports_agentic_checkout": True,
            "payment_gateway": "razorpay_test_mode",
        },
        "catalog_size": len(entries),
        "items": entries,
    }


if __name__ == "__main__":
    with open("merchant_catalog_raw.json") as f:
        raw = json.load(f)

    agent_catalog = to_agent_readable(raw)

    with open("merchant_catalog_agent_readable.json", "w") as f:
        json.dump(agent_catalog, f, indent=2)

    print(f"Agent-readable catalog: {agent_catalog['catalog_size']} queryable SKUs")
    print("Written to: merchant_catalog_agent_readable.json")
