"""
Checkout Layer — Track 01 Direction: "Conversational In-App Checkout"

Simulates a Razorpay test-mode payment call. In your real submission, replace
`_call_razorpay_test_mode()` with an actual call to Razorpay's test-mode
Orders/Payments API (see their docs) — the surrounding gate + audit logic
does not need to change at all, which is the point of separating them.
"""

import random
import uuid


class CheckoutAgent:
    def __init__(self, gate, audit_trail):
        self.gate = gate
        self.audit = audit_trail

    def _call_razorpay_test_mode(self, session_id, amount):
        """
        STUB for Razorpay test-mode API call.
        Replace with real SDK call:
            razorpay_client.order.create({"amount": amount*100, "currency": "INR", ...})
        Simulated here with a 90% success rate to demonstrate real failure handling.
        """
        success = random.random() < 0.9
        order_id = f"order_test_{uuid.uuid4().hex[:12]}"
        return {"success": success, "order_id": order_id, "amount": amount}

    def checkout(self, session_id, cart, requires_human_approval=False):
        """
        cart: list of catalog items (from discovery.query results)
        Returns a structured result the conversational layer can turn into a
        chat reply, and logs every step to the audit trail.
        """
        total = sum(item["price"]["amount"] for item in cart)

        self.audit.log(session_id, "checkout", "checkout_initiated",
                        f"Cart of {len(cart)} item(s), total INR {total}.",
                        data={"items": [i["sku"] for i in cart], "total": total})

        allowed, reason, needs_approval = self.gate.check(
            session_id, cart, total, requires_human_approval=requires_human_approval
        )

        if needs_approval:
            return {
                "status": "needs_approval",
                "message": f"This order totals INR {total}, which is above the "
                           f"auto-approve limit. Please confirm to proceed.",
                "total": total,
            }

        if not allowed:
            return {
                "status": "blocked",
                "message": f"Sorry, I can't complete this order: {reason.replace('_', ' ')}.",
                "reason": reason,
            }

        # Gate passed -> attempt payment
        payment_result = self._call_razorpay_test_mode(session_id, total)

        if payment_result["success"]:
            self.audit.log(session_id, "checkout", "payment_success",
                            f"Payment of INR {total} succeeded. Order: {payment_result['order_id']}.",
                            data=payment_result, status="ok")
            return {
                "status": "success",
                "message": f"Order placed! INR {total} charged. Order ID: {payment_result['order_id']}.",
                "order_id": payment_result["order_id"],
            }
        else:
            # THIS is the required "one failure handled gracefully" case
            self.audit.log(session_id, "checkout", "payment_failed",
                            "Razorpay test-mode payment call failed (simulated gateway timeout). "
                            "No charge was made; order not created.",
                            data=payment_result, status="error")
            return {
                "status": "failed",
                "message": "Payment couldn't be completed right now due to a gateway issue. "
                           "No amount was charged. Want me to retry, or try a different payment method?",
            }
