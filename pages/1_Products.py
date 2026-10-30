"""
pages/1_Products.py
SmartStock - Product Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.product_service import (
    get_all_products, get_product_by_id, create_product,
    update_product, delete_product, adjust_stock
)
from services.category_service import get_all_categories
from services.supplier_service import get_all_suppliers

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Products | SmartStock", page_icon="🛒", layout="wide")

st.markdown("## 🛒 Product Management")
st.caption("Add, view, search, update and manage products · Created by Anand D")

# Sidebar filters
st.sidebar.header("🔍 Filter Products")
search = st.sidebar.text_input("Search by Name / SKU")
cats   = get_all_categories()
cat_opts = {c["category_name"]: c["category_id"] for c in cats}
cat_filter = st.sidebar.selectbox("Category", ["All"] + list(cat_opts.keys()))
sups   = get_all_suppliers()
sup_opts = {s["supplier_name"]: s["supplier_id"] for s in sups}
sup_filter = st.sidebar.selectbox("Supplier", ["All"] + list(sup_opts.keys()))
low_only = st.sidebar.checkbox("Low Stock Only")

cat_id = cat_opts.get(cat_filter) if cat_filter != "All" else None
sup_id = sup_opts.get(sup_filter) if sup_filter != "All" else None

tab_list, tab_add, tab_edit, tab_adjust = st.tabs(
    ["📋 Product List", "➕ Add Product", "✏️ Edit Product", "📦 Adjust Stock"]
)

# ------------------------------------------------------------------
# TAB 1: LIST
# ------------------------------------------------------------------
with tab_list:
    products = get_all_products(search=search, category_id=cat_id,
                                 supplier_id=sup_id, low_stock_only=low_only)
    if products:
        df = pd.DataFrame(products)
        display_cols = ["product_name", "sku", "category_name", "supplier_name",
                        "purchase_price", "selling_price",
                        "quantity_in_stock", "reorder_level"]
        df_display = df[display_cols].copy()
        df_display.columns = ["Product Name", "SKU", "Category", "Supplier",
                               "Purchase Price (₹)", "Selling Price (₹)",
                               "In Stock", "Reorder Level"]
        df_display["Purchase Price (₹)"] = df_display["Purchase Price (₹)"].apply(lambda x: f"₹{x:,.2f}")
        df_display["Selling Price (₹)"]  = df_display["Selling Price (₹)"].apply(lambda x: f"₹{x:,.2f}")

        st.success(f"Showing {len(products)} product(s)")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # CSV export
        csv = df_display.to_csv(index=False)
        st.download_button("⬇️ Export CSV", csv, "products.csv", "text/csv")
    else:
        st.info("No products found. Add a product using the 'Add Product' tab.")

# ------------------------------------------------------------------
# TAB 2: ADD
# ------------------------------------------------------------------
with tab_add:
    st.subheader("Add New Product")
    with st.form("add_product_form"):
        c1, c2 = st.columns(2)
        name  = c1.text_input("Product Name *")
        sku   = c2.text_input("SKU *", help="Unique stock-keeping identifier, e.g. SKU-001")
        cat   = c1.selectbox("Category *", list(cat_opts.keys()))
        sup   = c2.selectbox("Supplier", ["None"] + list(sup_opts.keys()))
        pp    = c1.number_input("Purchase Price (₹) *", min_value=0.0, step=0.5, format="%.2f")
        sp    = c2.number_input("Selling Price (₹) *",  min_value=0.0, step=0.5, format="%.2f")
        rl    = st.number_input("Reorder Level", min_value=0, value=5, step=1)
        submitted = st.form_submit_button("➕ Add Product", type="primary")

    if submitted:
        try:
            sup_id_sel = sup_opts.get(sup) if sup != "None" else None
            pid = create_product(
                name, sku, cat_opts[cat], sup_id_sel, pp, sp, rl
            )
            st.success(f"✅ Product '{name}' added successfully (ID: {pid})")
        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")

# ------------------------------------------------------------------
# TAB 3: EDIT
# ------------------------------------------------------------------
with tab_edit:
    st.subheader("Edit Existing Product")
    products_all = get_all_products()
    if products_all:
        prod_opts = {f"[{p['sku']}] {p['product_name']}": p["product_id"]
                     for p in products_all}
        selected_label = st.selectbox("Select Product to Edit", list(prod_opts.keys()))
        selected_id = prod_opts[selected_label]
        prod = get_product_by_id(selected_id)
        if prod:
            with st.form("edit_product_form"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("Product Name",    value=prod["product_name"])
                e_sku  = c2.text_input("SKU",             value=prod["sku"])
                cat_list = list(cat_opts.keys())
                cur_cat  = next((k for k, v in cat_opts.items()
                                  if v == prod["category_id"]), cat_list[0])
                e_cat  = c1.selectbox("Category", cat_list,
                                       index=cat_list.index(cur_cat))
                sup_list_e = ["None"] + list(sup_opts.keys())
                cur_sup  = next((k for k, v in sup_opts.items()
                                  if v == prod["supplier_id"]), "None")
                e_sup  = c2.selectbox("Supplier", sup_list_e,
                                       index=sup_list_e.index(cur_sup))
                e_pp   = c1.number_input("Purchase Price (₹)",
                                          value=float(prod["purchase_price"]),
                                          min_value=0.0, step=0.5, format="%.2f")
                e_sp   = c2.number_input("Selling Price (₹)",
                                          value=float(prod["selling_price"]),
                                          min_value=0.0, step=0.5, format="%.2f")
                e_rl   = st.number_input("Reorder Level",
                                          value=int(prod["reorder_level"]),
                                          min_value=0, step=1)
                save = st.form_submit_button("💾 Save Changes", type="primary")

            if save:
                try:
                    sup_id_e = sup_opts.get(e_sup) if e_sup != "None" else None
                    update_product(selected_id, e_name, e_sku,
                                   cat_opts[e_cat], sup_id_e, e_pp, e_sp, e_rl)
                    st.success("✅ Product updated successfully.")
                except ValueError as e:
                    st.error(f"❌ {e}")

            st.divider()
            st.markdown("**⚠️ Danger Zone – Delete Product**")
            st.warning("Deletion is only allowed if the product has no transaction history.")
            if st.button("🗑️ Delete This Product", type="secondary"):
                try:
                    delete_product(selected_id)
                    st.success("✅ Product deleted.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")
    else:
        st.info("No products found.")

# ------------------------------------------------------------------
# TAB 4: ADJUST STOCK
# ------------------------------------------------------------------
with tab_adjust:
    st.subheader("Manual Stock Adjustment")
    st.info("Use this for corrections, damage write-offs, or stock takes. "
            "Purchases and sales automatically update stock via triggers.")
    products_all2 = get_all_products()
    if products_all2:
        adj_opts = {f"[{p['sku']}] {p['product_name']} (Stock: {p['quantity_in_stock']})": p["product_id"]
                    for p in products_all2}
        adj_sel = st.selectbox("Select Product", list(adj_opts.keys()), key="adj_sel")
        adj_pid = adj_opts[adj_sel]
        with st.form("adjust_stock_form"):
            adj_qty = st.number_input("Quantity Change (+add / -remove)",
                                       min_value=-9999, max_value=9999, value=0, step=1)
            adj_note = st.text_input("Reason / Notes")
            adj_sub = st.form_submit_button("✅ Apply Adjustment", type="primary")
        if adj_sub:
            try:
                adjust_stock(adj_pid, adj_qty, adj_note)
                st.success(f"✅ Stock adjusted by {adj_qty:+d}")
            except ValueError as e:
                st.error(f"❌ {e}")
