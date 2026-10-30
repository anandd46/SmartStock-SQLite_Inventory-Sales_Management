"""
services/purchase_service.py
SmartStock - Purchase Transaction Service
Created by Anand D

Stock is updated ONLY by the SQLite trigger trg_purchase_item_stock_increase.
This service does NOT update stock directly.
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def create_purchase(supplier_id: int, purchase_date: str,
                    items: list[dict], notes: str = "") -> int:
    """
    Create a complete purchase transaction.
    items: list of {'product_id': int, 'quantity': int, 'unit_cost': float}

    The purchase header is inserted first, then purchase_items.
    The trigger trg_purchase_item_stock_increase fires after each item insert
    and increases stock + records inventory movements automatically.

    Entire operation is wrapped in a transaction – all or nothing.
    Returns the new purchase_id.
    """
    if not items:
        raise ValueError("A purchase must have at least one item.")

    for item in items:
        if item["quantity"] <= 0:
            raise ValueError("All quantities must be positive.")
        if item["unit_cost"] < 0:
            raise ValueError("Unit cost cannot be negative.")

    conn = get_connection()
    try:
        conn.execute("BEGIN")

        # Validate supplier exists
        sup = conn.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id=?",
            (supplier_id,)
        ).fetchone()
        if not sup:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        # Calculate total amount
        total_amount = sum(i["quantity"] * i["unit_cost"] for i in items)

        # Insert purchase header
        cursor = conn.execute("""
            INSERT INTO purchases
                (supplier_id, purchase_date, total_amount, status, notes)
            VALUES (?, ?, ?, 'COMPLETED', ?)
        """, (supplier_id, purchase_date, total_amount, notes))
        purchase_id = cursor.lastrowid

        # Insert each purchase item (trigger fires and updates stock)
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            cost = item["unit_cost"]
            line_total = qty * cost

            # Validate product exists
            prod = conn.execute(
                "SELECT product_id FROM products WHERE product_id=?", (pid,)
            ).fetchone()
            if not prod:
                raise ValueError(f"Product ID {pid} not found.")

            conn.execute("""
                INSERT INTO purchase_items
                    (purchase_id, product_id, quantity, unit_cost, line_total)
                VALUES (?, ?, ?, ?, ?)
            """, (purchase_id, pid, qty, cost, line_total))

        conn.execute("COMMIT")
        logger.info(f"Purchase #{purchase_id} created with {len(items)} items.")
        return purchase_id

    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Purchase creation failed: {e}")
        raise
    finally:
        close_connection(conn)


def get_all_purchases(supplier_id: int = None,
                      start_date: str = None, end_date: str = None,
                      status: str = None) -> list[dict]:
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT p.purchase_id, p.purchase_date, p.total_amount,
                   p.status, p.notes, p.created_at,
                   s.supplier_name,
                   COUNT(pi.purchase_item_id) AS item_count
            FROM   purchases p
            INNER JOIN suppliers s     ON p.supplier_id = s.supplier_id
            LEFT  JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
            WHERE 1=1
        """
        if supplier_id:
            query += " AND p.supplier_id=?"
            params.append(supplier_id)
        if start_date:
            query += " AND p.purchase_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND p.purchase_date <= ?"
            params.append(end_date)
        if status:
            query += " AND p.status=?"
            params.append(status)
        query += " GROUP BY p.purchase_id ORDER BY p.purchase_date DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_purchase_details(purchase_id: int) -> dict | None:
    conn = get_connection()
    try:
        header = conn.execute("""
            SELECT p.*, s.supplier_name
            FROM   purchases p
            INNER JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE  p.purchase_id = ?
        """, (purchase_id,)).fetchone()
        if not header:
            return None
        items = conn.execute("""
            SELECT pi.*, pr.product_name, pr.sku
            FROM   purchase_items pi
            INNER JOIN products pr ON pi.product_id = pr.product_id
            WHERE  pi.purchase_id = ?
        """, (purchase_id,)).fetchall()
        return {
            "header": dict(header),
            "items": [dict(i) for i in items]
        }
    finally:
        close_connection(conn)
