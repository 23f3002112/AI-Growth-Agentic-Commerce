"""
Orchestrator — Track 01: AI Growth & Agentic Commerce
Runs the full agent loop end to end: discover -> substitute (if needed) ->
upsell -> gate -> checkout -> audit, plus a standalone campaign demo.

This is the single script that demonstrates ALL FOUR example directions
working together against one shared catalog, gate, and audit trail.
"""

import sys


from discovery import CatalogDiscovery
from upsell import UpsellAgent
from gate import TransactionGate
from checkout import CheckoutAgent
from campaign import CampaignOrchestrator
from audit import AuditTrail


def run_demo():
    audit = AuditTrail()
    discovery = CatalogDiscovery()
    gate = TransactionGate(audit)
    checkout = CheckoutAgent(gate, audit)
    upsell = UpsellAgent(discovery, audit)
    campaign = CampaignOrchestrator(audit)

    print("=" * 70)
    print("DEMO 1: Happy path — conversational checkout + upsell")
    print("=" * 70)
    session_1 = "sess_001"
    result = discovery.query(category="Apparel", attributes={"color": "Black"}, max_price=2000)
    if result["matches"]:
        cart = [result["matches"][0]]
        print(f"Buyer agent found: {cart[0]['name']} ({cart[0]['sku']}) - INR {cart[0]['price']['amount']}")

        suggestions = upsell.suggest(session_1, cart)
        print(f"Upsell suggestions: {[s['name'] for s in suggestions]}")

        outcome = checkout.checkout(session_1, cart)
        print(f"Checkout result: {outcome['status']} — {outcome['message']}")
    audit.print_session(session_1)

    print("\n" + "=" * 70)
    print("DEMO 2: Failure handling — item out of stock, agent finds substitute")
    print("=" * 70)
    session_2 = "sess_002"
    result = discovery.query(category="Footwear", only_in_stock=False)
    out_of_stock_items = [i for i in result["matches"] if not i["availability"]["in_stock"]]
    if out_of_stock_items:
        wanted = out_of_stock_items[0]
        audit.log(session_2, "agent", "item_unavailable",
                   f"Buyer requested {wanted['name']} ({wanted['sku']}), but it is OUT_OF_STOCK.",
                   data={"sku": wanted["sku"]}, status="needs_fallback")
        print(f"Buyer wanted: {wanted['name']} ({wanted['sku']}) — OUT OF STOCK")

        substitutes = discovery.find_substitutes(wanted)
        if substitutes:
            sub = substitutes[0]
            audit.log(session_2, "agent", "substitute_found",
                       f"Found in-stock substitute: {sub['name']} ({sub['sku']}), "
                       f"same product line as originally requested item.",
                       data={"original_sku": wanted["sku"], "substitute_sku": sub["sku"]})
            print(f"Agent gracefully substituted: {sub['name']} ({sub['sku']}) - INR {sub['price']['amount']}")
            outcome = checkout.checkout(session_2, [sub])
            print(f"Checkout result: {outcome['status']} — {outcome['message']}")
        else:
            audit.log(session_2, "agent", "no_substitute_found",
                       "No in-stock substitute found in same product line or category/price band.",
                       status="dead_end")
            print("No substitute found — agent would inform the buyer honestly here.")
    audit.print_session(session_2)

    print("\n" + "=" * 70)
    print("DEMO 3: Gate blocking — high-value cart requiring human approval")
    print("=" * 70)
    session_3 = "sess_003"
    expensive = sorted(discovery.items, key=lambda x: -x["price"]["amount"])
    cart_3 = [i for i in expensive if i["availability"]["in_stock"]][:3]
    total_3 = sum(i["price"]["amount"] for i in cart_3)
    print(f"Cart total: INR {total_3} across {len(cart_3)} items")
    outcome_3 = checkout.checkout(session_3, cart_3)
    print(f"Checkout result: {outcome_3['status']} — {outcome_3['message']}")
    audit.print_session(session_3)

    print("\n" + "=" * 70)
    print("DEMO 4: Campaign orchestrator — abandoned cart + slow stock")
    print("=" * 70)
    session_4 = "sess_004"
    cart_4 = [i for i in discovery.items if i["availability"]["in_stock"]][:2]
    offer = campaign.evaluate_cart_abandonment(session_4, cart_4, minutes_idle=25)
    print(f"Abandonment offer: {offer}")

    slow_item = discovery.items[5]
    promo = campaign.evaluate_slow_moving_stock(session_4, slow_item, days_in_stock=45, units_sold=0)
    print(f"Slow-stock promo: {promo}")
    audit.print_session(session_4)

    audit.save("full_audit_trail.json")
    print(f"\n\nTotal audit events logged across all demos: {len(audit.events)}")
    print("Full audit trail saved to: full_audit_trail.json")

    print("\n" + "=" * 70)
    print("DEMO 5: Ad-hoc test — free-text discovery query")
    print("=" * 70)
    ad_hoc_result = discovery.query(text="ceramic mug")
    print("Matches for text='ceramic mug':")
    for match in ad_hoc_result["matches"]:
        print(f" - {match['name']} ({match['sku']}) - {match['category']}")


if __name__ == "__main__":
    run_demo()
