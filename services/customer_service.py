"""
services/customer_service.py
SmartStock - Customer CRUD Service
Created by Anand D
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_all_customers(search: str = "") -> list[dict]:
    conn = get_connection()
    try:
        if search:
            rows = conn.execute("""
                SELECT * FROM customers
                WHERE customer_name LIKE ? OR phone LIKE ? OR email LIKE ?
                ORDER BY customer_name
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM customers ORDER BY customer_name"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_customer_by_id(customer_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id=?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_connection(conn)


def create_customer(customer_name: str, phone: str = "", email: str = "") -> int:
    if not customer_name.strip():
        raise ValueError("Customer name cannot be blank.")
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO customers (customer_name, phone, email)
            VALUES (?, ?, ?)
        """, (customer_name.strip(), phone, email))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def update_customer(customer_id: int, customer_name: str,
                    phone: str, email: str) -> None:
    if not customer_name.strip():
        raise ValueError("Customer name cannot be blank.")
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE customers SET customer_name=?, phone=?, email=?
            WHERE customer_id=?
        """, (customer_name.strip(), phone, email, customer_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def delete_customer(customer_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM customers WHERE customer_id=?", (customer_id,)
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Cannot delete customer: {e}")
    finally:
        close_connection(conn)


def get_customer_sales_summary(customer_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT c.customer_name,
                   COUNT(s.sale_id)      AS total_orders,
                   SUM(s.total_amount)   AS total_spent,
                   AVG(s.total_amount)   AS avg_order_value,
                   MIN(s.sale_date)      AS first_purchase,
                   MAX(s.sale_date)      AS last_purchase
            FROM   sales s
            INNER JOIN customers c ON s.customer_id = c.customer_id
            WHERE  s.customer_id = ? AND s.status = 'COMPLETED'
            GROUP BY s.customer_id
        """, (customer_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_customer_sales(customer_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.sale_id, s.sale_date, s.total_amount,
                   s.payment_method, s.status,
                   COUNT(si.sale_item_id) AS item_count
            FROM   sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE  s.customer_id = ?
            GROUP BY s.sale_id
            ORDER BY s.sale_date DESC
        """, (customer_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)
