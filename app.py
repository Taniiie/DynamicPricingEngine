# app.py
import streamlit as st
import pandas as pd
import json
import time
import threading
import queue
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from engine.violation_checker import ViolationChecker

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Dynamic Pricing Engine — Cyberpunk", layout="wide", initial_sidebar_state="expanded")
REC_FILE = Path("configs/recommendations.jsonl")
FEATURES_FILE = Path("data/stream_sample.jsonl")
WS_URL = st.secrets.get("WS_URL", "ws://localhost:8765")  # websocket server (optional)
# OPENAI_KEY removed - using Local RAG (Ollama)

# ----------------------------
# CSS / THEME (Cyberpunk)
# ----------------------------
CYBER_CSS = """
<style>
/* Animated Gradient Background */
body {
    background: linear-gradient(-45deg, #FF3CAC, #784BA0, #2B86C5, #ee0979, #ff6a00);
    background-size: 400% 400%;
    animation: gradient 15s ease infinite;
    color: white;
}
@keyframes gradient {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

/* Sidebar Glassmorphism */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.2);
}

/* Glass Panels (Header Box) */
.block {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-left: 8px solid #ff00cc; /* Neon Pink Strip */
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    margin-bottom: 24px;
}

/* Metrics (Stats Boxes) - Colorful & Bright */
.metric {
    background: linear-gradient(135deg, #FF00CC 0%, #333399 100%); /* Pink to Blue */
    padding: 20px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.3);
    text-align: center;
    box-shadow: 0 4px 15px rgba(255, 0, 204, 0.4);
    transition: all 0.3s ease;
    color: white !important;
}

.metric:nth-of-type(2) { background: linear-gradient(135deg, #FF9966 0%, #FF5E62 100%); /* Orange */ } 
/* Note: nth-of-type might not hit if not siblings, so sticking to a universal vibrant look or inline styles later if needed. 
   Let's use a generic vibrant gradient for all for now, or use a pseudo-random effect in Python. */
   
.metric:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 10px 25px rgba(255, 0, 204, 0.6);
    background: linear-gradient(135deg, #00ebff 0%, #005c97 100%); /* Cyan on hover */
}

.kpi { 
    font-size: 42px; 
    font-weight: 900; 
    color: #ffffff; 
    text-shadow: 0 2px 5px rgba(0,0,0,0.5);
    margin-bottom: 5px;
}
.kpi-sub { 
    font-size: 14px; 
    color: #e0e0e0; 
    font-weight: 700; 
    text-transform: uppercase; 
    letter-spacing: 1.5px; 
    opacity: 0.9;
}
.table-row-violation { background: rgba(255, 0, 80, 0.3); }
h1, h2, h3 { text-shadow: 2px 2px 4px rgba(0,0,0,0.4); }
</style>
"""
st.markdown(CYBER_CSS, unsafe_allow_html=True)

# ----------------------------
# Globals & helper utilities
# ----------------------------
q = queue.Queue()  # queue for incoming websocket messages

@st.cache_resource
def get_policy_checker():
    return ViolationChecker()

checker = get_policy_checker()

def read_recent_recs(n=200) -> pd.DataFrame:
    if not REC_FILE.exists():
        return pd.DataFrame()
    rows = []
    with open(REC_FILE, "r") as fh:
        lines = fh.readlines()[-n:]
    for line in lines:
        try:
            r = json.loads(line)
            rows.append(r)
        except:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp")

# ----------------------------
# WebSocket client (background)
# ----------------------------
def ws_client_runner(ws_url: str, queue_obj: queue.Queue):
    """
    Background thread that connects to websocket server and pushes messages to queue.
    Uses simple websocket-client library.
    """
    try:
        import websocket
    except Exception:
        # websocket-client not installed; fallback to polling if necessary
        return

    def on_message(ws, message):
        try:
            obj = json.loads(message)
            queue_obj.put(obj)
        except Exception:
            pass

    def on_error(ws, error):
        print("WS error:", error)

    def on_close(ws, close_status_code, close_msg):
        print("WS closed", close_status_code, close_msg)

    def on_open(ws):
        print("WS opened to", ws_url)

    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    # blocking call that runs forever
    ws.run_forever()

def start_ws_client_once(url=WS_URL):
    # start background thread
    if "ws_thread_started" not in st.session_state:
        t = threading.Thread(target=ws_client_runner, args=(url, q), daemon=True)
        t.start()
        st.session_state["ws_thread_started"] = True

# ----------------------------
# UI: Left navigation bar
# ----------------------------
with st.sidebar:
    st.markdown("<h2 style='color:#ff00cc'>⚡ Dynamic Pricing</h2>", unsafe_allow_html=True)
    st.markdown("<div class='small-muted'>Real-time · Hybrid · RAG policy checks</div>", unsafe_allow_html=True)
    nav = st.radio("Navigation", ["Overview", "SKU Dashboard", "Heatmaps & Anomalies", "AI Agent", "Settings"], index=0)
    st.markdown("---")
    st.markdown("**Live Controls**")
    auto_refresh = st.checkbox("Auto-Refresh UI", value=True)
    refresh_secs = st.slider("Refresh interval (sec)", 1, 10, 2)
    st.markdown("---")
    st.markdown("**Theme**")
    theme_choice = st.selectbox("Choose theme", ["Cyberpunk", "Default"], index=0)
    st.markdown("---")
    st.markdown("Powered by Pathway • RAG • Hybrid ML", unsafe_allow_html=True)

# ----------------------------
# Start websocket client (attempt) and polling fallback
# ----------------------------
start_ws_client_once()

# helper to ingest queue items into session_state list
if "live_recs" not in st.session_state:
    st.session_state["live_recs"] = []

def ingest_ws_queue():
    pushed = False
    while not q.empty():
        obj = q.get_nowait()
        st.session_state["live_recs"].append(obj)
        pushed = True
    return pushed

# polling fallback: check file for new lines
def poll_file_for_updates():
    # load most recent row from recommendations file and append to session_state if new
    if not REC_FILE.exists():
        return False
    try:
        with open(REC_FILE, "r") as fh:
            lines = fh.readlines()
        if not lines:
            return False
        last = json.loads(lines[-1])
        last_id = last.get("_internal_id") or f"{last.get('sku')}-{last.get('timestamp')}"
        if "last_seen_id" not in st.session_state or st.session_state["last_seen_id"] != last_id:
            st.session_state["last_seen_id"] = last_id
            st.session_state["live_recs"].append(last)
            return True
    except Exception:
        return False
    return False

# ----------------------------
# Pages
# ----------------------------
def page_overview():
    st.markdown("<div class='block'><h3>Overview</h3><p class='small-muted'>Live feed, model health, and policy dashboard</p></div>", unsafe_allow_html=True)
    # KPIs
    df = read_recent_recs(500)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total = len(df)
        st.markdown(f"<div class='metric'><div class='kpi'>{total}</div><div class='kpi-sub'>Recommendations (recent)</div></div>", unsafe_allow_html=True)
    with col2:
        skus = df['sku'].nunique() if not df.empty else 0
        st.markdown(f"<div class='metric'><div class='kpi'>{skus}</div><div class='kpi-sub'>Active SKUs</div></div>", unsafe_allow_html=True)
    with col3:
        blocked = df[ df['approved'] == False ].shape[0] if not df.empty else 0
        st.markdown(f"<div class='metric'><div class='kpi' style='color:#ff6b6b'>{blocked}</div><div class='kpi-sub'>Policy Violations</div></div>", unsafe_allow_html=True)
    with col4:
        last_ts = df['timestamp'].max() if not df.empty and 'timestamp' in df.columns else None
        last_text = last_ts.strftime('%Y-%m-%d %H:%M:%S') if last_ts is not None else "n/a"
        st.markdown(f"<div class='metric'><div class='kpi'>{last_text}</div><div class='kpi-sub'>Last update</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Recent activity (live)**")
    # show live entries from session_state (populated by WS or polling)
    ingest_ws_queue()
    if st.session_state["live_recs"]:
        live_df = pd.DataFrame(st.session_state["live_recs"][-50:])
        if 'timestamp' in live_df.columns:
            live_df['timestamp'] = pd.to_datetime(live_df['timestamp'])
        st.dataframe(live_df.sort_values('timestamp', ascending=False).head(20), use_container_width=True)
    else:
        st.info("No live recommendations yet. Run pipeline or start ws_server.py")

def page_sku_dashboard():
    st.markdown("<div class='block'><h3>SKU-wise Comparison</h3><p class='small-muted'>Compare pricing and trends per SKU</p></div>", unsafe_allow_html=True)
    df = read_recent_recs(1000)
    if df.empty:
        st.info("No data. Start the pipeline or simulator.")
        return
    sku_list = df['sku'].unique().tolist()
    sku = st.selectbox("Select SKU", sku_list)
    sku_df = df[df['sku'] == sku].sort_values('timestamp')
    # time series
    st.markdown("#### Price vs Time")
    st.line_chart(sku_df.set_index('timestamp')['proposed_price'])
    # conversion-like metric: confidence as proxy
    st.markdown("#### Confidence (proxy for conversion probability)")
    st.area_chart(sku_df.set_index('timestamp')['confidence'])
    # table with last 20 recommendations
    st.markdown("#### Recent Recommendations for SKU")
    display_df = sku_df[['timestamp', 'base_price', 'proposed_price', 'confidence', 'approved', 'violations']].tail(20).copy()
    
    # Sanitize 'violations' to be strings to avoid Arrow struct/non-struct errors
    display_df['violations'] = display_df['violations'].apply(lambda x: str(x) if isinstance(x, (list, dict)) else str(x))
    
    st.dataframe(display_df, use_container_width=True)

def page_heatmaps():
    st.markdown("<div class='block'><h3>Heatmaps & Anomaly Detection</h3><p class='small-muted'>Price heatmaps and simple anomaly detection</p></div>", unsafe_allow_html=True)
    df = read_recent_recs(2000)
    if df.empty:
        st.info("No data yet.")
        return
    # build pivot table: sku x hour -> avg proposed_price
    df['hour'] = df['timestamp'].dt.hour
    pivot = df.groupby(['sku', 'hour'])['proposed_price'].mean().unstack(fill_value=0)
    st.markdown("#### Price heatmap (SKU x Hour)")
    st.dataframe(pivot.style.background_gradient(cmap='magma'), use_container_width=True)

    # anomaly detection (z-score over last window)
    st.markdown("#### Simple Anomaly Detection (z-score on price changes)")
    out = []
    for sku in df['sku'].unique():
        s = df[df['sku'] == sku].sort_values('timestamp')
        if s.shape[0] < 5: continue
        s = s.assign(pct_change = s['proposed_price'].pct_change().fillna(0))
        mean = s['pct_change'].mean()
        std = s['pct_change'].std() if s['pct_change'].std() > 0 else 1e-6
        s['z'] = (s['pct_change'] - mean)/std
        # anomalies if abs(z) > 3
        anomalies = s[ s['z'].abs() > 3 ]
        for _, r in anomalies.iterrows():
            out.append({"timestamp": r['timestamp'], "sku": sku, "proposed_price": r['proposed_price'], "z": float(r['z'])})
    if out:
        a_df = pd.DataFrame(out).sort_values('timestamp', ascending=False)
        st.dataframe(a_df.head(50), use_container_width=True)
    else:
        st.success("No anomalies detected in recent window.")

def page_ai_agent():
    st.markdown("<div class='block'><h3>AI Conversational Agent</h3><p class='small-muted'>Ask the system about pricing decisions or policies</p></div>", unsafe_allow_html=True)
    # Chat messages state
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    # chat UI
    chat_col1, chat_col2 = st.columns([3,1])
    with chat_col1:
        user_input = st.text_input("Ask the AI (pricing / policy / explain):", key="ai_input")
    with chat_col2:
        if st.button("Send"):
            if user_input:
                st.session_state['chat_history'].append({"role":"user", "text":user_input, "ts": datetime.utcnow().isoformat()})
                # call policy checker RAG for an explainability answer
                with st.spinner("Thinking (Ollama + RAG)..."):
                    # Use RAG directly
                    try:
                        # checker is ViolationChecker, checker.rag is LocalRAG
                        rag_resp = checker.rag.ask(user_input)
                        answer = rag_resp.get("explanation") or str(rag_resp)
                        # include evidence
                        evidence_ids = rag_resp.get("evidence_passages", [])
                        # mock evidence structure for UI compatibility or update UI
                        evidence = [{"passage_id": pid, "text_snippet": "See doc...", "score": 1.0} for pid in evidence_ids]
                        
                        st.session_state['chat_history'].append({"role":"assistant", "text": answer, "evidence": evidence, "ts": datetime.utcnow().isoformat()})
                    except Exception as e:
                        st.session_state['chat_history'].append({"role":"assistant", "text": f"Failed to call RAG: {e}", "ts": datetime.utcnow().isoformat()})

    # render chat
    for msg in reversed(st.session_state['chat_history'][-10:]):
        if msg["role"] == "user":
            st.markdown(f"<div style='text-align:right; padding:8px; margin:4px; border-radius:8px; background:linear-gradient(90deg,#051429,#06203a);'>{msg['text']}</div>", unsafe_allow_html=True)
        else:
            ev_html = ""
            if msg.get("evidence"):
                ev_html = "<details><summary>Evidence</summary><ul>"
                for e in msg["evidence"][:3]:
                    ev_html += f"<li><b>{e.get('passage_id')}</b>: {e.get('text_snippet')[:150]} (score: {e.get('score')})</li>"
                ev_html += "</ul></details>"
            st.markdown(f"<div style='text-align:left; padding:10px; margin:6px; border-radius:8px; background:linear-gradient(90deg,#08102a,#0b1a3a);'><b>Assistant:</b> {msg['text']}<br/>{ev_html}</div>", unsafe_allow_html=True)

def page_settings():
    st.markdown("<div class='block'><h3>Settings & Diagnostics</h3></div>", unsafe_allow_html=True)
    st.markdown("**WebSocket Server URL**")
    st.write(WS_URL)
    st.markdown("**Data files**")
    st.write(f"- Recommendations file: `{REC_FILE}`")
    st.write(f"- Features file: `{FEATURES_FILE}`")
    st.markdown("**Local RAG & Compliance**")
    st.write("Using Local RAG Engine (Ollama - llama3.2). Ensure Ollama is running (`ollama serve`).")

# ----------------------------
# Page routing
# ----------------------------
if nav == "Overview":
    page_overview()
elif nav == "SKU Dashboard":
    page_sku_dashboard()
elif nav == "Heatmaps & Anomalies":
    page_heatmaps()
elif nav == "AI Agent":
    page_ai_agent()
elif nav == "Settings":
    page_settings()

# ----------------------------
# Live update loop (non-blocking; Streamlit rerun)
# ----------------------------
# ingest queue items if any
ingest_ws_queue()

# fallback polling
if poll_file_for_updates():
    pass

if auto_refresh:
    # schedule a rerun after refresh_secs
    time.sleep(refresh_secs)
    st.rerun()
