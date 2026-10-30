"""
services/product_service.py
SmartStock - Product CRUD Service
Created by Anand D

All SQL uses parameterized queries. Never concatenates raw user input.
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_all_products(search: str = "", category_id: int = None,
                     supplier_id: int = None, low_stock_only: bool = False) -> list[dict]:
    """Return products with optional search/filter using INNER JOIN and LEFT JOIN."""
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT p.product_id, p.product_name, p.sku,
                   c.category_name, s.supplier_name,
                   p.purchase_price, p.selling_price,
                   p.quantity_in_stock, p.reorder_level,
                   p.category_id, p.supplier_id,
                   p.created_at, p.updated_at
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
            WHERE  1=1
        """
        if search:
            query += " AND (p.product_name LIKE ? OR p.sku LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if category_id:
            query += " AND p.category_id = ?"
            params.append(category_id)
        if supplier_id:
            query += " AND p.supplier_id = ?"
            params.append(supplier_id)
        if low_stock_only:
            query += " AND p.quantity_in_stock <= p.reorder_level"
        query += " ORDER BY p.product_name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_product_by_id(product_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT p.*, c.category_name, s.supplier_name
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
            WHERE  p.product_id = ?
        """, (product_id,)).fetchone()
        return dict(row) if row else None
    finally:
        close_connection(conn)


def get_product_by_sku(sku: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_connection(conn)


def create_product(product_name: str, sku: str, category_id: int,
                   supplier_id: int | None, purchase_price: float,
                   selling_price: float, reorder_level: int = 5) -> int:
    """Insert a new product. Returns the new product_id."""
    if not product_name.strip():
        raise ValueError("Product name cannot be blank.")
    if not sku.strip():
        raise ValueError("SKU cannot be blank.")
    if purchase_price < 0 or selling_price < 0:
        raise ValueError("Prices cannot be negative.")
    if reorder_level < 0:
        raise ValueError("Reorder level cannot be negative.")

    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO products
                (product_name, sku, category_id, supplier_id,
                 purchase_price, selling_price, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_name.strip(), sku.strip().upper(), category_id,
              supplier_id, purchase_price, selling_price, reorder_level))
        conn.commit()
        logger.info(f"Product created: {sku}")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE" in str(e):
            raise ValueError(f"SKU '{sku}' already exists.")
        raise ValueError(f"Database constraint error: {e}")
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)


def update_product(product_id: int, product_name: str, sku: str,
                   category_id: int, supplier_id: int | None,
                   purchase_price: float, selling_price: float,
                   reorder_level: int) -> None:
    """Update an existing product's details (not stock quantity)."""
    if not product_name.strip():
        raise ValueError("Product name cannot be blank.")
    if purchase_price < 0 or selling_price < 0:
        raise ValueError("Prices cannot be negative.")

    conn = get_connection()
    try:
        conn.execute("""
            UPDATE products
            SET product_name   = ?,
                sku            = ?,
                category_id    = ?,
                supplier_id    = ?,
                purchase_price = ?,
                selling_price  = ?,
                reorder_level  = ?
            WHERE product_id = ?
        """, (product_name.strip(), sku.strip().upper(), category_id,
              supplier_id, purchase_price, selling_price,
              reorder_level, product_id))
        conn.commit()
        logger.info(f"Product updated: id={product_id}")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Update error: {e}")
    finally:
        close_connection(conn)


def delete_product(product_id: int) -> None:
    """
    Delete a product only if it has no sale_items or purchase_items references.
    Raises ValueError if the product is referenced in historical transactions.
    """
    conn = get_connection()
    try:
        si_count = conn.execute(
            "SELECT COUNT(*) FROM sale_items WHERE product_id=?", (product_id,)
        ).fetchone()[0]
        pi_count = conn.execute(
            "SELECT COUNT(*) FROM purchase_items WHERE product_id=?", (product_id,)
        ).fetchone()[0]
        if si_count > 0 or pi_count > 0:
            raise ValueError(
                "Cannot delete: product is referenced in transaction history. "
                "Consider deactivating or renaming instead."
            )
        conn.execute("DELETE FROM products WHERE product_id=?", (product_id,))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Cannot delete product: {e}")
    finally:
        close_connection(conn)


def adjust_stock(product_id: int, quantity_change: int, notes: str = "") -> None:
    """
    Manually adjust stock (positive = add, negative = remove).
    Records an ADJUSTMENT movement. Does NOT go through purchase/sale triggers.
    """
    if quantity_change == 0:
        raise ValueError("Quantity change cannot be zero.")

    conn = get_connection()
    try:
        # Validate resulting stock won't be negative
        current = conn.execute(
            "SELECT quantity_in_stock FROM products WHERE product_id=?",
            (product_id,)
        ).fetchone()
        if not current:
            raise ValueError("Product not found.")
        new_qty = current[0] + quantity_change
        if new_qty < 0:
            raise ValueError(f"Adjustment would result in negative stock ({new_qty}).")

        conn.execute("""
            UPDATE products SET quantity_in_stock = quantity_in_stock + ?,
                                updated_at = datetime('now','localtime')
            WHERE product_id = ?
        """, (quantity_change, product_id))
        conn.execute("""
            INSERT INTO inventory_movements
                (product_id, movement_type, quantity_change,
                 reference_type, movement_date, notes)
            VALUES (?, 'ADJUSTMENT', ?, 'manual',
                    datetime('now','localtime'), ?)
        """, (product_id, quantity_change, notes or "Manual stock adjustment"))
        conn.commit()
        logger.info(f"Stock adjusted for product {product_id}: {quantity_change:+d}")
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection(conn)
