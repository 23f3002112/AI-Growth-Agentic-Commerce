import os
import json
import uuid
from dotenv import load_dotenv

from discovery import CatalogDiscovery
from upsell import UpsellAgent
from gate import TransactionGate
from checkout import CheckoutAgent
from campaign import CampaignOrchestrator
from audit import AuditTrail

class AgentSession:
    def __init__(self, discovery, upsell, gate, checkout, campaign, audit):
        self.session_id = f"sess_{uuid.uuid4().hex[:6]}"
        self.discovery = discovery
        self.upsell = upsell
        self.gate = gate
        self.checkout = checkout
        self.campaign = campaign
        self.audit = audit
        
        self.cart = []
        self.history = []
        self.last_candidates = []

    def handle_message(self, user_text: str) -> dict:
        self.history.append({"role": "user", "text": user_text})
        user_text_lower = user_text.lower()
        
        # 1. Check for Checkout Intent
        checkout_keywords = ["checkout", "buy now", "confirm", "pay"]
        if any(kw in user_text_lower for kw in checkout_keywords):
            if not self.cart:
                reply = "Your cart is empty. What would you like to buy?"
                self.audit.log(self.session_id, "agent", "checkout_empty_cart", "User asked to checkout but cart is empty.", status="blocked")
                return self._respond(reply, "blocked")
                
            checkout_result = self.checkout.checkout(self.session_id, self.cart, requires_human_approval=False)
            
            if checkout_result["status"] == "success":
                reply = checkout_result["message"]
                self.cart = [] # clear cart on success
                return self._respond(reply, "success")
            elif checkout_result["status"] == "needs_approval":
                reply = checkout_result["message"]
                return self._respond(reply, "needs_approval")
            else:
                reply = checkout_result["message"]
                return self._respond(reply, "failed")

        # 2. Check for Add-to-Cart Intent based on previous clarification
        add_keywords_1 = ["first", "1st", "number 1", "number one", "one"]
        add_keywords_2 = ["second", "2nd", "number 2", "number two", "two"]
        add_keywords_3 = ["third", "3rd", "number 3", "number three", "three"]
        
        selected_item = None
        if self.last_candidates:
            if any(kw in user_text_lower for kw in add_keywords_1):
                selected_item = self.last_candidates[0]
            elif len(self.last_candidates) > 1 and any(kw in user_text_lower for kw in add_keywords_2):
                selected_item = self.last_candidates[1]
            elif len(self.last_candidates) > 2 and any(kw in user_text_lower for kw in add_keywords_3):
                selected_item = self.last_candidates[2]
            
            # Simple keyword match on candidate names
            if not selected_item:
                for c in self.last_candidates:
                    if c["name"].lower() in user_text_lower or c.get("attributes", {}).get("color", "").lower() in user_text_lower:
                        selected_item = c
                        break

        if selected_item:
            self.cart.append(selected_item)
            self.audit.log(self.session_id, "agent", "item_added", f"Added {selected_item['name']} to cart based on user selection.", data={"sku": selected_item["sku"]})
            self.last_candidates = [] # clear candidates
            
            # Upsell
            suggestions = self.upsell.suggest(self.session_id, self.cart)
            reply = f"Great, I've added {selected_item['name']} to your cart! "
            if suggestions:
                upsell_item = suggestions[0]
                reply += f"\nRecommendation: {upsell_item['reason']} (Item: {upsell_item['name']} - INR {upsell_item['price']})"
            return self._respond(reply, "item_added")

        # 3. Handle as a Search Query
        results = self.discovery.query(text=user_text)
        matches = results["matches"]
        
        if len(matches) == 0:
            self.audit.log(self.session_id, "agent", "no_match_found", f"No catalog matches for query: '{user_text}'", status="error")
            
            import random
            in_stock = [i for i in self.discovery.items if i.get("availability", {}).get("in_stock", False)]
            if in_stock:
                suggestions = random.sample(in_stock, min(3, len(in_stock)))
                sug_text = "\n".join([f"- **{s['name']}** (INR {s['price']['amount']})" for s in suggestions])
                reply = f"I couldn't find anything matching '{user_text}'. Here are some popular items we have instead:\n\n{sug_text}\n\nWhat would you like?"
            else:
                reply = "I couldn't find anything matching that description. Could you try rephrasing?"
                
            return self._respond(reply, "no_match")
            
        elif len(matches) == 1:
            item = matches[0]
            self.cart.append(item)
            self.audit.log(self.session_id, "agent", "strong_match_added", f"Found exactly one match for '{user_text}'. Added {item['name']} to cart.", data={"sku": item["sku"]})
            
            suggestions = self.upsell.suggest(self.session_id, self.cart)
            reply = f"I found exactly what you're looking for: {item['name']} (INR {item['price']['amount']}). I've added it to your cart. "
            if suggestions:
                upsell_item = suggestions[0]
                reply += f"\nAlso, {upsell_item['reason']} (Item: {upsell_item['name']} - INR {upsell_item['price']})"
            return self._respond(reply, "item_added")
            
        else:
            # Multiple matches
            self.last_candidates = matches[:3] # keep top 3
            self.audit.log(self.session_id, "agent", "clarification_needed", f"Multiple matches found for '{user_text}'. Asking user to clarify.", data={"matches": [m["sku"] for m in self.last_candidates]})
            
            options_text = " ".join([f"{i+1}. {m['name']} (INR {m['price']['amount']})" for i, m in enumerate(self.last_candidates)])
            reply = f"I found a few great options. Did you mean: {options_text}?"
            return self._respond(reply, "clarification_needed")
            
    def _respond(self, reply_text: str, status: str) -> dict:
        self.history.append({"role": "agent", "text": reply_text})
        return {
            "reply": reply_text,
            "cart": [i["sku"] for i in self.cart],
            "status": status
        }

def interactive_loop():
    load_dotenv()
    
    print("Initializing Agentic Commerce Session...")
    audit = AuditTrail()
    discovery = CatalogDiscovery()
    gate = TransactionGate(audit)
    checkout = CheckoutAgent(gate, audit)
    upsell = UpsellAgent(discovery, audit)
    campaign = CampaignOrchestrator(audit)
    
    agent = AgentSession(discovery, upsell, gate, checkout, campaign, audit)
    print(f"Session Started [{agent.session_id}]. Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            response = agent.handle_message(user_input)
            print(f"\nAgent: {response['reply']}")
            print(f"[Cart: {response['cart']} | Status: {response['status']}]\n")
            
        except KeyboardInterrupt:
            break
            
    print("\n--- Final Audit Trail ---")
    audit.print_session(agent.session_id)

if __name__ == "__main__":
    interactive_loop()
