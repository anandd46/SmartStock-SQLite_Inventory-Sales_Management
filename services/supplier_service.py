"""
services/supplier_service.py
SmartStock - Supplier CRUD Service
Created by Anand D
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_all_suppliers(search: str = "") -> list[dict]:
    conn = get_connection()
    try:
        if search:
            rows = conn.execute("""
                SELECT * FROM suppliers
                WHERE supplier_name LIKE ? OR phone LIKE ? OR email LIKE ?
                ORDER BY supplier_name
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM suppliers ORDER BY supplier_name"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_supplier_by_id(supplier_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM suppliers WHERE supplier_id=?", (supplier_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_connection(conn)


def create_supplier(supplier_name: str, phone: str = "",
                    email: str = "", address: str = "") -> int:
    if not supplier_name.strip():
        raise ValueError("Supplier name cannot be blank.")
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO suppliers (supplier_name, phone, email, address)
            VALUES (?, ?, ?, ?)
        """, (supplier_name.strip(), phone, email, address))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def update_supplier(supplier_id: int, supplier_name: str,
                    phone: str, email: str, address: str) -> None:
    if not supplier_name.strip():
        raise ValueError("Supplier name cannot be blank.")
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE suppliers
            SET supplier_name=?, phone=?, email=?, address=?
            WHERE supplier_id=?
        """, (supplier_name.strip(), phone, email, address, supplier_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def delete_supplier(supplier_id: int) -> None:
    conn = get_connection()
    try:
        ref = conn.execute(
            "SELECT COUNT(*) FROM purchases WHERE supplier_id=?", (supplier_id,)
        ).fetchone()[0]
        if ref > 0:
            raise ValueError("Cannot delete: supplier has purchase history.")
        conn.execute("DELETE FROM suppliers WHERE supplier_id=?", (supplier_id,))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Cannot delete supplier: {e}")
    finally:
        close_connection(conn)


def get_supplier_purchase_summary(supplier_id: int) -> list[dict]:
    """Return purchase summary for a specific supplier using GROUP BY."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.supplier_name,
                   COUNT(p.purchase_id)        AS total_purchases,
                   SUM(p.total_amount)         AS total_spent,
                   MIN(p.purchase_date)        AS first_purchase,
                   MAX(p.purchase_date)        AS last_purchase
            FROM   purchases p
            INNER JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE  p.supplier_id = ?
              AND  p.status = 'COMPLETED'
            GROUP BY p.supplier_id
        """, (supplier_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_supplier_purchases(supplier_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.purchase_id, p.purchase_date, p.total_amount,
                   p.status, p.notes,
                   COUNT(pi.purchase_item_id) AS item_count
            FROM   purchases p
            LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
            WHERE  p.supplier_id = ?
            GROUP BY p.purchase_id
            ORDER BY p.purchase_date DESC
        """, (supplier_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)
