"""
database/triggers_setup.py
SmartStock - SQLite Triggers
Created by Anand D

Implements four triggers:
  1. trg_purchase_item_stock_increase  - Increases stock on purchase_item INSERT
  2. trg_sale_item_stock_decrease      - Decreases stock on sale_item INSERT (with stock check)
  3. trg_sale_item_audit               - Audit log for sale completions
  4. trg_product_updated_at            - Updates products.updated_at automatically

NOTE: Stock changes happen ONLY via triggers to ensure a single source of truth.
Python services must NOT update quantity_in_stock directly.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

TRIGGERS_SQL = """
-- ============================================================
-- SmartStock Triggers
-- Created by Anand D
-- ============================================================

-- Trigger 1: Increase product stock when a purchase item is inserted.
-- Fires AFTER INSERT on purchase_items.
-- Also writes an inventory movement record.
DROP TRIGGER IF EXISTS trg_purchase_item_stock_increase;
CREATE TRIGGER trg_purchase_item_stock_increase
AFTER INSERT ON purchase_items
FOR EACH ROW
BEGIN
    -- Increase the product's stock quantity
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock + NEW.quantity,
           updated_at        = datetime('now','localtime')
    WHERE  product_id = NEW.product_id;

    -- Record the movement in the inventory ledger
    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    VALUES
        (NEW.product_id, 'PURCHASE', NEW.quantity,
         'purchase_items', NEW.purchase_item_id,
         datetime('now','localtime'),
         'Stock increased via purchase item #' || NEW.purchase_item_id);

    -- Write audit log entry
    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('products', NEW.product_id, 'STOCK_INCREASE',
            'Purchase item ' || NEW.purchase_item_id ||
            ' added qty ' || NEW.quantity);
END;

-- Trigger 2: Decrease product stock when a sale item is inserted.
-- Fires BEFORE INSERT on sale_items so we can ABORT the transaction
-- if stock is insufficient (SQLite RAISE(ABORT,...) rolls back the statement).
DROP TRIGGER IF EXISTS trg_sale_item_stock_decrease;
CREATE TRIGGER trg_sale_item_stock_decrease
BEFORE INSERT ON sale_items
FOR EACH ROW
BEGIN
    -- Abort if the product does not have enough stock
    SELECT RAISE(ABORT, 'Insufficient stock: not enough units available for this product.')
    WHERE (SELECT quantity_in_stock FROM products WHERE product_id = NEW.product_id) < NEW.quantity;
END;

-- Trigger 2b: After the stock check passes, actually decrease the stock.
DROP TRIGGER IF EXISTS trg_sale_item_stock_decrease_after;
CREATE TRIGGER trg_sale_item_stock_decrease_after
AFTER INSERT ON sale_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock - NEW.quantity,
           updated_at        = datetime('now','localtime')
    WHERE  product_id = NEW.product_id;

    -- Record in inventory ledger (negative quantity_change = stock out)
    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    VALUES
        (NEW.product_id, 'SALE', -NEW.quantity,
         'sale_items', NEW.sale_item_id,
         datetime('now','localtime'),
         'Stock decreased via sale item #' || NEW.sale_item_id);

    -- Write audit log
    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('products', NEW.product_id, 'STOCK_DECREASE',
            'Sale item ' || NEW.sale_item_id ||
            ' removed qty ' || NEW.quantity);
END;

-- Trigger 3: Automatically update products.updated_at on any UPDATE.
DROP TRIGGER IF EXISTS trg_product_updated_at;
CREATE TRIGGER trg_product_updated_at
AFTER UPDATE OF product_name, sku, category_id, supplier_id,
               purchase_price, selling_price, reorder_level
ON products
FOR EACH ROW
BEGIN
    UPDATE products
    SET updated_at = datetime('now','localtime')
    WHERE product_id = NEW.product_id;
END;

-- Trigger 4: When a sale is CANCELLED, restore stock for all its items.
-- Fires AFTER UPDATE when status changes from COMPLETED to CANCELLED.
DROP TRIGGER IF EXISTS trg_sale_cancellation_restore_stock;
CREATE TRIGGER trg_sale_cancellation_restore_stock
AFTER UPDATE OF status ON sales
FOR EACH ROW
WHEN OLD.status = 'COMPLETED' AND NEW.status = 'CANCELLED'
BEGIN
    -- Restore stock for each item in the cancelled sale
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock + si.quantity,
           updated_at        = datetime('now','localtime')
    FROM   (SELECT product_id, quantity FROM sale_items WHERE sale_id = NEW.sale_id) AS si
    WHERE  products.product_id = si.product_id;

    -- Record cancellation movements
    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    SELECT product_id, 'CANCELLATION', quantity,
           'sales', NEW.sale_id,
           datetime('now','localtime'),
           'Stock restored: sale #' || NEW.sale_id || ' cancelled'
    FROM   sale_items
    WHERE  sale_id = NEW.sale_id;

    -- Audit log
    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('sales', NEW.sale_id, 'SALE_CANCELLED',
            'Sale #' || NEW.sale_id || ' cancelled; stock restored.');
END;
"""


def create_triggers(conn: sqlite3.Connection) -> None:
    """Drop and recreate all triggers using an open connection."""
    try:
        conn.executescript(TRIGGERS_SQL)
        logger.info("Triggers created/refreshed successfully.")
    except sqlite3.Error as e:
        logger.error(f"Trigger creation error: {e}")
        raise
