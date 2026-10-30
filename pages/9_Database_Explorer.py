"""
pages/9_Database_Explorer.py
SmartStock - Database Explorer Page
Created by Anand D

Allows viewing table schemas, running safe read-only queries, and inspecting data.
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import initialize_database, get_connection, close_connection

if "db_initialized" not in st.session_state:
    initialize_database()
    st.session_state["db_initialized"] = True

st.set_page_config(page_title="DB Explorer | SmartStock", page_icon="🗄️", layout="wide")
st.markdown("## 🗄️ Database Explorer")
st.caption("Inspect tables, schemas, indexes, triggers, and run custom queries · Created by Anand D")

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def safe_query(sql: str) -> tuple[pd.DataFrame | None, str | None]:
    """Execute a SELECT-only query and return (DataFrame, error_string)."""
    sql_strip = sql.strip().upper()
    # Only allow SELECT and PRAGMA statements for safety
    allowed = ("SELECT", "PRAGMA", "WITH", "EXPLAIN")
    if not any(sql_strip.startswith(k) for k in allowed):
        return None, "⛔ Only SELECT, PRAGMA, WITH, and EXPLAIN statements are permitted."
    conn = get_connection()
    try:
        rows = conn.execute(sql).fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[d[0] for d in conn.execute(sql).description])
            return df, None
        else:
            return pd.DataFrame(), None
    except Exception as e:
        return None, str(e)
    finally:
        close_connection(conn)


def get_all_tables() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        close_connection(conn)


def get_table_info(table: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_table_row_count(table: str) -> int:
    conn = get_connection()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
    finally:
        close_connection(conn)


def get_indexes() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_triggers() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


# ------------------------------------------------------------------
# TABS
# ------------------------------------------------------------------
tab_tables, tab_schema, tab_indexes, tab_triggers, tab_query, tab_sql_lab = st.tabs([
    "📋 Tables", "🔍 Schema", "🗂️ Indexes", "⚡ Triggers",
    "🔎 Table Browser", "💻 SQL Lab"
])

# --- TABLES ---
with tab_tables:
    st.subheader("Database Tables Overview")
    tables = get_all_tables()
    if tables:
        overview = []
        for t in tables:
            info = get_table_info(t)
            count = get_table_row_count(t)
            overview.append({
                "Table": t,
                "Columns": len(info),
                "Rows": count
            })
        df_ov = pd.DataFrame(overview)
        st.dataframe(df_ov, use_container_width=True, hide_index=True)
        st.info(f"📊 Total: **{len(tables)} tables** | "
                f"**{df_ov['Rows'].sum()} rows** across all tables")
    else:
        st.warning("No tables found. Database may not be initialized.")

# --- SCHEMA ---
with tab_schema:
    st.subheader("Table Schema Inspector")
    tables = get_all_tables()
    if tables:
        sel_table = st.selectbox("Select Table", tables)
        info = get_table_info(sel_table)
        if info:
            df_info = pd.DataFrame(info)[["cid","name","type","notnull","dflt_value","pk"]]
            df_info.columns = ["#","Column","Type","NOT NULL","Default","Primary Key"]
            df_info["Primary Key"] = df_info["Primary Key"].apply(lambda x: "✅" if x else "")
            df_info["NOT NULL"]    = df_info["NOT NULL"].apply(lambda x: "✅" if x else "")
            st.dataframe(df_info, use_container_width=True, hide_index=True)

        # Show CREATE statement
        conn = get_connection()
        try:
            row = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (sel_table,)
            ).fetchone()
            if row and row[0]:
                st.subheader("CREATE Statement")
                st.code(row[0], language="sql")
        finally:
            close_connection(conn)

        # Preview data
        st.subheader(f"Sample Data — {sel_table}")
        conn2 = get_connection()
        try:
            rows = conn2.execute(f"SELECT * FROM '{sel_table}' LIMIT 20").fetchall()
            if rows:
                df_preview = pd.DataFrame(rows, columns=[d[0] for d in conn2.execute(
                    f"SELECT * FROM '{sel_table}' LIMIT 0").description])
                st.dataframe(df_preview, use_container_width=True, hide_index=True)
            else:
                st.info("Table is empty.")
        except Exception as e:
            st.error(f"Preview error: {e}")
        finally:
            close_connection(conn2)

# --- INDEXES ---
with tab_indexes:
    st.subheader("Database Indexes")
    indexes = get_indexes()
    if indexes:
        for idx in indexes:
            with st.expander(f"🗂️ {idx['name']} (on `{idx['tbl_name']}`)"):
                if idx["sql"]:
                    st.code(idx["sql"], language="sql")
                else:
                    st.info("Auto-created index (no DDL).")
    else:
        st.info("No indexes found.")

# --- TRIGGERS ---
with tab_triggers:
    st.subheader("Database Triggers")
    triggers = get_triggers()
    if triggers:
        for trg in triggers:
            with st.expander(f"⚡ {trg['name']} (on `{trg['tbl_name']}`)"):
                if trg["sql"]:
                    st.code(trg["sql"], language="sql")
    else:
        st.warning("No triggers found. Run `initialize_database()` to apply them.")

# --- TABLE BROWSER ---
with tab_query:
    st.subheader("Table Browser")
    tables2 = get_all_tables()
    if tables2:
        sel_t = st.selectbox("Table", tables2, key="browser_table")
        limit = st.slider("Row Limit", 10, 500, 50)
        offset = st.number_input("Offset (skip rows)", min_value=0, value=0, step=10)
        try:
            conn = get_connection()
            rows = conn.execute(
                f"SELECT * FROM '{sel_t}' LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=[d[0] for d in conn.execute(
                    f"SELECT * FROM '{sel_t}' LIMIT 0").description])
                total = get_table_row_count(sel_t)
                st.caption(f"Showing rows {offset+1}–{min(offset+limit, total)} of {total}")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("⬇️ Export", df.to_csv(index=False), f"{sel_t}.csv")
            else:
                st.info("No rows found.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            close_connection(conn)

# --- SQL LAB ---
with tab_sql_lab:
    st.subheader("💻 SQL Lab — Read-Only Query Runner")
    st.warning("⚠️ Only SELECT, PRAGMA, WITH, and EXPLAIN statements are permitted for safety.")

    example_queries = {
        "-- Select an example --": "",
        "All products with stock levels": """SELECT p.product_id, p.product_name, p.sku,
       c.category_name, p.quantity_in_stock, p.reorder_level
FROM   products p
JOIN   categories c ON p.category_id = c.category_id
ORDER  BY p.product_name;""",
        "Low stock products": """SELECT product_name, sku, quantity_in_stock, reorder_level,
       (reorder_level - quantity_in_stock) AS shortage
FROM   products
WHERE  quantity_in_stock <= reorder_level
ORDER  BY shortage DESC;""",
        "Monthly sales summary": """SELECT strftime('%Y-%m', s.sale_date) AS month,
       COUNT(DISTINCT s.sale_id)   AS transactions,
       SUM(si.quantity)            AS items_sold,
       SUM(si.quantity * si.unit_price) AS revenue
FROM   sales s
JOIN   sale_items si ON s.sale_id = si.sale_id
WHERE  s.status = 'COMPLETED'
GROUP  BY month
ORDER  BY month DESC;""",
        "Best-selling products": """SELECT p.product_name, p.sku,
       SUM(si.quantity) AS units_sold,
       SUM(si.quantity * si.unit_price) AS revenue
FROM   sale_items si
JOIN   products p ON si.product_id = p.product_id
JOIN   sales s ON si.sale_id = s.sale_id
WHERE  s.status = 'COMPLETED'
GROUP  BY p.product_id
ORDER  BY units_sold DESC
LIMIT 10;""",
        "Category-wise revenue": """SELECT c.category_name,
       COUNT(DISTINCT s.sale_id) AS transactions,
       SUM(si.quantity) AS items_sold,
       ROUND(SUM(si.quantity * si.unit_price), 2) AS revenue
FROM   categories c
JOIN   products p  ON c.category_id  = p.category_id
JOIN   sale_items si ON p.product_id = si.product_id
JOIN   sales s ON si.sale_id = s.sale_id
WHERE  s.status = 'COMPLETED'
GROUP  BY c.category_id
ORDER  BY revenue DESC;""",
        "Inventory movement ledger": """SELECT im.movement_date,
       p.product_name, p.sku,
       im.movement_type, im.quantity_change,
       im.reference_type, im.notes
FROM   inventory_movements im
JOIN   products p ON im.product_id = p.product_id
ORDER  BY im.movement_date DESC
LIMIT 50;""",
        "List all triggers (PRAGMA)": "SELECT * FROM sqlite_master WHERE type='trigger';",
        "Table row counts": """SELECT name AS 'Table',
       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) AS exists_flag
FROM   sqlite_master m WHERE type='table'
ORDER  BY name;""",
    }

    sel_ex = st.selectbox("Load Example Query", list(example_queries.keys()))
    default_sql = example_queries[sel_ex]

    sql_input = st.text_area("SQL Query", value=default_sql, height=160,
                              placeholder="SELECT * FROM products LIMIT 10;")

    if st.button("▶️ Run Query", type="primary"):
        if sql_input.strip():
            df_result, err = safe_query(sql_input.strip())
            if err:
                st.error(f"❌ {err}")
            elif df_result is not None and not df_result.empty:
                st.success(f"✅ {len(df_result)} row(s) returned")
                st.dataframe(df_result, use_container_width=True, hide_index=True)
                st.download_button("⬇️ Export Results", df_result.to_csv(index=False), "query_result.csv")
            elif df_result is not None:
                st.info("Query executed successfully — no rows returned.")
        else:
            st.warning("Please enter a SQL query.")

