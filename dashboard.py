"""
Veridi Logistics — Delivery Performance Dashboard
Run locally:   streamlit run dashboard.py
Deploy free:   push to GitHub, then connect the repo at https://share.streamlit.io

Expects these three CSVs in the SAME folder as this script (exported automatically
by veridi_logistics_audit.ipynb):
    - veridi_master_dataset.csv
    - veridi_state_summary.csv
    - veridi_risk_matrix.csv   (optional — dashboard degrades gracefully without it)
"""

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Veridi Logistics — Delivery Performance Audit",
    page_icon=" ",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Data loading (cached so the app doesn't reload CSVs on every interaction)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    master = pd.read_csv("veridi_master_dataset.csv")
    state_summary = pd.read_csv("veridi_state_summary.csv")
    try:
        risk_matrix = pd.read_csv("veridi_risk_matrix.csv")
    except FileNotFoundError:
        risk_matrix = pd.DataFrame()
    return master, state_summary, risk_matrix


try:
    master, state_summary, risk_matrix = load_data()
except FileNotFoundError as e:
    st.error(
        "Couldn't find the required CSVs. Make sure `veridi_master_dataset.csv` and "
        "`veridi_state_summary.csv` (exported by the notebook) are in the same folder "
        f"as this script.\n\nDetails: {e}"
    )
    st.stop()

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("Veridi Logistics — Delivery Performance Audit")
st.caption(
    "Are we failing specific regions, or is this a nationwide problem? "
    "An audit of the Olist e-commerce delivery data."
)

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")
all_states = sorted(master["customer_state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect(
    "Filter by state (leave empty = all states)", options=all_states, default=[]
)

filtered = master.copy()
if selected_states:
    filtered = filtered[filtered["customer_state"].isin(selected_states)]

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data source:** [Olist Brazilian E-Commerce Dataset]"
    "(https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)"
)

# ----------------------------------------------------------------------------
# KPI row
# ----------------------------------------------------------------------------
delivered_mask = filtered["delivery_status"].isin(["On Time", "Late", "Super Late"])
delivered = filtered[delivered_mask]

total_orders = len(filtered)
late_rate = (
    delivered["delivery_status"].isin(["Late", "Super Late"]).mean() * 100
    if len(delivered) else 0
)
undelivered_rate = (
    (filtered["delivery_status"] == "Undelivered (canceled/unavailable)").mean() * 100
    if len(filtered) else 0
)
avg_review = filtered["review_score"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Orders", f"{total_orders:,}")
col2.metric("Late or Super Late", f"{late_rate:.1f}%")
col3.metric("Never Delivered", f"{undelivered_rate:.1f}%")
col4.metric("Avg Review Score", f"{avg_review:.2f} / 5" if pd.notna(avg_review) else "N/A")

st.markdown("---")

# ----------------------------------------------------------------------------
# Row 1: Delivery outcome breakdown + Review score by status
# ----------------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Delivery Outcome Breakdown")
    status_order = ["On Time", "Late", "Super Late", "Undelivered (canceled/unavailable)"]
    status_counts = (
        filtered["delivery_status"].value_counts().reindex(status_order).fillna(0).reset_index()
    )
    status_counts.columns = ["Status", "Orders"]
    fig1 = px.bar(
        status_counts, x="Status", y="Orders", color="Status",
        color_discrete_map={
            "On Time": "#2C7A55", "Late": "#F9A825",
            "Super Late": "#F96167", "Undelivered (canceled/unavailable)": "#9E9E9E",
        },
        text="Orders",
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(showlegend=False, yaxis_title="", xaxis_title="")
    st.plotly_chart(fig1, width='stretch')

with c2:
    st.subheader("Average Review Score by Delivery Status")
    review_by_status = (
        delivered.groupby("delivery_status")["review_score"]
        .mean()
        .reindex(["On Time", "Late", "Super Late"])
        .reset_index()
    )
    review_by_status.columns = ["Status", "Avg Review Score"]
    fig2 = px.bar(
        review_by_status, x="Status", y="Avg Review Score", color="Status",
        color_discrete_map={"On Time": "#2C7A55", "Late": "#F9A825", "Super Late": "#F96167"},
        text="Avg Review Score", range_y=[0, 5],
    )
    fig2.update_traces(texttemplate="%{y:.2f}", textposition="outside")
    fig2.update_layout(showlegend=False, yaxis_title="", xaxis_title="")
    st.plotly_chart(fig2, width='stretch')

st.markdown("---")

# ----------------------------------------------------------------------------
# Row 2: Late % by state (the "regional vs nationwide" question)
# ----------------------------------------------------------------------------
st.subheader("Late Delivery Rate by State")
st.caption("States with fewer than 30 orders are excluded to avoid noisy small-sample rates.")

ss = state_summary[state_summary["total_orders"] >= 30].sort_values("pct_late", ascending=True)
national_avg = (
    delivered["delivery_status"].isin(["Late", "Super Late"]).mean() * 100
    if len(delivered) else None
)

fig3 = px.bar(
    ss, x="pct_late", y="customer_state", orientation="h",
    labels={"pct_late": "% Late", "customer_state": "State"},
    color="pct_late", color_continuous_scale="Reds",
)
fig3.update_layout(coloraxis_showscale=False, height=max(400, 28 * len(ss)))
fig3.update_traces(hovertemplate="%{y}: %{x:.1%}<extra></extra>")
fig3.update_xaxes(tickformat=".0%")
if national_avg is not None:
    fig3.add_vline(
        x=national_avg / 100, line_dash="dash", line_color="black",
        annotation_text=f"National avg: {national_avg:.1f}%", annotation_position="top",
    )
st.plotly_chart(fig3, width='stretch')

st.markdown("---")

# ----------------------------------------------------------------------------
# Row 3: Business Impact Risk Matrix (Candidate's Choice)
# ----------------------------------------------------------------------------
st.subheader("Business Impact Risk Matrix — Priority Segments")
st.caption(
    "Combines lateness rate, review-score penalty, and order volume into a single "
    "priority score, so ops knows exactly where to focus first."
)

if not risk_matrix.empty:
    top_n = st.slider("Show top N segments", min_value=5, max_value=min(50, len(risk_matrix)), value=15)
    top_risk = risk_matrix.sort_values("priority_score", ascending=False).head(top_n)

    fig4 = px.bar(
        top_risk.sort_values("priority_score"),
        x="priority_score",
        y=top_risk.sort_values("priority_score").apply(
            lambda r: f"{r['customer_state']} – {r['primary_category_en']}", axis=1
        ),
        orientation="h",
        labels={"priority_score": "Priority Score", "y": ""},
        color="priority_score", color_continuous_scale="Reds",
    )
    fig4.update_layout(coloraxis_showscale=False, height=max(400, 28 * top_n))
    st.plotly_chart(fig4, width='stretch')

    st.dataframe(
        top_risk[["customer_state", "primary_category_en", "order_volume",
                  "pct_late", "review_penalty", "priority_score"]]
        .rename(columns={
            "customer_state": "State", "primary_category_en": "Category",
            "order_volume": "Orders", "pct_late": "% Late",
            "review_penalty": "Review Penalty", "priority_score": "Priority Score",
        })
        .style.format({"% Late": "{:.1%}", "Review Penalty": "{:.2f}", "Priority Score": "{:.2f}"}),
        width='stretch',
    )
else:
    st.info(
        "Risk matrix data not found — this section requires `veridi_risk_matrix.csv`, "
        "which the notebook only exports if `olist_order_items_dataset.csv` was available."
    )

st.markdown("---")
st.caption(
    "Built from the Olist Brazilian E-Commerce Dataset. "
    "Source notebook: veridi_logistics_audit.ipynb"
)
