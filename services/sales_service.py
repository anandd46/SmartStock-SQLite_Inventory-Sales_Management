"""
services/sales_service.py
SmartStock - Sales Transaction Service
Created by Anand D

Stock is decreased ONLY by the SQLite trigger trg_sale_item_stock_decrease_after.
The BEFORE trigger trg_sale_item_stock_decrease checks for sufficient stock
and raises ABORT if stock is insufficient.
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def create_sale(customer_id: int | None, sale_date: str,
                payment_method: str, items: list[dict],
                notes: str = "") -> int:
    """
    Create a complete sale transaction.
    items: list of {'product_id': int, 'quantity': int, 'unit_price': float}

    The BEFORE INSERT trigger checks stock availability and raises ABORT
    if insufficient. The AFTER INSERT trigger decreases stock.
    The entire operation is atomic.

    Returns the new sale_id.
    """
    if not items:
        raise ValueError("A sale must have at least one item.")

    valid_methods = ("Cash", "UPI", "Card", "Credit")
    if payment_method not in valid_methods:
        raise ValueError(f"Payment method must be one of {valid_methods}.")

    for item in items:
        if item["quantity"] <= 0:
            raise ValueError("All quantities must be positive.")
        if item["unit_price"] < 0:
            raise ValueError("Unit price cannot be negative.")

    conn = get_connection()
    try:
        conn.execute("BEGIN")

        # Validate customer exists (if provided)
        if customer_id is not None:
            cust = conn.execute(
                "SELECT customer_id FROM customers WHERE customer_id=?",
                (customer_id,)
            ).fetchone()
            if not cust:
                raise ValueError(f"Customer ID {customer_id} not found.")

        # Calculate total
        total_amount = sum(i["quantity"] * i["unit_price"] for i in items)

        # Insert sale header
        cursor = conn.execute("""
            INSERT INTO sales
                (customer_id, sale_date, total_amount, payment_method, status, notes)
            VALUES (?, ?, ?, ?, 'COMPLETED', ?)
        """, (customer_id, sale_date, total_amount, payment_method, notes))
        sale_id = cursor.lastrowid

        # Insert each sale item (triggers handle stock check and deduction)
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]
            price = item["unit_price"]
            line_total = qty * price

            # Validate product exists
            prod = conn.execute(
                "SELECT product_id, quantity_in_stock FROM products WHERE product_id=?",
                (pid,)
            ).fetchone()
            if not prod:
                raise ValueError(f"Product ID {pid} not found.")

            # Insert: the BEFORE trigger checks stock, AFTER trigger deducts it
            conn.execute("""
                INSERT INTO sale_items
                    (sale_id, product_id, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?)
            """, (sale_id, pid, qty, price, line_total))

        conn.execute("COMMIT")
        logger.info(f"Sale #{sale_id} created with {len(items)} items.")
        return sale_id

    except sqlite3.Error as e:
        conn.execute("ROLLBACK")
        logger.error(f"Sale creation failed: {e}")
        error_msg = str(e)
        if "Insufficient stock" in error_msg:
            raise ValueError(error_msg)
        raise ValueError(f"Sale failed: {error_msg}")
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Sale creation failed: {e}")
        raise
    finally:
        close_connection(conn)


def cancel_sale(sale_id: int) -> None:
    """
    Cancel a completed sale. The trigger trg_sale_cancellation_restore_stock
    automatically restores stock when status changes to CANCELLED.
    """
    conn = get_connection()
    try:
        sale = conn.execute(
            "SELECT status FROM sales WHERE sale_id=?", (sale_id,)
        ).fetchone()
        if not sale:
            raise ValueError(f"Sale #{sale_id} not found.")
        if sale["status"] == "CANCELLED":
            raise ValueError(f"Sale #{sale_id} is already cancelled.")

        # Update triggers trg_sale_cancellation_restore_stock
        conn.execute(
            "UPDATE sales SET status='CANCELLED' WHERE sale_id=?", (sale_id,)
        )
        conn.commit()
        logger.info(f"Sale #{sale_id} cancelled; stock restored by trigger.")
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def get_all_sales(customer_id: int = None, start_date: str = None,
                  end_date: str = None, payment_method: str = None,
                  status: str = None) -> list[dict]:
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT s.sale_id, s.sale_date, s.total_amount,
                   s.payment_method, s.status, s.notes, s.created_at,
                   COALESCE(c.customer_name, 'Walk-in Customer') AS customer_name,
                   COUNT(si.sale_item_id) AS item_count
            FROM   sales s
            LEFT  JOIN customers  c  ON s.customer_id = c.customer_id
            LEFT  JOIN sale_items si ON s.sale_id     = si.sale_id
            WHERE 1=1
        """
        if customer_id:
            query += " AND s.customer_id=?"
            params.append(customer_id)
        if start_date:
            query += " AND s.sale_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.sale_date <= ?"
            params.append(end_date)
        if payment_method:
            query += " AND s.payment_method=?"
            params.append(payment_method)
        if status:
            query += " AND s.status=?"
            params.append(status)
        query += " GROUP BY s.sale_id ORDER BY s.sale_date DESC, s.sale_id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_sale_details(sale_id: int) -> dict | None:
    conn = get_connection()
    try:
        header = conn.execute("""
            SELECT s.*,
                   COALESCE(c.customer_name, 'Walk-in Customer') AS customer_name
            FROM   sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            WHERE  s.sale_id = ?
        """, (sale_id,)).fetchone()
        if not header:
            return None
        items = conn.execute("""
            SELECT si.*, p.product_name, p.sku
            FROM   sale_items si
            INNER JOIN products p ON si.product_id = p.product_id
            WHERE  si.sale_id = ?
        """, (sale_id,)).fetchall()
        return {
            "header": dict(header),
            "items": [dict(i) for i in items]
        }
    finally:
        close_connection(conn)


def check_stock_availability(product_id: int, required_qty: int) -> tuple[bool, int]:
    """Returns (is_available: bool, current_stock: int)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT quantity_in_stock FROM products WHERE product_id=?",
            (product_id,)
        ).fetchone()
        if not row:
            return False, 0
        stock = row["quantity_in_stock"]
        return stock >= required_qty, stock
    finally:
        close_connection(conn)
