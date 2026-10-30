"""
pages/3_Suppliers.py
SmartStock - Supplier Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.supplier_service import (
    get_all_suppliers, get_supplier_by_id,
    create_supplier, update_supplier, delete_supplier,
    get_supplier_purchases, get_supplier_purchase_summary
)

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Suppliers | SmartStock", page_icon="🏭", layout="wide")
st.markdown("## 🏭 Supplier Management")
st.caption("Manage suppliers and view purchase history · Created by Anand D")

search = st.text_input("🔍 Search Suppliers")
tab_list, tab_add, tab_edit, tab_history = st.tabs(
    ["📋 Supplier List", "➕ Add Supplier", "✏️ Edit / Delete", "📜 Purchase History"]
)

with tab_list:
    sups = get_all_suppliers(search=search)
    if sups:
        df = pd.DataFrame(sups)[["supplier_name","phone","email","address","created_at"]]
        df.columns = ["Name","Phone","Email","Address","Registered At"]
        st.success(f"{len(sups)} supplier(s)")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", df.to_csv(index=False), "suppliers.csv")
    else:
        st.info("No suppliers found.")

with tab_add:
    st.subheader("Register New Supplier")
    with st.form("add_sup_form"):
        c1, c2 = st.columns(2)
        s_name  = c1.text_input("Supplier Name *")
        s_phone = c2.text_input("Phone")
        s_email = c1.text_input("Email")
        s_addr  = c2.text_input("Address")
        if st.form_submit_button("➕ Register Supplier", type="primary"):
            try:
                sid = create_supplier(s_name, s_phone, s_email, s_addr)
                st.success(f"✅ Supplier '{s_name}' registered (ID: {sid})")
            except ValueError as e:
                st.error(f"❌ {e}")

with tab_edit:
    all_sups = get_all_suppliers()
    if all_sups:
        opts = {f"[{s['supplier_id']}] {s['supplier_name']}": s["supplier_id"]
                for s in all_sups}
        sel_l = st.selectbox("Select Supplier", list(opts.keys()))
        sel_id = opts[sel_l]
        sup = get_supplier_by_id(sel_id)
        if sup:
            with st.form("edit_sup_form"):
                c1, c2 = st.columns(2)
                e_n = c1.text_input("Name",    value=sup["supplier_name"])
                e_p = c2.text_input("Phone",   value=sup["phone"] or "")
                e_e = c1.text_input("Email",   value=sup["email"] or "")
                e_a = c2.text_input("Address", value=sup["address"] or "")
                if st.form_submit_button("💾 Save", type="primary"):
                    try:
                        update_supplier(sel_id, e_n, e_p, e_e, e_a)
                        st.success("✅ Updated.")
                    except ValueError as e:
                        st.error(f"❌ {e}")
            st.divider()
            if st.button("🗑️ Delete Supplier", type="secondary"):
                try:
                    delete_supplier(sel_id)
                    st.success("✅ Deleted.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")

with tab_history:
    all_sups2 = get_all_suppliers()
    if all_sups2:
        opts2 = {s["supplier_name"]: s["supplier_id"] for s in all_sups2}
        sel_s2 = st.selectbox("Select Supplier", list(opts2.keys()), key="sup_hist")
        sid2   = opts2[sel_s2]

        summary = get_supplier_purchase_summary(sid2)
        if summary:
            s = summary[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Purchases", s["total_purchases"])
            c2.metric("Total Spent",     f"₹{s['total_spent']:,.2f}")
            c3.metric("Last Purchase",   s["last_purchase"])

        purchases = get_supplier_purchases(sid2)
        if purchases:
            df_p = pd.DataFrame(purchases)
            df_p = df_p[["purchase_id","purchase_date","total_amount","status","item_count"]]
            df_p.columns = ["ID","Date","Amount (₹)","Status","Items"]
            df_p["Amount (₹)"] = df_p["Amount (₹)"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df_p, use_container_width=True, hide_index=True)
        else:
            st.info("No purchases for this supplier.")
