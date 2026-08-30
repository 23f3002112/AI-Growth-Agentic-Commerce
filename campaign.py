"""
Campaign Orchestrator — Track 01 Direction: "Campaign orchestrator"

Decides WHEN to trigger a promotional nudge (e.g. abandoned high-value cart,
slow-moving stock) and WHAT to offer — bounded by a discount ceiling so the
agent can never invent unlimited discounts on its own.
"""

MAX_AUTO_DISCOUNT_PERCENT = 15  # hard ceiling — agent cannot exceed this without approval


class CampaignOrchestrator:
    def __init__(self, audit_trail):
        self.audit = audit_trail

    def evaluate_cart_abandonment(self, session_id, cart, minutes_idle):
        """Decide whether to trigger a recovery nudge for an idle cart."""
        cart_total = sum(item["price"]["amount"] for item in cart)

        if minutes_idle < 10:
            self.audit.log(session_id, "campaign", "no_action",
                            f"Cart idle only {minutes_idle} min, below 10-min trigger threshold.",
                            status="ok")
            return None

        if cart_total > 3000:
            discount_percent = min(10, MAX_AUTO_DISCOUNT_PERCENT)
            reason = (f"High-value cart (INR {cart_total}) idle for {minutes_idle} min. "
                      f"Offering {discount_percent}% recovery discount, within the "
                      f"{MAX_AUTO_DISCOUNT_PERCENT}% auto-approve ceiling.")
        else:
            discount_percent = 5
            reason = (f"Cart idle for {minutes_idle} min. Offering standard {discount_percent}% "
                      f"nudge discount.")

        self.audit.log(session_id, "campaign", "recovery_offer_triggered", reason,
                        data={"cart_total": cart_total, "discount_percent": discount_percent},
                        status="ok")

        return {
            "action": "send_recovery_offer",
            "discount_percent": discount_percent,
            "message": f"Still thinking it over? Here's {discount_percent}% off to complete your order.",
        }

    def evaluate_slow_moving_stock(self, session_id, item, days_in_stock, units_sold):
        """Decide whether an item needs a promotional push."""
        if units_sold == 0 and days_in_stock > 30:
            discount_percent = min(12, MAX_AUTO_DISCOUNT_PERCENT)
            self.audit.log(session_id, "campaign", "slow_stock_promo_triggered",
                            f"{item['name']} ({item['sku']}) has 0 sales in {days_in_stock} days. "
                            f"Triggering {discount_percent}% promo, within ceiling.",
                            data={"sku": item["sku"], "discount_percent": discount_percent})
            return {"sku": item["sku"], "discount_percent": discount_percent}

        self.audit.log(session_id, "campaign", "no_action",
                        f"{item['name']} does not meet slow-stock criteria "
                        f"({units_sold} sold, {days_in_stock} days in stock).")
        return None
