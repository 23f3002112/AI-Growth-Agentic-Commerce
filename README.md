# AI Growth & Agentic Commerce — Unified Agent
Razorpay AI Buildathon 2026 — Track 01

## Problem
Track 01 asks for an agent that either grows a merchant's revenue, or makes
the merchant transactable by an AI buyer end to end. Rather than picking one
of the four example directions, this project implements **all four** on top
of one shared foundation: an agent-readable catalog, an explicit transaction
gate, and a unified audit trail. Every other layer builds on that shared core.

## The bar this is built to clear
> "Every money action explainable, bounded and gated. Show the audit trail
> and one failure handled gracefully."

Concretely, this means:
- **Explainable** — every decision (match, upsell, discount, block, approval)
  is logged with a plain-English reason, not just a status code.
- **Bounded** — hard-coded limits (`MAX_AUTO_APPROVE_AMOUNT`,
  `MAX_DAILY_AGENT_SPEND`, `MAX_ITEMS_PER_ORDER`, `MAX_AUTO_DISCOUNT_PERCENT`)
  that the agent cannot reason its way around.
- **Gated** — nothing reaches the payment layer without passing
  `backend/gate.py` first.
- **One failure handled gracefully** — the out-of-stock -> substitute flow in
  `orchestrator.py` Demo 2 is the explicit, reproducible example of this.

## Architecture

```
catalog/generate_catalog.py   -> raw merchant product data (synthetic)
catalog/schema.py             -> converts raw catalog to agent-readable format
        |
        v
backend/discovery.py          -> [Direction: Agent-Readable Catalog]
                                  structured query interface an AI buyer agent calls
        |
        v
backend/upsell.py             -> [Direction: Upsell & Cross-sell Agent]
                                  rule-based, explainable suggestions
        |
        v
backend/gate.py                -> hard-coded bounds, approval routing (shared by all)
        |
        v
backend/checkout.py            -> [Direction: Conversational In-App Checkout]
                                  simulated Razorpay test-mode call, graceful failure handling
        |
backend/campaign.py            -> [Direction: Campaign Orchestrator]
                                  abandoned-cart + slow-stock triggers, discount-capped
        |
        v
backend/audit.py               -> unified audit trail, used by every layer above
        |
        v
backend/orchestrator.py        -> ties everything together, runs 4 end-to-end demos
```

## How to run
```bash
cd catalog
python3 generate_catalog.py --n 60 --seed 7
python3 schema.py

cd ../backend
python3 orchestrator.py
```

## What each demo proves (from an actual run)
1. **Happy path checkout + upsell**: buyer agent queries for a black apparel
   item under ₹2000, gets an upsell suggestion (same category, similar price
   band, explained reason), gate approves (₹1549 is within the ₹5000
   auto-approve limit), payment succeeds via simulated Razorpay test-mode call.
2. **Failure handling (the required case)**: buyer wants a specific sneaker
   variant that is out of stock. Agent detects this, searches the *same
   product line* first for an in-stock substitute, finds one, and completes
   checkout — all logged with explicit reasoning at each step, no silent
   guessing and no crash.
3. **Gate blocking**: a 3-item cart totaling ₹22,397 exceeds the ₹5,000
   auto-approve limit. The gate blocks automatic execution and routes to
   `needs_approval` — this is what "bounded and gated" looks like when it
   actually fires, not just as a design claim.
4. **Campaign orchestrator**: an idle high-value cart triggers a 10% recovery
   offer (capped at the 15% ceiling), and a slow-moving stock item (0 sales
   in 45 days) triggers a 12% promo — both logged with the exact trigger
   condition that fired.

Every event above is captured in `backend/full_audit_trail.json` — this file
alone should answer any judge question of "why did the agent do that."

## What broke / lesson learned
Initial version of `find_substitutes()` searched the entire catalog by price
similarity first, which sometimes suggested a completely different product
(e.g. sandals instead of sneakers) just because the price matched. Fixed by
requiring the search to check the **same `product_id`** (same product line,
different variant) before falling back to a cross-category price-based
match — this is a meaningfully better substitute and is what a real customer
would actually expect.

## 7-Part Milestone Plan
1. Problem scoping & repo skeleton
2. Synthetic catalog generator + agent-readable schema conversion — DONE
3. Discovery layer (structured query interface) — DONE
4. Gate + audit trail (shared infrastructure) — DONE
5. Checkout, upsell, and campaign orchestrator layers — DONE, demonstrated end-to-end
6. Backend API (FastAPI) + UI dashboard (chat-style checkout demo + audit trail viewer)
7. Deployment, real Razorpay test-mode API integration (replacing the
   `_call_razorpay_test_mode()` stub), evaluation write-up, pitch video

## Next steps (Milestones 6-7, not yet built)
- Replace the simulated payment call in `checkout.py` with a real Razorpay
  test-mode SDK call — the gate/audit logic around it needs zero changes.
- Wrap `orchestrator.py`'s functions in a FastAPI backend with a `/chat`
  endpoint that maintains conversation state per session.
- Build a simple chat-UI frontend (Streamlit is enough) where a user types
  natural language ("I want a black t-shirt under 2000"), and the backend
  runs discovery -> upsell -> gate -> checkout, streaming back the
  conversational replies and showing the audit trail in a side panel.
