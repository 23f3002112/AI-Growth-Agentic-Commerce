import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Agentic Commerce", page_icon="🛍️", layout="wide")

# ----------------- SESSION STATE INIT -----------------
if "session_id" not in st.session_state:
    try:
        res = requests.post(f"{API_BASE_URL}/session")
        if res.status_code == 200:
            st.session_state["session_id"] = res.json()["session_id"]
            st.session_state["messages"] = []
            st.session_state["cart"] = []
            st.session_state["audit_trail"] = []
        else:
            st.error("Failed to initialize backend session. Is FastAPI running?")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend (http://localhost:8000). Please start FastAPI via `uvicorn api:app --reload`.")
        st.stop()

# ----------------- SIDEBAR (CART) -----------------
with st.sidebar:
    st.title("🛒 Your Cart")
    
    if not st.session_state.get("cart"):
        st.info("Cart is currently empty.")
    else:
        for idx, sku in enumerate(st.session_state["cart"]):
            st.markdown(f"**Item {idx + 1}:** `{sku}`")
            
    st.divider()
    st.caption(f"Session ID: {st.session_state.get('session_id', 'None')}")

# ----------------- MAIN AREA -----------------
st.title("🛍️ Agentic Commerce Dashboard")
st.caption("Track 01: Next-Gen AI Growth Agent (Clean & Professional)")

tab_chat, tab_audit = st.tabs(["💬 Chat Interface", "🛡️ Audit Trail"])

# ------------ TAB 1: CHAT ------------
with tab_chat:
    # Render Chat History natively
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    if prompt := st.chat_input("Type here (e.g. 'black t-shirt under 2000' or 'checkout')..."):
        
        # Display user message immediately
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Call Backend API
        session_id = st.session_state["session_id"]
        with st.spinner("Agent is thinking..."):
            try:
                res = requests.post(f"{API_BASE_URL}/session/{session_id}/message", json={"text": prompt})
                if res.status_code == 200:
                    data = res.json()
                    reply = data["reply"]
                    cart = data["cart"]
                    
                    # Update local state
                    st.session_state["messages"].append({"role": "assistant", "content": reply})
                    st.session_state["cart"] = cart
                    
                    # Fetch latest audit trail
                    audit_res = requests.get(f"{API_BASE_URL}/session/{session_id}/audit")
                    if audit_res.status_code == 200:
                        st.session_state["audit_trail"] = audit_res.json()
                        
                    st.rerun() # Force UI refresh for cart and chat
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except requests.exceptions.ConnectionError:
                st.error("Connection to backend lost.")

# ------------ TAB 2: AUDIT TRAIL ------------
with tab_audit:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Live Transaction & Agent Logs")
    with col2:
        needs_review_only = st.checkbox("Show Needs Review Only", value=False)
        
    audit_data = []
    if needs_review_only:
        try:
            res = requests.get(f"{API_BASE_URL}/session/{st.session_state['session_id']}/audit/needs-review")
            if res.status_code == 200:
                audit_data = res.json()
        except:
            pass
    else:
        audit_data = st.session_state.get("audit_trail", [])
        
    if not audit_data:
        st.info("No audit events logged yet.")
    else:
        for event in reversed(audit_data):
            status = event['status']
            time_str = event['timestamp'].split('T')[1][:8]
            
            # Format the message clearly
            message = f"**[{time_str}] @{event['actor'].upper()}** &rarr; `{event['action']}`\n\n{event['reason']}"
            
            # Use Streamlit's native alerting for a very clean, professional look
            if status == "ok":
                st.success(message, icon="✅")
            elif status == "needs_approval":
                st.warning(message, icon="⚠️")
            else:  # error or blocked
                st.error(message, icon="🚫")
