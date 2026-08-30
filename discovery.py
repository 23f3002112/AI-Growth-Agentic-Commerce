"""
Discovery Layer — Track 01 core: lets an external AI buyer agent find
matching products from the agent-readable catalog via structured query,
not free-text scraping.
"""

import json


class CatalogDiscovery:
    def __init__(self, catalog_path="../catalog/merchant_catalog_agent_readable.json"):
        with open(catalog_path) as f:
            data = json.load(f)
        self.items = data["items"]

    def query(self, category=None, name_contains=None, max_price=None,
              attributes=None, only_in_stock=True):
        """
        A structured query interface — this is what an AI buyer agent calls
        instead of scraping a webpage. Returns ranked candidates.
        """
        results = self.items

        if category:
            results = [i for i in results if i["category"].lower() == category.lower()]
        if name_contains:
            results = [i for i in results if name_contains.lower() in i["name"].lower()]
        if max_price:
            results = [i for i in results if i["price"]["amount"] <= max_price]
        if attributes:
            for k, v in attributes.items():
                results = [i for i in results if i["attributes"].get(k, "").lower() == v.lower()]
        if only_in_stock:
            in_stock = [i for i in results if i["availability"]["in_stock"]]
            out_of_stock = [i for i in results if not i["availability"]["in_stock"]]
            # return in-stock first, but keep out-of-stock as "would-have-matched"
            # so the agent layer can build a substitute suggestion instead of a dead end
            return {"matches": in_stock, "out_of_stock_matches": out_of_stock}

        return {"matches": results, "out_of_stock_matches": []}

    def find_substitutes(self, reference_item, max_results=3):
        """Used for failure handling: if the exact match is out of stock,
        find the closest in-stock alternative in the same product line."""
        same_product = [i for i in self.items
                         if i["product_id"] == reference_item["product_id"]
                         and i["availability"]["in_stock"]]
        if same_product:
            return same_product[:max_results]

        # fallback: same category, similar price band
        target_price = reference_item["price"]["amount"]
        same_category = [i for i in self.items
                          if i["category"] == reference_item["category"]
                          and i["availability"]["in_stock"]
                          and abs(i["price"]["amount"] - target_price) < target_price * 0.3]
        return same_category[:max_results]
