"""
pages/6_Sales.py
SmartStock - Sales Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.sales_service import (
    create_sale, get_all_sales, get_sale_details,
    cancel_sale, check_stock_availability
)
from services.customer_service import get_all_customers
from services.product_service import get_all_products

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Sales | SmartStock", page_icon="💰", layout="wide")
st.markdown("## 💰 Sales Management")
st.caption("Record sales, view history, manage transactions · Stock updated by trigger · Created by Anand D")

tab_new, tab_list, tab_detail, tab_cancel = st.tabs(
    ["➕ New Sale", "📋 Sales History", "🔍 Sale Detail", "🚫 Cancel Sale"]
)

# ------------------------------------------------------------------
# TAB: NEW SALE
# ------------------------------------------------------------------
with tab_new:
    st.subheader("Record New Sale")
    st.info("ℹ️ Stock decreases automatically via trigger. "
            "Sale is rejected if stock is insufficient.")

    custs = get_all_customers()
    prods = get_all_products()

    if not prods:
        st.warning("⚠️ Please add products before creating sales.")
    else:
        cust_opts = {"Walk-in Customer (No Account)": None}
        cust_opts.update({c["customer_name"]: c["customer_id"] for c in custs})
        prod_opts = {f"[{p['sku']}] {p['product_name']} (Stock: {p['quantity_in_stock']})": p
                     for p in prods}

        with st.form("new_sale_form"):
            c1, c2, c3 = st.columns(3)
            sel_cust    = c1.selectbox("Customer", list(cust_opts.keys()))
            sdate       = c2.date_input("Sale Date", value=date.today())
            payment     = c3.selectbox("Payment Method", ["Cash","UPI","Card","Credit"])
            notes       = st.text_input("Notes (optional)")

            st.markdown("**🛍️ Sale Items**")
            num_items = st.number_input("Number of Product Lines",
                                        min_value=1, max_value=10, value=1, step=1)
            items_data = []
            for i in range(int(num_items)):
                st.markdown(f"---\n**Line {i+1}**")
                lc1, lc2, lc3 = st.columns([3, 1, 1])
                sel_prod = lc1.selectbox("Product", list(prod_opts.keys()),
                                          key=f"s_prod_{i}")
                qty   = lc2.number_input("Qty", min_value=1, value=1, step=1,
                                          key=f"s_qty_{i}")
                price = lc3.number_input(
                    "Unit Price (₹)", min_value=0.0,
                    value=float(prod_opts[sel_prod]["selling_price"]),
                    step=0.5, format="%.2f", key=f"s_price_{i}"
                )
                items_data.append((sel_prod, qty, price))

            submitted = st.form_submit_button("✅ Save Sale", type="primary")

        if submitted:
            # Pre-check stock (for friendly errors before trigger fires)
            stock_errors = []
            for sp, qty, price in items_data:
                p = prod_opts[sp]
                ok, stock = check_stock_availability(p["product_id"], qty)
                if not ok:
                    stock_errors.append(
                        f"'{p['product_name']}': need {qty}, have {stock}"
                    )
            if stock_errors:
                for err in stock_errors:
                    st.error(f"❌ Insufficient stock – {err}")
            else:
                try:
                    items = [
                        {
                            "product_id": prod_opts[sp]["product_id"],
                            "quantity":   qty,
                            "unit_price": price
                        }
                        for sp, qty, price in items_data
                    ]
                    cust_id = cust_opts.get(sel_cust)
                    sid = create_sale(cust_id, str(sdate), payment, items, notes)
                    total = sum(i["quantity"] * i["unit_price"] for i in items)
                    st.success(
                        f"✅ Sale #{sid} saved! Total: ₹{total:,.2f} · "
                        f"Payment: {payment} · Stock deducted by trigger."
                    )
                except ValueError as e:
                    st.error(f"❌ {e}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")

# ------------------------------------------------------------------
# TAB: SALES HISTORY
# ------------------------------------------------------------------
with tab_list:
    st.subheader("Sales History")
    c1, c2, c3, c4 = st.columns(4)
    custs_f = get_all_customers()
    cust_opts_f = {"All": None}
    cust_opts_f.update({c["customer_name"]: c["customer_id"] for c in custs_f})
    sel_c_f  = c1.selectbox("Customer", list(cust_opts_f.keys()), key="sh_cust")
    start_f  = c2.date_input("From", value=None, key="sh_start")
    end_f    = c3.date_input("To",   value=None, key="sh_end")
    pay_f    = c4.selectbox("Payment", ["All","Cash","UPI","Card","Credit"], key="sh_pay")
    status_f = st.radio("Status", ["All","COMPLETED","CANCELLED"], horizontal=True)

    sales = get_all_sales(
        customer_id=cust_opts_f.get(sel_c_f),
        start_date=str(start_f) if start_f else None,
        end_date=str(end_f)   if end_f   else None,
        payment_method=pay_f   if pay_f != "All" else None,
        status=status_f        if status_f != "All" else None,
    )
    if sales:
        df = pd.DataFrame(sales)
        df_d = df[["sale_id","sale_date","customer_name",
                   "total_amount","payment_method","item_count","status"]].copy()
        df_d.columns = ["ID","Date","Customer","Total (₹)","Payment","Items","Status"]
        df_d["Total (₹)"] = df_d["Total (₹)"].apply(lambda x: f"₹{x:,.2f}")
        total_rev = sum(s["total_amount"] for s in sales
                        if s["status"] == "COMPLETED")
        st.success(f"{len(sales)} sale(s) | Revenue: ₹{total_rev:,.2f}")
        st.dataframe(df_d, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export CSV", df_d.to_csv(index=False), "sales.csv")
    else:
        st.info("No sales found.")

# ------------------------------------------------------------------
# TAB: SALE DETAIL
# ------------------------------------------------------------------
with tab_detail:
    st.subheader("Sale Detail View")
    all_s = get_all_sales()
    if all_s:
        s_opts = {f"#{s['sale_id']} — {s['sale_date']} — {s['customer_name']}":
                  s["sale_id"] for s in all_s}
        sel_s = st.selectbox("Select Sale", list(s_opts.keys()))
        sid   = s_opts[sel_s]
        detail = get_sale_details(sid)
        if detail:
            h = detail["header"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Customer",    h["customer_name"])
            c2.metric("Date",        h["sale_date"])
            c3.metric("Total",       f"₹{h['total_amount']:,.2f}")
            c4.metric("Payment",     h["payment_method"])
            st.markdown(f"**Status:** `{h['status']}`")
            if h.get("notes"):
                st.markdown(f"**Notes:** {h['notes']}")
            st.divider()
            items_df = pd.DataFrame(detail["items"])
            items_df = items_df[["product_name","sku","quantity","unit_price","line_total"]]
            items_df.columns = ["Product","SKU","Qty","Unit Price (₹)","Line Total (₹)"]
            items_df["Unit Price (₹)"]  = items_df["Unit Price (₹)"].apply(lambda x: f"₹{x:,.2f}")
            items_df["Line Total (₹)"]  = items_df["Line Total (₹)"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(items_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# TAB: CANCEL SALE
# ------------------------------------------------------------------
with tab_cancel:
    st.subheader("Cancel a Sale")
    st.warning("⚠️ Cancellation restores stock via the database trigger. "
               "This action cannot be undone.")
    completed = get_all_sales(status="COMPLETED")
    if completed:
        c_opts = {f"#{s['sale_id']} — {s['sale_date']} — {s['customer_name']} — ₹{s['total_amount']:,.2f}":
                  s["sale_id"] for s in completed}
        sel_cancel = st.selectbox("Select Sale to Cancel", list(c_opts.keys()))
        cancel_id  = c_opts[sel_cancel]
        if st.button("🚫 Cancel This Sale", type="secondary"):
            try:
                cancel_sale(cancel_id)
                st.success(f"✅ Sale #{cancel_id} cancelled. Stock restored by trigger.")
                st.rerun()
            except ValueError as e:
                st.error(f"❌ {e}")
    else:
        st.info("No completed sales available to cancel.")
