import sys
from dotenv import load_dotenv
from agent_session import AgentSession
from discovery import CatalogDiscovery
from upsell import UpsellAgent
from gate import TransactionGate
from checkout import CheckoutAgent
from campaign import CampaignOrchestrator
from audit import AuditTrail

def run_convo(name, messages):
    print(f"\n=========================================")
    print(f"CONVERSATION: {name}")
    print(f"=========================================")
    audit = AuditTrail()
    discovery = CatalogDiscovery()
    gate = TransactionGate(audit)
    checkout = CheckoutAgent(gate, audit)
    upsell = UpsellAgent(discovery, audit)
    campaign = CampaignOrchestrator(audit)
    agent = AgentSession(discovery, upsell, gate, checkout, campaign, audit)
    
    for msg in messages:
        print(f"\nUser: {msg}")
        resp = agent.handle_message(msg)
        print(f"Agent: {resp['reply']}")
        print(f"[Cart: {resp['cart']} | Status: {resp['status']}]")
        
    audit.print_session(agent.session_id)

if __name__ == "__main__":
    load_dotenv()
    # 1. Clean purchase
    run_convo("Clean Purchase (Exact match)", [
        "Running Shoes PROD1009-10-BLA", 
        "checkout"
    ])
    
    # 2. Ambiguous query needing clarification
    run_convo("Ambiguous Query & Clarification", [
        "ceramic mug",
        "add the first one",
        "buy now"
    ])
    
    # 3. Query with no matches
    run_convo("No Matches", [
        "astronaut spacesuit under 10 dollars"
    ])
