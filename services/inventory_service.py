"""
services/inventory_service.py
SmartStock - Inventory Management Service
Created by Anand D
"""

import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


def get_current_stock(search: str = "", category_id: int = None,
                      out_of_stock: bool = False,
                      low_stock: bool = False) -> list[dict]:
    """Return current stock levels with optional filtering."""
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT p.product_id, p.product_name, p.sku,
                   c.category_name, p.quantity_in_stock,
                   p.reorder_level,
                   CASE WHEN p.quantity_in_stock = 0           THEN 'Out of Stock'
                        WHEN p.quantity_in_stock <= p.reorder_level THEN 'Low Stock'
                        ELSE 'OK'
                   END AS stock_status,
                   p.selling_price,
                   p.quantity_in_stock * p.selling_price AS stock_value
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            WHERE  1=1
        """
        if search:
            query += " AND (p.product_name LIKE ? OR p.sku LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if category_id:
            query += " AND p.category_id=?"
            params.append(category_id)
        if out_of_stock:
            query += " AND p.quantity_in_stock = 0"
        elif low_stock:
            query += " AND p.quantity_in_stock <= p.reorder_level AND p.quantity_in_stock > 0"
        query += " ORDER BY p.quantity_in_stock ASC, p.product_name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_inventory_movements(product_id: int = None,
                             movement_type: str = None,
                             start_date: str = None,
                             end_date: str = None,
                             limit: int = 200) -> list[dict]:
    """Return inventory movement ledger with optional filters."""
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT im.movement_id, im.movement_type,
                   im.quantity_change, im.reference_type, im.reference_id,
                   im.movement_date, im.notes,
                   p.product_name, p.sku
            FROM   inventory_movements im
            INNER JOIN products p ON im.product_id = p.product_id
            WHERE  1=1
        """
        if product_id:
            query += " AND im.product_id=?"
            params.append(product_id)
        if movement_type:
            query += " AND im.movement_type=?"
            params.append(movement_type)
        if start_date:
            query += " AND im.movement_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND im.movement_date <= ?"
            params.append(end_date + " 23:59:59")
        query += " ORDER BY im.movement_date DESC, im.movement_id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_stock_summary() -> dict:
    """Return aggregate stock statistics."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*)                                      AS total_products,
                   SUM(quantity_in_stock)                       AS total_units,
                   SUM(quantity_in_stock * selling_price)       AS total_stock_value,
                   SUM(CASE WHEN quantity_in_stock = 0 THEN 1 ELSE 0 END) AS out_of_stock,
                   SUM(CASE WHEN quantity_in_stock > 0
                             AND quantity_in_stock <= reorder_level
                             THEN 1 ELSE 0 END)                 AS low_stock_count
            FROM   products
        """).fetchone()
        return dict(row) if row else {}
    finally:
        close_connection(conn)


def get_low_stock_products() -> list[dict]:
    """Return products at or below reorder level."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.product_id, p.product_name, p.sku,
                   c.category_name, s.supplier_name,
                   p.quantity_in_stock,
                   p.reorder_level,
                   (p.reorder_level - p.quantity_in_stock) AS shortage
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
            WHERE  p.quantity_in_stock <= p.reorder_level
              AND  p.quantity_in_stock > 0
            ORDER BY shortage DESC, p.product_name
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_out_of_stock_products() -> list[dict]:
    """Return products with zero stock."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.product_id, p.product_name, p.sku,
                   c.category_name, s.supplier_name,
                   p.reorder_level
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
            WHERE  p.quantity_in_stock = 0
            ORDER  BY p.product_name
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_current_stock_levels(search: str = "") -> list[dict]:
    """Alias for get_current_stock with supplier name included."""
    conn = get_connection()
    try:
        params = []
        query = """
            SELECT p.product_id, p.product_name, p.sku,
                   c.category_name,
                   COALESCE(s.supplier_name, '—') AS supplier_name,
                   p.quantity_in_stock, p.reorder_level,
                   p.purchase_price, p.selling_price,
                   p.quantity_in_stock * p.purchase_price AS cost_value,
                   p.quantity_in_stock * p.selling_price  AS retail_value
            FROM   products p
            INNER JOIN categories c ON p.category_id = c.category_id
            LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
            WHERE  1=1
        """
        if search:
            query += " AND (p.product_name LIKE ? OR p.sku LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        query += " ORDER BY p.product_name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)


def get_stock_valuation_summary() -> list[dict]:
    """Stock valuation grouped by category."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT c.category_name,
                   COUNT(p.product_id)                                   AS total_products,
                   COALESCE(SUM(p.quantity_in_stock), 0)                AS total_units,
                   ROUND(SUM(p.quantity_in_stock * p.purchase_price),2) AS cost_value,
                   ROUND(SUM(p.quantity_in_stock * p.selling_price),2)  AS sell_value
            FROM   categories c
            LEFT JOIN products p ON c.category_id = p.category_id
            GROUP  BY c.category_id, c.category_name
            ORDER  BY sell_value DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_connection(conn)
