"""
app.py
SmartStock - Main Application Entry Point
Created by Anand D

Run with: streamlit run app.py
"""

import streamlit as st
import logging
import os
import sys

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

from database.connection import initialize_database, DB_PATH
from services.report_service import get_dashboard_metrics, get_sales_trend_daily, get_best_selling_products
from services.inventory_service import get_low_stock_products

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="SmartStock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# CUSTOM CSS
# ------------------------------------------------------------------
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1f2e 0%, #252d3d 100%); }
    [data-testid="stSidebar"] .stMarkdown p { color: #a0aec0; font-size: 0.82rem; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e2a3a, #253347);
        border: 1px solid #2d3f55;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    [data-testid="metric-container"] label { color: #7ecffc !important; font-size: 0.78rem !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #ffffff !important; font-size: 1.6rem !important; font-weight: 700;
    }

    /* Page title */
    .main-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(90deg, #7ecffc, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title { color: #a0aec0; font-size: 0.95rem; margin-bottom: 1.5rem; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #7ecffc;
        border-left: 3px solid #7ecffc; padding-left: 0.6rem;
        margin: 1.5rem 0 0.8rem;
    }

    /* Alert boxes */
    .alert-warning {
        background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4);
        border-radius: 8px; padding: 0.6rem 1rem; color: #fbbf24;
        margin: 0.5rem 0;
    }
    .alert-danger {
        background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4);
        border-radius: 8px; padding: 0.6rem 1rem; color: #f87171;
        margin: 0.5rem 0;
    }
    .alert-success {
        background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4);
        border-radius: 8px; padding: 0.6rem 1rem; color: #34d399;
        margin: 0.5rem 0;
    }

    /* Table styling */
    .stDataFrame { border-radius: 10px; overflow: hidden; }

    /* Badge */
    .badge-ok      { color: #34d399; font-weight: 600; }
    .badge-low     { color: #fbbf24; font-weight: 600; }
    .badge-out     { color: #f87171; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# DATABASE INITIALIZATION (runs once per session)
# ------------------------------------------------------------------
if "db_initialized" not in st.session_state:
    try:
        initialize_database()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")
        st.stop()

# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0;'>
        <div style='font-size:2.5rem'>📦</div>
        <div style='font-size:1.3rem; font-weight:800;
                    background:linear-gradient(90deg,#7ecffc,#a78bfa);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
            SmartStock
        </div>
        <div style='color:#64748b; font-size:0.75rem;'>Inventory Management System</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown("**📋 Navigation**")
    st.markdown("Use the pages in the sidebar above to navigate.")
    st.divider()
    st.markdown("**🗄️ Database**")
    st.markdown(f"`{os.path.basename(DB_PATH)}`")
    if os.path.exists(DB_PATH):
        size_kb = os.path.getsize(DB_PATH) / 1024
        st.markdown(f"Size: `{size_kb:.1f} KB`")
    st.divider()
    st.markdown(
        "<div style='color:#475569;font-size:0.72rem;text-align:center'>"
        "Created by <strong style='color:#7ecffc;'>Anand D</strong><br>"
        "MCA Academic Mini-Project<br>SQLite · Python · Streamlit"
        "</div>",
        unsafe_allow_html=True
    )

# ------------------------------------------------------------------
# DASHBOARD PAGE
# ------------------------------------------------------------------
st.markdown('<div class="main-title">📦 SmartStock Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Inventory, Sales & Stock Management System · Created by Anand D</div>',
            unsafe_allow_html=True)

# KPI Metrics
try:
    metrics = get_dashboard_metrics()
except Exception as e:
    st.error(f"Could not load metrics: {e}")
    metrics = {}

col1, col2, col3, col4 = st.columns(4)
col1.metric("🛍️ Total Products",    metrics.get("total_products", 0))
col2.metric("🗂️ Categories",         metrics.get("total_categories", 0))
col3.metric("🏭 Suppliers",           metrics.get("total_suppliers", 0))
col4.metric("👥 Customers",           metrics.get("total_customers", 0))

col5, col6, col7, col8 = st.columns(4)
col5.metric("📦 Units in Stock",     f"{metrics.get('total_units', 0):,}")
col6.metric("⚠️ Low Stock Items",    metrics.get("low_stock", 0))
col7.metric("💰 Today's Revenue",    f"₹{metrics.get('today_revenue', 0):,.2f}")
col8.metric("📈 Month Revenue",      f"₹{metrics.get('month_revenue', 0):,.2f}")

st.divider()

# Charts row
col_chart1, col_chart2 = st.columns([3, 2])

with col_chart1:
    st.markdown('<div class="section-header">📈 Sales Trend (Last 30 Days)</div>',
                unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        trend_data = get_sales_trend_daily(30)
        if trend_data:
            dates   = [r["sale_date"]  for r in trend_data]
            revenue = [r["revenue"]    for r in trend_data]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=revenue, mode="lines+markers",
                name="Revenue",
                line=dict(color="#7ecffc", width=2.5),
                marker=dict(size=6, color="#7ecffc"),
                fill="tozeroy",
                fillcolor="rgba(126,207,252,0.1)"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, color="#475569"),
                yaxis=dict(showgrid=True, gridcolor="#1e2a3a", tickprefix="₹", color="#475569"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data available for the past 30 days.")
    except Exception as e:
        st.warning(f"Chart unavailable: {e}")

with col_chart2:
    st.markdown('<div class="section-header">🏆 Best Selling Products</div>',
                unsafe_allow_html=True)
    try:
        best = get_best_selling_products(limit=5)
        if best:
            import plotly.express as px
            import pandas as pd
            df_best = pd.DataFrame(best)
            fig2 = px.bar(
                df_best, x="units_sold", y="product_name",
                orientation="h",
                color="units_sold",
                color_continuous_scale=["#253347", "#7ecffc"],
                labels={"units_sold": "Units", "product_name": ""}
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No sales data yet.")
    except Exception as e:
        st.warning(f"Chart unavailable: {e}")

st.divider()

# Low stock alert + Recent info
col_low, col_stats = st.columns([2, 1])

with col_low:
    st.markdown('<div class="section-header">⚠️ Low Stock Alerts</div>', unsafe_allow_html=True)
    try:
        low = get_low_stock_products()
        if low:
            import pandas as pd
            df_low = pd.DataFrame(low[:10])
            df_low = df_low[["product_name", "sku", "category_name",
                              "quantity_in_stock", "reorder_level", "shortage"]]
            df_low.columns = ["Product", "SKU", "Category",
                               "In Stock", "Reorder Level", "Shortage"]
            st.dataframe(df_low, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="alert-success">✅ All products are above reorder levels.</div>',
                        unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not load low stock: {e}")

with col_stats:
    st.markdown('<div class="section-header">📊 Quick Stats</div>', unsafe_allow_html=True)
    st.info(f"🛒 Today's Sales: **{metrics.get('today_sales_count', 0)}** transactions")
    st.info(f"📅 Month Sales: **{metrics.get('month_sales_count', 0)}** transactions")
    st.warning(f"⚠️ Low Stock: **{metrics.get('low_stock', 0)}** items")
    if metrics.get("out_of_stock", 0) > 0:
        st.error(f"🚫 Out of Stock: **{metrics.get('out_of_stock', 0)}** items")

st.divider()
st.markdown(
    "<div style='text-align:center;color:#475569;font-size:0.78rem;'>"
    "SmartStock · MCA Academic Mini-Project · "
    "<strong style='color:#7ecffc;'>Created by Anand D</strong> · "
    "Built with SQLite + Python + Streamlit"
    "</div>",
    unsafe_allow_html=True
)
