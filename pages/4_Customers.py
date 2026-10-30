"""
pages/4_Customers.py
SmartStock - Customer Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.customer_service import (
    get_all_customers, get_customer_by_id,
    create_customer, update_customer, delete_customer,
    get_customer_sales, get_customer_sales_summary
)

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Customers | SmartStock", page_icon="👥", layout="wide")
st.markdown("## 👥 Customer Management")
st.caption("Manage customers and view purchase history · Created by Anand D")

search = st.text_input("🔍 Search Customers")
tab_list, tab_add, tab_edit, tab_history = st.tabs(
    ["📋 Customer List", "➕ Add Customer", "✏️ Edit / Delete", "📜 Purchase History"]
)

with tab_list:
    custs = get_all_customers(search=search)
    if custs:
        df = pd.DataFrame(custs)[["customer_name","phone","email","created_at"]]
        df.columns = ["Name","Phone","Email","Registered At"]
        st.success(f"{len(custs)} customer(s)")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", df.to_csv(index=False), "customers.csv")
    else:
        st.info("No customers found.")

with tab_add:
    st.subheader("Register New Customer")
    with st.form("add_cust_form"):
        c1, c2 = st.columns(2)
        c_name  = c1.text_input("Customer Name *")
        c_phone = c2.text_input("Phone")
        c_email = c1.text_input("Email")
        if st.form_submit_button("➕ Register Customer", type="primary"):
            try:
                cid = create_customer(c_name, c_phone, c_email)
                st.success(f"✅ Customer '{c_name}' registered (ID: {cid})")
            except ValueError as e:
                st.error(f"❌ {e}")

with tab_edit:
    all_custs = get_all_customers()
    if all_custs:
        opts = {f"[{c['customer_id']}] {c['customer_name']}": c["customer_id"]
                for c in all_custs}
        sel_l  = st.selectbox("Select Customer", list(opts.keys()))
        sel_id = opts[sel_l]
        cust   = get_customer_by_id(sel_id)
        if cust:
            with st.form("edit_cust_form"):
                c1, c2 = st.columns(2)
                e_n = c1.text_input("Name",  value=cust["customer_name"])
                e_p = c2.text_input("Phone", value=cust["phone"] or "")
                e_e = c1.text_input("Email", value=cust["email"] or "")
                if st.form_submit_button("💾 Save", type="primary"):
                    try:
                        update_customer(sel_id, e_n, e_p, e_e)
                        st.success("✅ Updated.")
                    except ValueError as e:
                        st.error(f"❌ {e}")
            st.divider()
            if st.button("🗑️ Delete Customer", type="secondary"):
                try:
                    delete_customer(sel_id)
                    st.success("✅ Deleted.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")

with tab_history:
    all_custs2 = get_all_customers()
    if all_custs2:
        opts2 = {c["customer_name"]: c["customer_id"] for c in all_custs2}
        sel_c2 = st.selectbox("Select Customer", list(opts2.keys()), key="cust_hist")
        cid2   = opts2[sel_c2]

        summary = get_customer_sales_summary(cid2)
        if summary:
            s = summary[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Orders",  s["total_orders"])
            c2.metric("Total Spent",   f"₹{s['total_spent']:,.2f}")
            c3.metric("Avg Order",     f"₹{s['avg_order_value']:,.2f}")

        sales = get_customer_sales(cid2)
        if sales:
            df_s = pd.DataFrame(sales)
            df_s = df_s[["sale_id","sale_date","total_amount","payment_method","status","item_count"]]
            df_s.columns = ["ID","Date","Amount (₹)","Payment","Status","Items"]
            df_s["Amount (₹)"] = df_s["Amount (₹)"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df_s, use_container_width=True, hide_index=True)
        else:
            st.info("No purchases found for this customer.")
