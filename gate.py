"""
Gate Module — Explicit, bounded transaction rules.
Enforces strict financial guardrails for agent actions. 
Nothing reaches Razorpay's API without passing through here.

Design principle: the gate is DUMB ON PURPOSE. It should never need an LLM to
decide whether a transaction is allowed — hard-coded, auditable business rules
only. This is what makes the system trustworthy: a human can read this file
top to bottom and know exactly what the agent can and cannot do with money.
"""

MAX_AUTO_APPROVE_AMOUNT = 5000       # INR — above this, needs explicit approval flag
MAX_DAILY_AGENT_SPEND = 50000        # INR — hard ceiling per session/day
MAX_ITEMS_PER_ORDER = 5              # prevents runaway cart-stuffing
BLOCKED_CATEGORIES = []              # e.g. could restrict certain categories per-merchant


class TransactionGate:
    def __init__(self, audit_trail):
        self.audit = audit_trail
        self.session_spend = {}  # session_id -> running total

    def check(self, session_id, cart, total_amount, requires_human_approval=False):
        """
        Returns (allowed: bool, reason: str, needs_approval: bool)
        Every check is logged to the audit trail regardless of outcome.
        """
        spent_so_far = self.session_spend.get(session_id, 0)

        # Rule 1: item count bound
        if len(cart) > MAX_ITEMS_PER_ORDER:
            self.audit.log(session_id, "gate", "transaction_blocked",
                            f"Cart has {len(cart)} items, exceeds max {MAX_ITEMS_PER_ORDER} per order.",
                            data={"cart_size": len(cart)}, status="blocked")
            return False, "cart_size_exceeded", False

        # Rule 2: blocked categories
        for item in cart:
            if item.get("category") in BLOCKED_CATEGORIES:
                self.audit.log(session_id, "gate", "transaction_blocked",
                                f"Category '{item['category']}' is not allowed for agentic checkout.",
                                data={"sku": item.get("sku")}, status="blocked")
                return False, "category_blocked", False

            # Rule 2.5: single item exceeds 40% of MAX_DAILY_AGENT_SPEND
            if item["price"]["amount"] > MAX_DAILY_AGENT_SPEND * 0.4:
                self.audit.log(session_id, "gate", "transaction_blocked",
                                f"Item '{item.get('name')}' price ({item['price']['amount']}) exceeds "
                                f"single-item limit (40% of {MAX_DAILY_AGENT_SPEND}).",
                                data={"sku": item.get("sku"), "amount": item["price"]["amount"]}, status="blocked")
                return False, "single_item_limit_exceeded", False

        # Rule 3: daily spend ceiling
        if spent_so_far + total_amount > MAX_DAILY_AGENT_SPEND:
            self.audit.log(session_id, "gate", "transaction_blocked",
                            f"Would exceed daily spend ceiling: {spent_so_far} + {total_amount} "
                            f"> {MAX_DAILY_AGENT_SPEND}.",
                            data={"spent_so_far": spent_so_far, "attempted": total_amount},
                            status="blocked")
            return False, "daily_ceiling_exceeded", False

        # Rule 4: high-value transactions need explicit human approval
        if total_amount > MAX_AUTO_APPROVE_AMOUNT and not requires_human_approval:
            self.audit.log(session_id, "gate", "needs_approval",
                            f"Amount {total_amount} exceeds auto-approve limit "
                            f"{MAX_AUTO_APPROVE_AMOUNT}. Routing to human confirmation.",
                            data={"amount": total_amount}, status="needs_approval")
            return False, "requires_human_approval", True

        # All checks passed
        self.session_spend[session_id] = spent_so_far + total_amount
        self.audit.log(session_id, "gate", "transaction_approved",
                        f"Amount {total_amount} within all bounds "
                        f"(auto-approve limit {MAX_AUTO_APPROVE_AMOUNT}, "
                        f"daily ceiling {MAX_DAILY_AGENT_SPEND}).",
                        data={"amount": total_amount}, status="ok")
        return True, "approved", False
