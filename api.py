from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from agent_session import AgentSession
from discovery import CatalogDiscovery
from upsell import UpsellAgent
from gate import TransactionGate
from checkout import CheckoutAgent
from campaign import CampaignOrchestrator
from audit import AuditTrail
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Agentic Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for sessions (as requested for demo)
ACTIVE_SESSIONS = {}

# Shared singletons for the backend services
audit_trail = AuditTrail()
discovery = CatalogDiscovery()
gate = TransactionGate(audit_trail)
checkout = CheckoutAgent(gate, audit_trail)
upsell = UpsellAgent(discovery, audit_trail)
campaign = CampaignOrchestrator(audit_trail)

class MessageRequest(BaseModel):
    text: str

@app.post("/session")
def create_session():
    agent = AgentSession(discovery, upsell, gate, checkout, campaign, audit_trail)
    ACTIVE_SESSIONS[agent.session_id] = agent
    return {"session_id": agent.session_id}

@app.post("/session/{session_id}/message")
def handle_message(session_id: str, req: MessageRequest):
    agent = ACTIVE_SESSIONS.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    
    response = agent.handle_message(req.text)
    return response

@app.get("/session/{session_id}/audit")
def get_audit(session_id: str):
    if session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return audit_trail.for_session(session_id)

@app.get("/session/{session_id}/audit/summary")
def get_audit_summary(session_id: str):
    if session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return audit_trail.summary_by_actor(session_id)

@app.get("/session/{session_id}/audit/needs-review")
def get_audit_review(session_id: str):
    if session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return audit_trail.export_for_review(session_id)

@app.get("/catalog/search")
def search_catalog(text: str):
    results = discovery.query(text=text)
    return results
