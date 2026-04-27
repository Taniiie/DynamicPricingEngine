import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from policy_checker import PolicyChecker

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Dynamic Pricing Engine",
    layout="wide",
    page_icon="⚡"
)

# --------------------------------------------------
# CUSTOM CSS FOR MODERN UI
# --------------------------------------------------
st.markdown("""
<style>
/* Global background */
body {
    background: linear-gradient(135deg, #0f0f0f, #1c1c1c);
}

/* Glassmorphism containers */
.block-container {
    padding-top: 1rem;
}

.glass-card {
    background: rgba(255, 255, 255, 0.06);
    padding: 1.2rem;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    backdrop-filter: blur(12px);
}

/* Metric cards */
.metric-card {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 15px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.12);
}

.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #00eaff;
}

.metric-label {
    font-size: 14px;
    color: #ccc;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.05);
    border-right: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(12px);
}

/* Tables */
[data-testid="stDataFrame"] {
    background: rgba(0,0,0,0.4) !important;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Initialize Policy Checker
# --------------------------------------------------
@st.cache_resource
def get_policy_checker():
    return PolicyChecker()

checker = get_policy_checker()

# --------------------------------------------------
# Sidebar – Policy Guardian
# --------------------------------------------------
st.sidebar.header("🛡️ Policy Guardian")
st.sidebar.caption("Ask questions based on your pricing policy database.")

user_query = st.sidebar.text_input("Ask a policy question:")
if user_query:
    with st.sidebar.spinner("Analyzing policies..."):
        response = checker.call_llm(
            f"Answer strictly using pricing policies: {user_query}"
        )
    st.sidebar.success(response)

st.sidebar.markdown("---")
refresh_rate = st.sidebar.slider("Auto-refresh (seconds)", 1, 10, 2)

# --------------------------------------------------
# Load Data
# --------------------------------------------------
REC_FILE = Path("configs/recommendations.jsonl")

def load_data():
    if not REC_FILE.exists():
        return pd.DataFrame()

    data = []
    # Read last 120 lines for history
    try:
        with open(REC_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-120:]:
                try:
                    data.append(json.loads(line))
                except:
                    continue
    except Exception:
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    return df

# --------------------------------------------------
# Main UI
# --------------------------------------------------
st.markdown("""
# ⚡ Dynamic Pricing Engine  
### Real-Time · Hybrid Model · Policy-Aware RAG
""")

df = load_data()

# --------------------------------------------------
# Live Status
# --------------------------------------------------
status = "🟢 Streaming Active" if not df.empty else "🔴 Waiting for Data"
st.markdown(f"### {status}")

# --------------------------------------------------
# Top Metric Bar
# --------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class='metric-card'>
        <div class='metric-label'>Model Type</div>
        <div class='metric-value'>Hybrid Engine</div>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    last = df.iloc[-1]
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Latest SKU</div>
            <div class='metric-value'>{last.get('sku', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Latest Price</div>
            <div class='metric-value'>${last.get('proposed_price', 0):.2f}</div>
        </div>
        """, unsafe_allow_html=True)

# --------------------------------------------------
# Charts Section
# --------------------------------------------------
st.markdown("### 📈 Price Trends (Live)")

if not df.empty:
    top_skus = df['sku'].unique()[:4]
    chart_df = df[df['sku'].isin(top_skus)]
    st.line_chart(
        chart_df,
        x='timestamp',
        y='proposed_price',
        color='sku',
        height=300
    )
else:
    st.info("Waiting for streaming data...")

# --------------------------------------------------
# Live Recommendations Table
# --------------------------------------------------
st.markdown("### 📄 Live Pricing Recommendations")
if not df.empty:
    display_cols = [
        'timestamp', 'sku', 'base_price', 'proposed_price',
        'confidence', 'approved', 'violations'
    ]
    st.dataframe(
        df[display_cols].sort_values('timestamp', ascending=False).head(20),
        use_container_width=True
    )

# --------------------------------------------------
# Policy Violations
# --------------------------------------------------
st.markdown("### 🛑 Policy Violations")

violations = df[df['approved'] == False] if not df.empty else pd.DataFrame()
if not violations.empty:
    st.error(f"{len(violations)} Violations Detected")
    st.dataframe(
        violations[['timestamp', 'sku', 'violations', 'explanation']].tail(10),
        use_container_width=True
    )
else:
    st.success("No violations detected.")

# --------------------------------------------------
# Auto Refresh
# --------------------------------------------------
time.sleep(refresh_rate)
st.experimental_set_query_params()
st.rerun()
