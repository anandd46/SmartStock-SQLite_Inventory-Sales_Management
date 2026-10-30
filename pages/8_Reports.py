"""
pages/8_Reports.py
SmartStock - Business Reports Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.report_service import (
    get_daily_sales_report,
    get_monthly_sales_report,
    get_category_sales_report,
    get_best_selling_products,
    get_supplier_purchase_report,
    get_sales_trend_daily,
    get_sales_trend_monthly,
    get_profit_by_category
)

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Reports | SmartStock", page_icon="📈", layout="wide")
st.markdown("## 📈 Business Reports")
st.caption("SQL-driven sales, purchase, and performance reports · Created by Anand D")

tab_daily, tab_monthly, tab_cat, tab_best, tab_supplier, tab_profit, tab_trend = st.tabs([
    "📅 Daily", "📆 Monthly", "🗂️ By Category",
    "🏆 Best Sellers", "🏭 Supplier Spend", "💰 Profitability", "📊 Trends"
])

# ------------------------------------------------------------------
# TAB: DAILY REPORT
# ------------------------------------------------------------------
with tab_daily:
    st.subheader("Daily Sales Report")
    
    # Sensible default date range based on available sales
    try:
        from database.connection import get_connection, close_connection
        _conn = get_connection()
        _row = _conn.execute("SELECT MIN(sale_date), MAX(sale_date) FROM sales WHERE status='COMPLETED'").fetchone()
        close_connection(_conn)
        if _row and _row[1]:
            latest_sale = date.fromisoformat(_row[1])
            earliest_sale = date.fromisoformat(_row[0])
            if date.today() - latest_sale > timedelta(days=30):
                def_end = latest_sale
                def_start = max(earliest_sale, latest_sale - timedelta(days=30))
            else:
                def_end = date.today()
                def_start = date.today() - timedelta(days=30)
        else:
            def_end = date.today()
            def_start = date.today() - timedelta(days=30)
    except Exception:
        def_end = date.today()
        def_start = date.today() - timedelta(days=30)

    c1, c2 = st.columns(2)
    d_start = c1.date_input("From Date", value=def_start)
    d_end   = c2.date_input("To Date",   value=def_end)

    try:
        daily = get_daily_sales_report(str(d_start), str(d_end))
    except Exception as e:
        st.error(f"Error: {e}")
        daily = []

    if daily:
        df = pd.DataFrame(daily)
        total_rev  = df["revenue"].sum()
        total_txns = df["transactions"].sum()
        avg_rev    = df["revenue"].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Revenue",       f"₹{total_rev:,.2f}")
        c2.metric("Total Transactions",  int(total_txns))
        c3.metric("Avg Daily Revenue",   f"₹{avg_rev:,.2f}")

        df_disp = df[["sale_date","transactions","items_sold","revenue","avg_order_value"]].copy()
        df_disp.columns = ["Date","Transactions","Items Sold","Revenue (₹)","Avg Order (₹)"]
        df_disp["Revenue (₹)"]   = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "₹0.00")
        df_disp["Avg Order (₹)"] = df_disp["Avg Order (₹)"].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "₹0.00")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["sale_date"], y=df["revenue"],
                marker_color="#7ecffc", name="Revenue"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=300,
                xaxis=dict(showgrid=False), yaxis=dict(tickprefix="₹")
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "daily_report.csv")
    else:
        st.info("No sales in selected date range.")

# ------------------------------------------------------------------
# TAB: MONTHLY REPORT
# ------------------------------------------------------------------
with tab_monthly:
    st.subheader("Monthly Sales Report")
    def_year = def_end.year if "def_end" in locals() else date.today().year
    year_sel = st.number_input("Year", min_value=2020, max_value=2035,
                                value=def_year, step=1)
    try:
        monthly = get_monthly_sales_report(int(year_sel))
    except Exception as e:
        st.error(f"Error: {e}")
        monthly = []

    if monthly:
        df = pd.DataFrame(monthly)
        c1, c2, c3 = st.columns(3)
        c1.metric("Annual Revenue",      f"₹{df['revenue'].sum():,.2f}")
        c2.metric("Best Month",          df.loc[df['revenue'].idxmax(), 'month_name'])
        c3.metric("Total Transactions",  int(df['transactions'].sum()))

        df_disp = df[["month_name","transactions","items_sold","revenue","avg_order_value"]].copy()
        df_disp.columns = ["Month","Transactions","Items Sold","Revenue (₹)","Avg Order (₹)"]
        df_disp["Revenue (₹)"]   = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Avg Order (₹)"] = df_disp["Avg Order (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["month_name"], y=df["revenue"],
                marker_color="#a78bfa", name="Monthly Revenue"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=300,
                xaxis=dict(showgrid=False), yaxis=dict(tickprefix="₹")
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "monthly_report.csv")
    else:
        st.info(f"No sales data for {year_sel}.")

# ------------------------------------------------------------------
# TAB: CATEGORY REPORT
# ------------------------------------------------------------------
with tab_cat:
    st.subheader("Category-Wise Sales Summary")
    try:
        cats = get_category_sales_report()
    except Exception as e:
        st.error(f"Error: {e}")
        cats = []

    if cats:
        df = pd.DataFrame(cats)
        df_disp = df[["category_name","total_transactions","total_items_sold",
                       "total_revenue","avg_order_value"]].copy()
        df_disp.columns = ["Category","Transactions","Items Sold","Revenue (₹)","Avg Order (₹)"]
        df_disp["Revenue (₹)"]   = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Avg Order (₹)"] = df_disp["Avg Order (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        try:
            import plotly.express as px
            fig = px.treemap(df, path=["category_name"], values="total_revenue",
                              color="total_revenue",
                              color_continuous_scale=["#1e2a3a", "#7ecffc"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350,
                               font_color="#a0aec0")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "category_report.csv")
    else:
        st.info("No category sales data yet.")

# ------------------------------------------------------------------
# TAB: BEST SELLERS
# ------------------------------------------------------------------
with tab_best:
    st.subheader("Best Selling Products")
    limit = st.slider("Show top N products", 5, 50, 10)
    try:
        best = get_best_selling_products(limit=limit)
    except Exception as e:
        st.error(f"Error: {e}")
        best = []

    if best:
        df = pd.DataFrame(best)
        df_disp = df[["rank","product_name","sku","category_name",
                       "units_sold","revenue","transactions"]].copy()
        df_disp.columns = ["Rank","Product","SKU","Category","Units Sold","Revenue (₹)","Txns"]
        df_disp["Revenue (₹)"] = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        try:
            import plotly.express as px
            fig = px.bar(df.head(15), x="units_sold", y="product_name",
                          orientation="h",
                          color="revenue",
                          color_continuous_scale=["#253347","#7ecffc"],
                          labels={"units_sold":"Units Sold","product_name":""})
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=400,
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "best_sellers.csv")
    else:
        st.info("No sales data yet.")

# ------------------------------------------------------------------
# TAB: SUPPLIER SPEND
# ------------------------------------------------------------------
with tab_supplier:
    st.subheader("Supplier Purchase Report")
    try:
        sup_data = get_supplier_purchase_report()
    except Exception as e:
        st.error(f"Error: {e}")
        sup_data = []

    if sup_data:
        df = pd.DataFrame(sup_data)
        df_disp = df[["supplier_name","total_purchases","total_items","total_spent",
                       "last_purchase"]].copy()
        df_disp.columns = ["Supplier","Purchases","Items","Total Spent (₹)","Last Purchase"]
        df_disp["Total Spent (₹)"] = df_disp["Total Spent (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        try:
            import plotly.express as px
            fig = px.pie(df, names="supplier_name", values="total_spent",
                          title="Spend by Supplier",
                          color_discrete_sequence=px.colors.sequential.Purples_r)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aec0", height=350)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "supplier_report.csv")
    else:
        st.info("No purchase data yet.")

# ------------------------------------------------------------------
# TAB: PROFITABILITY
# ------------------------------------------------------------------
with tab_profit:
    st.subheader("Profitability by Category")
    try:
        profit_data = get_profit_by_category()
    except Exception as e:
        st.error(f"Error: {e}")
        profit_data = []

    if profit_data:
        df = pd.DataFrame(profit_data)
        total_rev  = df["revenue"].sum()
        total_cost = df["cost"].sum()
        gross      = df["gross_profit"].sum()
        margin_pct = (gross / total_rev * 100) if total_rev else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue",    f"₹{total_rev:,.2f}")
        c2.metric("Total Cost",       f"₹{total_cost:,.2f}")
        c3.metric("Gross Profit",     f"₹{gross:,.2f}")
        c4.metric("Gross Margin",     f"{margin_pct:.1f}%")

        df_disp = df[["category_name","units_sold","revenue","cost",
                       "gross_profit","margin_pct"]].copy()
        df_disp.columns = ["Category","Units","Revenue (₹)","Cost (₹)","Gross Profit (₹)","Margin %"]
        df_disp["Revenue (₹)"]      = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Cost (₹)"]         = df_disp["Cost (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Gross Profit (₹)"] = df_disp["Gross Profit (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Margin %"]         = df_disp["Margin %"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export", df_disp.to_csv(index=False), "profitability.csv")
    else:
        st.info("No data available.")

# ------------------------------------------------------------------
# TAB: TRENDS
# ------------------------------------------------------------------
with tab_trend:
    st.subheader("Sales Trends")
    view = st.radio("View", ["Daily (90 Days)", "Monthly"], horizontal=True)
    try:
        if view == "Daily (90 Days)":
            trend = get_sales_trend_daily(90)
            x_col, x_label = "sale_date", "Date"
        else:
            trend = get_sales_trend_monthly()
            x_col, x_label = "period", "Month"
    except Exception as e:
        st.error(f"Error: {e}")
        trend = []

    if trend:
        df = pd.DataFrame(trend)
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df["revenue"],
                mode="lines+markers", name="Revenue",
                line=dict(color="#7ecffc", width=2),
                fill="tozeroy", fillcolor="rgba(126,207,252,0.08)"
            ))
            fig.add_trace(go.Bar(
                x=df[x_col], y=df["transactions"],
                name="Transactions", yaxis="y2",
                marker_color="rgba(167,139,250,0.4)"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0", height=380,
                xaxis=dict(showgrid=False, title=x_label),
                yaxis=dict(title="Revenue (₹)", tickprefix="₹", showgrid=True,
                            gridcolor="#1e2a3a"),
                yaxis2=dict(title="Transactions", overlaying="y", side="right",
                             showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as ex:
            st.warning(f"Chart error: {ex}")

        df_disp = df.rename(columns={x_col: "Period", "revenue": "Revenue (₹)",
                                      "transactions": "Transactions"})
        df_disp["Revenue (₹)"] = df_disp["Revenue (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
    else:
        st.info("No trend data available.")
