"""
pages/5_Purchases.py
SmartStock - Purchase Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.purchase_service import (
    create_purchase, get_all_purchases, get_purchase_details
)
from services.supplier_service import get_all_suppliers
from services.product_service import get_all_products

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Purchases | SmartStock", page_icon="🛒", layout="wide")
st.markdown("## 🛒 Purchase Management")
st.caption("Record purchases from suppliers · Stock updated automatically by database trigger · Created by Anand D")

tab_new, tab_list, tab_detail = st.tabs(
    ["➕ New Purchase", "📋 Purchase History", "🔍 Purchase Detail"]
)

# ------------------------------------------------------------------
# TAB: NEW PURCHASE
# ------------------------------------------------------------------
with tab_new:
    st.subheader("Record New Purchase")
    st.info("ℹ️ Stock increases automatically via the database trigger "
            "`trg_purchase_item_stock_increase` when items are saved.")

    sups  = get_all_suppliers()
    prods = get_all_products()

    if not sups:
        st.warning("⚠️ Please add suppliers before creating purchases.")
    elif not prods:
        st.warning("⚠️ Please add products before creating purchases.")
    else:
        sup_opts = {s["supplier_name"]: s["supplier_id"] for s in sups}
        prod_opts = {f"[{p['sku']}] {p['product_name']}": p for p in prods}

        with st.form("new_purchase_form"):
            c1, c2 = st.columns(2)
            sel_sup  = c1.selectbox("Supplier *", list(sup_opts.keys()))
            pdate    = c2.date_input("Purchase Date *", value=date.today())
            notes    = st.text_input("Notes (optional)")

            st.markdown("**📦 Purchase Items**")
            st.caption("Add up to 10 product lines")

            items_data = []
            num_items = st.number_input("Number of Product Lines", min_value=1,
                                         max_value=10, value=1, step=1)
            for i in range(int(num_items)):
                st.markdown(f"---\n**Line {i+1}**")
                lc1, lc2, lc3 = st.columns([3, 1, 1])
                sel_prod = lc1.selectbox(f"Product", list(prod_opts.keys()),
                                          key=f"p_prod_{i}")
                qty  = lc2.number_input("Qty", min_value=1, value=1, step=1,
                                         key=f"p_qty_{i}")
                cost = lc3.number_input("Unit Cost (₹)", min_value=0.0, value=0.0,
                                         step=0.5, format="%.2f", key=f"p_cost_{i}")
                items_data.append((sel_prod, qty, cost))

            submitted = st.form_submit_button("✅ Save Purchase", type="primary")

        if submitted:
            try:
                items = [
                    {
                        "product_id": prod_opts[sp]["product_id"],
                        "quantity":   qty,
                        "unit_cost":  cost
                    }
                    for sp, qty, cost in items_data
                    if cost > 0
                ]
                if not items:
                    st.error("❌ Enter at least one item with cost > 0.")
                else:
                    pid = create_purchase(
                        sup_opts[sel_sup], str(pdate), items, notes
                    )
                    total = sum(i["quantity"] * i["unit_cost"] for i in items)
                    st.success(
                        f"✅ Purchase #{pid} saved! "
                        f"Total: ₹{total:,.2f} · "
                        f"Stock updated automatically by trigger."
                    )
            except ValueError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")

# ------------------------------------------------------------------
# TAB: PURCHASE HISTORY
# ------------------------------------------------------------------
with tab_list:
    st.subheader("Purchase History")
    c1, c2, c3 = st.columns(3)
    sups_f = get_all_suppliers()
    sup_opts_f = {"All": None}
    sup_opts_f.update({s["supplier_name"]: s["supplier_id"] for s in sups_f})
    sel_sup_f = c1.selectbox("Filter by Supplier", list(sup_opts_f.keys()), key="ph_sup")
    start_f = c2.date_input("From Date", value=None, key="ph_start")
    end_f   = c3.date_input("To Date",   value=None, key="ph_end")

    purchases = get_all_purchases(
        supplier_id=sup_opts_f.get(sel_sup_f),
        start_date=str(start_f) if start_f else None,
        end_date=str(end_f)   if end_f   else None,
    )
    if purchases:
        df = pd.DataFrame(purchases)
        df_disp = df[["purchase_id","purchase_date","supplier_name",
                       "total_amount","item_count","status"]].copy()
        df_disp.columns = ["ID","Date","Supplier","Total (₹)","Items","Status"]
        df_disp["Total (₹)"] = df_disp["Total (₹)"].apply(lambda x: f"₹{x:,.2f}")
        st.success(f"{len(purchases)} purchase(s)")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        total_spent = sum(p["total_amount"] for p in purchases)
        st.metric("Total Expenditure", f"₹{total_spent:,.2f}")
        st.download_button("⬇️ Export CSV", df_disp.to_csv(index=False), "purchases.csv")
    else:
        st.info("No purchases found.")

# ------------------------------------------------------------------
# TAB: DETAIL
# ------------------------------------------------------------------
with tab_detail:
    st.subheader("View Purchase Details")
    all_p = get_all_purchases()
    if all_p:
        p_opts = {f"#{p['purchase_id']} — {p['purchase_date']} — {p['supplier_name']}":
                  p["purchase_id"] for p in all_p}
        sel_p = st.selectbox("Select Purchase", list(p_opts.keys()))
        pid   = p_opts[sel_p]
        detail = get_purchase_details(pid)
        if detail:
            h = detail["header"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Supplier",  h["supplier_name"])
            c2.metric("Date",      h["purchase_date"])
            c3.metric("Total",     f"₹{h['total_amount']:,.2f}")
            st.markdown(f"**Status:** `{h['status']}`")
            if h.get("notes"):
                st.markdown(f"**Notes:** {h['notes']}")
            st.divider()
            items_df = pd.DataFrame(detail["items"])
            items_df = items_df[["product_name","sku","quantity","unit_cost","line_total"]]
            items_df.columns = ["Product","SKU","Qty","Unit Cost (₹)","Line Total (₹)"]
            items_df["Unit Cost (₹)"]  = items_df["Unit Cost (₹)"].apply(lambda x: f"₹{x:,.2f}")
            items_df["Line Total (₹)"] = items_df["Line Total (₹)"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(items_df, use_container_width=True, hide_index=True)
    else:
        st.info("No purchases available.")
