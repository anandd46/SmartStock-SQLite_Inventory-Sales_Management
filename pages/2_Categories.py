"""
pages/2_Categories.py
SmartStock - Category Management Page
Created by Anand D
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database
from services.category_service import (
    get_all_categories, get_category_by_id,
    create_category, update_category, delete_category
)

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="Categories | SmartStock", page_icon="🗂️", layout="wide")
st.markdown("## 🗂️ Category Management")
st.caption("Manage product categories · Created by Anand D")

search = st.text_input("🔍 Search Categories", placeholder="Search by name...")
tab_list, tab_add, tab_edit = st.tabs(["📋 Category List", "➕ Add Category", "✏️ Edit / Delete"])

with tab_list:
    cats = get_all_categories(search=search)
    if cats:
        df = pd.DataFrame(cats)
        df_disp = df[["category_name", "description", "product_count", "created_at"]].copy()
        df_disp.columns = ["Category Name", "Description", "Products", "Created At"]
        st.success(f"{len(cats)} categories")
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
    else:
        st.info("No categories found.")

with tab_add:
    st.subheader("Add New Category")
    with st.form("add_cat_form"):
        cat_name = st.text_input("Category Name *")
        cat_desc = st.text_area("Description", height=100)
        if st.form_submit_button("➕ Add Category", type="primary"):
            try:
                cid = create_category(cat_name, cat_desc)
                st.success(f"✅ Category '{cat_name}' added (ID: {cid})")
            except ValueError as e:
                st.error(f"❌ {e}")

with tab_edit:
    st.subheader("Edit / Delete Category")
    all_cats = get_all_categories()
    if all_cats:
        opts = {f"[{c['category_id']}] {c['category_name']}": c["category_id"]
                for c in all_cats}
        sel_label = st.selectbox("Select Category", list(opts.keys()))
        sel_id = opts[sel_label]
        cat = get_category_by_id(sel_id)
        if cat:
            with st.form("edit_cat_form"):
                e_name = st.text_input("Category Name", value=cat["category_name"])
                e_desc = st.text_area("Description",    value=cat["description"] or "")
                if st.form_submit_button("💾 Save", type="primary"):
                    try:
                        update_category(sel_id, e_name, e_desc)
                        st.success("✅ Updated.")
                    except ValueError as e:
                        st.error(f"❌ {e}")

            st.divider()
            st.warning("⚠️ Deletion fails if products use this category.")
            if st.button("🗑️ Delete Category", type="secondary"):
                try:
                    delete_category(sel_id)
                    st.success("✅ Deleted.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")
    else:
        st.info("No categories available.")
