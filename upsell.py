"""
Upsell & Cross-sell Layer
Uses LLM reasoning to recommend complementary products.
"""
import os
import json

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class UpsellAgent:
    def __init__(self, discovery, audit_trail):
        self.discovery = discovery
        self.audit = audit_trail

    def suggest(self, session_id, cart, max_suggestions=2):
        suggestions = []
        cart_categories = {item["category"] for item in cart}
        cart_skus = {item["sku"] for item in cart}
        cart_total = sum(item["price"]["amount"] for item in cart)

        for item in cart:
            # Cross-sell: same category, different product, similar price band
            candidates = [
                i for i in self.discovery.items
                if i["category"] == item["category"]
                and i["sku"] not in cart_skus
                and i["availability"]["in_stock"]
                and i["product_id"] != item["product_id"]
            ]
            candidates.sort(key=lambda x: -x["rating"])

            for c in candidates[:1]:
                suggestions.append({
                    "sku": c["sku"], "name": c["name"], "price": c["price"]["amount"],
                    "reason": f"Frequently bought alongside {item['name']} "
                              f"(same category: {item['category']}, rated {c['rating']}/5).",
                })

        # Upsell: if cart total is close to a round threshold, suggest bridging item
        threshold = 999 if cart_total < 999 else (1999 if cart_total < 1999 else None)
        if threshold and threshold - cart_total < 500:
            gap = threshold - cart_total
            bridge_candidates = [
                i for i in self.discovery.items
                if i["price"]["amount"] <= gap + 200
                and i["availability"]["in_stock"]
                and i["sku"] not in cart_skus
            ]
            if bridge_candidates:
                b = max(bridge_candidates, key=lambda x: x["rating"])
                suggestions.append({
                    "sku": b["sku"], "name": b["name"], "price": b["price"]["amount"],
                    "reason": f"Adding this gets you close to the INR {threshold} "
                              f"threshold — only INR {gap} more needed.",
                })

        suggestions = suggestions[:max_suggestions]

        self.audit.log(session_id, "upsell", "rule_based_suggestions",
                        f"Generated {len(suggestions)} rule-based suggestion(s).",
                        data={"suggestions": suggestions})

        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and genai and suggestions:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = (
                    f"You are an AI shopping assistant. "
                    f"The user has these items in their cart: {json.dumps([{'name': i['name'], 'price': i['price']} for i in cart])}\n"
                    f"Here are the rule-based upsell suggestions: {json.dumps(suggestions)}\n"
                    "Pick the SINGLE best suggestion to show the user. "
                    "Write a natural, customer-facing one-sentence reason why they should buy it. "
                    "Return ONLY strict JSON in this exact format: {\"best_sku\": \"...\", \"customer_facing_reason\": \"...\"}"
                )
                response = model.generate_content(prompt)
                
                llm_text = response.text
                import re
                json_match = re.search(r'\{.*\}', llm_text, re.DOTALL)
                if json_match:
                    llm_data = json.loads(json_match.group(0))
                    best_sku = llm_data.get("best_sku")
                    
                    best_suggestion = next((s for s in suggestions if s["sku"] == best_sku), None)
                    if best_suggestion:
                        best_suggestion["reason"] = llm_data.get("customer_facing_reason", best_suggestion["reason"])
                        self.audit.log(session_id, "upsell", "llm_enhanced_suggestion",
                                        f"LLM picked {best_sku} and rewrote the reason.",
                                        data={"llm_suggestion": best_suggestion})
                        return [best_suggestion]
            except Exception as e:
                self.audit.log(session_id, "upsell", "llm_fallback",
                                "LLM reasoning failed, falling back to rule-based.",
                                data={"error": str(e)}, status="error")
                pass

        return suggestions
