"""
pages/7_Inventory.py
SmartStock - Inventory Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.inventory_service import (
    get_current_stock_levels,
    get_low_stock_products,
    get_inventory_movements,
    get_stock_valuation_summary,
    get_out_of_stock_products
)

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Inventory | SmartStock", page_icon="📦", layout="wide")
st.markdown("## 📦 Inventory Management")
st.caption("Track stock levels, valuation, and movement history · Created by Anand D")

tab_stock, tab_low, tab_valuation, tab_movements = st.tabs([
    "📊 Stock Levels", "⚠️ Low Stock", "💰 Valuation", "📜 Movement Ledger"
])

# ------------------------------------------------------------------
# TAB 1: STOCK LEVELS
# ------------------------------------------------------------------
with tab_stock:
    st.subheader("Current Stock Levels")
    search = st.text_input("🔍 Search product or SKU", key="inv_search")

    try:
        stocks = get_current_stock_levels(search=search)
    except Exception as e:
        st.error(f"Error loading stock: {e}")
        stocks = []

    if stocks:
        df = pd.DataFrame(stocks)

        # Status badge column
        def stock_status(row):
            if row["quantity_in_stock"] <= 0:
                return "🔴 OUT"
            elif row["quantity_in_stock"] <= row["reorder_level"]:
                return "🟡 LOW"
            else:
                return "🟢 OK"

        df["Status"] = df.apply(stock_status, axis=1)
        df_disp = df[["product_name","sku","category_name","supplier_name",
                       "quantity_in_stock","reorder_level","selling_price","Status"]].copy()
        df_disp.columns = ["Product","SKU","Category","Supplier",
                            "In Stock","Reorder Level","Selling Price (₹)","Status"]
        df_disp["Selling Price (₹)"] = df_disp["Selling Price (₹)"].apply(
            lambda x: f"₹{x:,.2f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Products", len(df))
        col2.metric("Low / Out of Stock",
                    len(df[df["quantity_in_stock"] <= df["reorder_level"]]))
        col3.metric("Total Units",
                    f"{df['quantity_in_stock'].sum():,}")

        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", df_disp.to_csv(index=False), "stock_levels.csv")
    else:
        st.info("No products found.")

# ------------------------------------------------------------------
# TAB 2: LOW STOCK
# ------------------------------------------------------------------
with tab_low:
    st.subheader("Low Stock & Out of Stock Alerts")
    try:
        low   = get_low_stock_products()
        out   = get_out_of_stock_products()
    except Exception as e:
        st.error(f"Error: {e}")
        low, out = [], []

    if out:
        st.error(f"🚫 **{len(out)} product(s) are OUT OF STOCK**")
        df_out = pd.DataFrame(out)[["product_name","sku","category_name",
                                     "reorder_level","supplier_name"]]
        df_out.columns = ["Product","SKU","Category","Reorder Level","Supplier"]
        st.dataframe(df_out, use_container_width=True, hide_index=True)
        st.divider()

    if low:
        st.warning(f"⚠️ **{len(low)} product(s) are below reorder level**")
        df_low = pd.DataFrame(low)[["product_name","sku","category_name",
                                      "quantity_in_stock","reorder_level","shortage","supplier_name"]]
        df_low.columns = ["Product","SKU","Category","In Stock","Reorder Level","Shortage","Supplier"]
        st.dataframe(df_low, use_container_width=True, hide_index=True)

        # Suggest reorder quantities
        st.subheader("📋 Suggested Reorder List")
        reorder = []
        for row in low:
            target = max(row["reorder_level"] * 2, row["reorder_level"] + 10)
            reorder.append({
                "Product": row["product_name"],
                "SKU": row["sku"],
                "Supplier": row["supplier_name"],
                "Current Stock": row["quantity_in_stock"],
                "Reorder Level": row["reorder_level"],
                "Suggested Order Qty": max(0, target - row["quantity_in_stock"])
            })
        df_reorder = pd.DataFrame(reorder)
        st.dataframe(df_reorder, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Reorder List", df_reorder.to_csv(index=False), "reorder_list.csv")
    else:
        st.success("✅ All products are above reorder levels.")

# ------------------------------------------------------------------
# TAB 3: VALUATION
# ------------------------------------------------------------------
with tab_valuation:
    st.subheader("Stock Valuation Summary")
    try:
        val = get_stock_valuation_summary()
    except Exception as e:
        st.error(f"Error: {e}")
        val = []

    if val:
        df_val = pd.DataFrame(val)
        total_cost  = df_val["cost_value"].sum()
        total_sell  = df_val["sell_value"].sum()
        total_units = df_val["total_units"].sum()
        potential_profit = total_sell - total_cost

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Units",            f"{total_units:,}")
        c2.metric("Stock Cost Value",        f"₹{total_cost:,.2f}")
        c3.metric("Stock Retail Value",      f"₹{total_sell:,.2f}")
        c4.metric("Potential Gross Profit",  f"₹{potential_profit:,.2f}")

        st.divider()
        df_disp = df_val[["category_name","total_products","total_units",
                           "cost_value","sell_value"]].copy()
        df_disp.columns = ["Category","Products","Units","Cost Value (₹)","Retail Value (₹)"]
        df_disp["Cost Value (₹)"]   = df_disp["Cost Value (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_disp["Retail Value (₹)"] = df_disp["Retail Value (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        # Plotly pie chart
        try:
            import plotly.express as px
            fig = px.pie(df_val, names="category_name", values="sell_value",
                         title="Stock Value Distribution by Category",
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#a0aec0",
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
    else:
        st.info("No stock data available.")

# ------------------------------------------------------------------
# TAB 4: MOVEMENT LEDGER
# ------------------------------------------------------------------
with tab_movements:
    st.subheader("Inventory Movement Ledger")
    st.caption("All stock increases (purchases) and decreases (sales) and adjustments.")

    try:
        movements = get_inventory_movements()
    except Exception as e:
        st.error(f"Error: {e}")
        movements = []

    if movements:
        df_m = pd.DataFrame(movements)
        df_disp = df_m[["movement_date","product_name","sku",
                          "movement_type","quantity_change",
                          "reference_type","notes"]].copy()
        df_disp.columns = ["Date","Product","SKU","Type","Qty Change","Reference","Notes"]
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Ledger", df_disp.to_csv(index=False), "movements.csv")
    else:
        st.info("No movement records found.")

