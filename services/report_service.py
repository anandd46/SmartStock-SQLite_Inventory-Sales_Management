"""
services/report_service.py
SmartStock - Reporting Service (SQL-driven)
Created by Anand D

All reports use SQL aggregate functions, GROUP BY, and date functions.
No calculations are done in Python that belong in SQL.
"""

import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_dashboard_metrics() -> dict:
    """Return all dashboard KPI metrics in a single query batch."""
    conn = get_connection()
    try:
        today = conn.execute("SELECT date('now','localtime')").fetchone()[0]
        month_start = today[:7] + "-01"

        products_row = conn.execute("""
            SELECT COUNT(*)                                         AS total_products,
                   SUM(quantity_in_stock)                          AS total_units,
                   SUM(CASE WHEN quantity_in_stock <= reorder_level
                             AND quantity_in_stock > 0 THEN 1 ELSE 0 END) AS low_stock,
                   SUM(CASE WHEN quantity_in_stock = 0 THEN 1 ELSE 0 END) AS out_of_stock
            FROM   products
        """).fetchone()

        cats = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        sups = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        custs = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

        today_sales = conn.execute("""
            SELECT COALESCE(SUM(total_amount),0) AS revenue,
                   COUNT(*)                      AS count
            FROM   sales
            WHERE  sale_date = ? AND status='COMPLETED'
        """, (today,)).fetchone()

        month_sales = conn.execute("""
            SELECT COALESCE(SUM(total_amount),0) AS revenue,
                   COUNT(*)                      AS count
            FROM   sales
            WHERE  sale_date BETWEEN ? AND ?
              AND  status='COMPLETED'
        """, (month_start, today)).fetchone()

        return {
            "total_products":    products_row["total_products"] or 0,
            "total_units":       products_row["total_units"] or 0,
            "low_stock":         products_row["low_stock"] or 0,
            "out_of_stock":      products_row["out_of_stock"] or 0,
            "total_categories":  cats or 0,
            "total_suppliers":   sups or 0,
            "total_customers":   custs or 0,
            "today_revenue":     today_sales["revenue"] or 0,
            "today_sales_count": today_sales["count"] or 0,
            "month_revenue":     month_sales["revenue"] or 0,
            "month_sales_count": month_sales["count"] or 0,
        }
    finally:
        close_connection(conn)


def get_daily_sales_report(start_date: str, end_date: str) -> list[dict]:
    """Daily sales summary between two dates."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.sale_date,
                   COUNT(DISTINCT s.sale_id)            AS transactions,
                   SUM(si.quantity)                     AS items_sold,
                   ROUND(SUM(si.quantity*si.unit_price),2) AS revenue,
                   ROUND(AVG(s.total_amount),2)         AS avg_order_value
            FROM   sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE  s.status = 'COMPLETED'
              AND  s.sale_date BETWEEN ? AND ?
            GROUP  BY s.sale_date
            ORDER  BY s.sale_date
        """, (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_monthly_sales_report(year: int) -> list[dict]:
    """Monthly sales totals for a given year."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', s.sale_date)       AS month,
                   CASE strftime('%m', s.sale_date)
                     WHEN '01' THEN 'January'   WHEN '02' THEN 'February'
                     WHEN '03' THEN 'March'     WHEN '04' THEN 'April'
                     WHEN '05' THEN 'May'        WHEN '06' THEN 'June'
                     WHEN '07' THEN 'July'       WHEN '08' THEN 'August'
                     WHEN '09' THEN 'September'  WHEN '10' THEN 'October'
                     WHEN '11' THEN 'November'   WHEN '12' THEN 'December'
                   END                                   AS month_name,
                   COUNT(DISTINCT s.sale_id)            AS transactions,
                   SUM(si.quantity)                     AS items_sold,
                   ROUND(SUM(si.quantity*si.unit_price),2) AS revenue,
                   ROUND(AVG(s.total_amount),2)         AS avg_order_value
            FROM   sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE  s.status = 'COMPLETED'
              AND  strftime('%Y', s.sale_date) = ?
            GROUP  BY month
            ORDER  BY month
        """, (str(year),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_date_range_report(start_date: str, end_date: str) -> dict:
    conn = get_connection()
    try:
        summary = conn.execute("""
            SELECT COUNT(DISTINCT s.sale_id)    AS total_sales,
                   SUM(s.total_amount)          AS total_revenue,
                   AVG(s.total_amount)          AS avg_sale_value,
                   SUM(si.quantity)             AS total_units_sold,
                   COUNT(DISTINCT s.customer_id) AS unique_customers
            FROM   sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE  s.sale_date BETWEEN ? AND ? AND s.status='COMPLETED'
        """, (start_date, end_date)).fetchone()

        by_payment = conn.execute("""
            SELECT payment_method,
                   COUNT(*)          AS count,
                   SUM(total_amount) AS revenue
            FROM   sales
            WHERE  sale_date BETWEEN ? AND ? AND status='COMPLETED'
            GROUP BY payment_method
            ORDER BY revenue DESC
        """, (start_date, end_date)).fetchall()

        return {
            "summary": dict(summary) if summary else {},
            "by_payment": [dict(r) for r in by_payment]
        }
    finally:
        close_connection(conn)


def get_category_sales_report(start_date: str = None, end_date: str = None) -> list[dict]:
    """Category-wise sales using INNER JOIN and GROUP BY."""
    conn = get_connection()
    try:
        params = []
        where = "WHERE s.status='COMPLETED'"
        if start_date:
            where += " AND s.sale_date >= ?"
            params.append(start_date)
        if end_date:
            where += " AND s.sale_date <= ?"
            params.append(end_date)
        rows = conn.execute(f"""
            SELECT c.category_name,
                   COUNT(DISTINCT s.sale_id)  AS total_transactions,
                   SUM(si.quantity)           AS total_items_sold,
                   ROUND(SUM(si.line_total),2) AS total_revenue,
                   ROUND(AVG(s.total_amount),2) AS avg_order_value
            FROM   sale_items si
            INNER JOIN sales    s  ON si.sale_id    = s.sale_id
            INNER JOIN products p  ON si.product_id = p.product_id
            INNER JOIN categories c ON p.category_id = c.category_id
            {where}
            GROUP BY c.category_id, c.category_name
            ORDER BY total_revenue DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_best_selling_products(limit: int = 10,
                               start_date: str = None,
                               end_date: str = None) -> list[dict]:
    """Rank products by units sold."""
    conn = get_connection()
    try:
        params = []
        where = "WHERE s.status='COMPLETED'"
        if start_date:
            where += " AND s.sale_date >= ?"
            params.append(start_date)
        if end_date:
            where += " AND s.sale_date <= ?"
            params.append(end_date)
        params.append(limit)
        rows = conn.execute(f"""
            SELECT ROW_NUMBER() OVER (ORDER BY SUM(si.quantity) DESC) AS rank,
                   p.product_name, p.sku, c.category_name,
                   SUM(si.quantity)            AS units_sold,
                   SUM(si.line_total)          AS revenue,
                   COUNT(DISTINCT s.sale_id)   AS transactions
            FROM   sale_items si
            INNER JOIN sales      s  ON si.sale_id    = s.sale_id
            INNER JOIN products   p  ON si.product_id = p.product_id
            INNER JOIN categories c  ON p.category_id = c.category_id
            {where}
            GROUP BY si.product_id
            ORDER BY units_sold DESC
            LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_supplier_purchase_report(start_date: str = None,
                                  end_date: str = None) -> list[dict]:
    conn = get_connection()
    try:
        params = []
        where = "WHERE p.status='COMPLETED'"
        if start_date:
            where += " AND p.purchase_date >= ?"
            params.append(start_date)
        if end_date:
            where += " AND p.purchase_date <= ?"
            params.append(end_date)
        rows = conn.execute(f"""
            SELECT s.supplier_name,
                   COUNT(DISTINCT p.purchase_id) AS total_purchases,
                   SUM(pi.quantity)              AS total_items,
                   SUM(pi.quantity)              AS units_purchased,
                   ROUND(SUM(pi.line_total),2)   AS total_spent,
                   ROUND(SUM(pi.line_total),2)   AS total_cost,
                   MIN(p.purchase_date)          AS first_purchase,
                   MAX(p.purchase_date)          AS last_purchase
            FROM   purchase_items pi
            INNER JOIN purchases p  ON pi.purchase_id = p.purchase_id
            INNER JOIN suppliers s  ON p.supplier_id  = s.supplier_id
            {where}
            GROUP BY p.supplier_id, s.supplier_name
            ORDER BY total_spent DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_customer_sales_report(start_date: str = None,
                               end_date: str = None) -> list[dict]:
    conn = get_connection()
    try:
        params = []
        where = "WHERE s.status='COMPLETED'"
        if start_date:
            where += " AND s.sale_date >= ?"
            params.append(start_date)
        if end_date:
            where += " AND s.sale_date <= ?"
            params.append(end_date)
        rows = conn.execute(f"""
            SELECT COALESCE(c.customer_name, 'Walk-in Customer') AS customer_name,
                   COUNT(s.sale_id)      AS total_orders,
                   SUM(s.total_amount)   AS total_spent,
                   AVG(s.total_amount)   AS avg_order
            FROM   sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            {where}
            GROUP BY s.customer_id
            ORDER BY total_spent DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_inventory_valuation() -> list[dict]:
    """Inventory valuation at selling price (clearly labelled, not profit)."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.product_name, p.sku, c.category_name,
                   p.quantity_in_stock,
                   p.purchase_price,
                   p.selling_price,
                   p.quantity_in_stock * p.purchase_price AS cost_value,
                   p.quantity_in_stock * p.selling_price  AS retail_value
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            WHERE  p.quantity_in_stock > 0
            ORDER BY retail_value DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_monthly_revenue_trend(months: int = 6) -> list[dict]:
    """Return monthly revenue for the last N months for trend chart."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', sale_date) AS month,
                   COUNT(*)                    AS transactions,
                   SUM(total_amount)           AS revenue
            FROM   sales
            WHERE  status='COMPLETED'
            GROUP BY strftime('%Y-%m', sale_date)
            ORDER BY month DESC
            LIMIT ?
        """, (months,)).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        close_connection(conn)


def get_sales_trend_daily(days: int = 30) -> list[dict]:
    """Return daily sales revenue for the last N days."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT sale_date,
                   COUNT(*)          AS transactions,
                   SUM(total_amount) AS revenue
            FROM   sales
            WHERE  status='COMPLETED'
              AND  sale_date >= date('now','localtime',?)
            GROUP BY sale_date
            ORDER BY sale_date
        """, (f"-{days} days",)).fetchall()
        if not rows:
            # Fallback to the latest available sales if current window is empty
            rows = conn.execute("""
                SELECT sale_date,
                       COUNT(*)          AS transactions,
                       SUM(total_amount) AS revenue
                FROM   sales
                WHERE  status='COMPLETED'
                GROUP BY sale_date
                ORDER BY sale_date DESC
                LIMIT ?
            """, (days,)).fetchall()
            rows = list(reversed(rows))
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_audit_logs(limit: int = 100) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM audit_logs
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_sales_trend_monthly(months: int = 12) -> list[dict]:
    """Return monthly revenue trend for the last N months."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', sale_date)  AS period,
                   COUNT(*)                      AS transactions,
                   ROUND(SUM(total_amount), 2)   AS revenue
            FROM   sales
            WHERE  status = 'COMPLETED'
              AND  sale_date >= date('now','localtime', ?)
            GROUP  BY period
            ORDER  BY period
        """, (f"-{months} months",)).fetchall()
        if not rows:
            rows = conn.execute("""
                SELECT strftime('%Y-%m', sale_date)  AS period,
                       COUNT(*)                      AS transactions,
                       ROUND(SUM(total_amount), 2)   AS revenue
                FROM   sales
                WHERE  status = 'COMPLETED'
                GROUP  BY period
                ORDER  BY period DESC
                LIMIT ?
            """, (months,)).fetchall()
            rows = list(reversed(rows))
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_profit_by_category() -> list[dict]:
    """
    Gross profit per category:
      revenue  = SUM(sale_item.quantity * sale_item.unit_price)
      cost     = SUM(sale_item.quantity * product.purchase_price)
      margin % = (revenue - cost) / revenue * 100
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT c.category_name,
                   SUM(si.quantity)                              AS units_sold,
                   ROUND(SUM(si.quantity * si.unit_price), 2)   AS revenue,
                   ROUND(SUM(si.quantity * p.purchase_price), 2) AS cost,
                   ROUND(SUM(si.quantity * si.unit_price)
                         - SUM(si.quantity * p.purchase_price), 2) AS gross_profit,
                   ROUND(
                     (SUM(si.quantity * si.unit_price)
                      - SUM(si.quantity * p.purchase_price))
                     / NULLIF(SUM(si.quantity * si.unit_price), 0) * 100,
                   1) AS margin_pct
            FROM   sale_items si
            INNER JOIN sales      s  ON si.sale_id    = s.sale_id
            INNER JOIN products   p  ON si.product_id = p.product_id
            INNER JOIN categories c  ON p.category_id = c.category_id
            WHERE  s.status = 'COMPLETED'
            GROUP  BY c.category_id, c.category_name
            ORDER  BY gross_profit DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_stock_valuation_by_category() -> list[dict]:
    """Stock value grouped by category."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT c.category_name,
                   COUNT(p.product_id)                              AS total_products,
                   SUM(p.quantity_in_stock)                        AS total_units,
                   ROUND(SUM(p.quantity_in_stock * p.purchase_price),2) AS cost_value,
                   ROUND(SUM(p.quantity_in_stock * p.selling_price),2)  AS sell_value
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            GROUP  BY c.category_id, c.category_name
            ORDER  BY sell_value DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)
