"""
services/category_service.py
SmartStock - Category CRUD Service
Created by Anand D
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_all_categories(search: str = "") -> list[dict]:
    conn = get_connection()
    try:
        if search:
            rows = conn.execute("""
                SELECT c.*,
                       COUNT(p.product_id) AS product_count
                FROM   categories c
                LEFT JOIN products p ON c.category_id = p.category_id
                WHERE  c.category_name LIKE ?
                GROUP BY c.category_id
                ORDER BY c.category_name
            """, (f"%{search}%",)).fetchall()
        else:
            rows = conn.execute("""
                SELECT c.*,
                       COUNT(p.product_id) AS product_count
                FROM   categories c
                LEFT JOIN products p ON c.category_id = p.category_id
                GROUP BY c.category_id
                ORDER BY c.category_name
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_category_by_id(category_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM categories WHERE category_id=?", (category_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_connection(conn)


def create_category(category_name: str, description: str = "") -> int:
    if not category_name.strip():
        raise ValueError("Category name cannot be blank.")
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO categories (category_name, description)
            VALUES (?, ?)
        """, (category_name.strip(), description))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE" in str(e):
            raise ValueError(f"Category '{category_name}' already exists.")
        raise ValueError(str(e))
    finally:
        close_connection(conn)


def update_category(category_id: int, category_name: str,
                    description: str) -> None:
    if not category_name.strip():
        raise ValueError("Category name cannot be blank.")
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE categories SET category_name=?, description=?
            WHERE category_id=?
        """, (category_name.strip(), description, category_id))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Update error: {e}")
    finally:
        close_connection(conn)


def delete_category(category_id: int) -> None:
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE category_id=?",
            (category_id,)
        ).fetchone()[0]
        if count > 0:
            raise ValueError(
                f"Cannot delete: {count} product(s) use this category."
            )
        conn.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Cannot delete category: {e}")
    finally:
        close_connection(conn)
