"""
Audit Trail Module — used by EVERY layer (discovery, checkout, upsell, gate).
This is the single most judge-visible piece per Track 01's bar:
"Every money action explainable, bounded and gated. Show the audit trail."
"""

import json
import time
from datetime import datetime


class AuditTrail:
    def __init__(self):
        self.events = []

    def log(self, session_id, actor, action, reason, data=None, status="ok"):
        """
        actor: which layer logged this (discovery/agent/gate/checkout/upsell/campaign)
        action: what happened (e.g. "match_found", "transaction_blocked", "upsell_offered")
        reason: PLAIN ENGLISH explanation — this is what makes it "explainable"
        status: ok / blocked / error / needs_approval
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "actor": actor,
            "action": action,
            "reason": reason,
            "status": status,
            "data": data or {},
        }
        self.events.append(event)
        return event

    def for_session(self, session_id):
        return [e for e in self.events if e["session_id"] == session_id]

    def save(self, path="audit_trail.json"):
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)

    def print_session(self, session_id):
        print(f"\n--- AUDIT TRAIL: session {session_id} ---")
        for e in self.for_session(session_id):
            print(f"[{e['timestamp']}] {e['actor']:>10} | {e['action']:<25} | "
                  f"{e['status']:<15} | {e['reason']}")
