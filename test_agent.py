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
    return agent.session_id

if __name__ == "__main__":
    load_dotenv()
    
    # 1. Out of stock case
    run_convo("Out of Stock Case", [
        "Smart TV", 
        "add the first one",
        "checkout"
    ])
    
    # 2. High-value gate block case
    run_convo("High-Value Gate Block", [
        "Gaming Laptop",
        "add the first one",
        "checkout"
    ])
    
    # 3. Normal Clean Purchase
    run_convo("Clean Purchase", [
        "ceramic mug",
        "add the first one",
        "checkout"
    ])
