"""
Checkout Layer 
Executes the payment against the gateway.
"""

import random
import uuid
import os
import razorpay


class CheckoutAgent:
    def __init__(self, gate, audit_trail):
        self.gate = gate
        self.audit = audit_trail

    def _call_razorpay_test_mode(self, session_id, amount):
        """
        Calls real Razorpay test-mode API using SDK and environment keys.
        """
        key_id = os.environ.get("RAZORPAY_KEY_ID")
        key_secret = os.environ.get("RAZORPAY_KEY_SECRET")

        if not key_id or not key_secret:
            return {"success": False, "order_id": None, "amount": amount, "error": "Missing Razorpay keys in environment"}

        try:
            client = razorpay.Client(auth=(key_id, key_secret))
            # Create a test order
            order = client.order.create({
                "amount": int(amount * 100),
                "currency": "INR",
                "receipt": f"receipt_{session_id}"
            })
            return {"success": True, "order_id": order["id"], "amount": amount}
        except Exception as e:
            return {"success": False, "order_id": None, "amount": amount, "error": str(e)}

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
                            "Razorpay test-mode payment call failed. "
                            "No charge was made; order not created.",
                            data=payment_result, status="error")
            return {
                "status": "failed",
                "message": "Payment couldn't be completed right now due to a gateway issue. "
                           "No amount was charged. Want me to retry, or try a different payment method?",
            }
