-- ============================================================
-- database/triggers.sql
-- SmartStock - Triggers SQL Reference File
-- Created by Anand D
-- Reference copy of triggers_setup.py for documentation / CLI use
-- ============================================================

PRAGMA foreign_keys = ON;

DROP TRIGGER IF EXISTS trg_purchase_item_stock_increase;
CREATE TRIGGER trg_purchase_item_stock_increase
AFTER INSERT ON purchase_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock + NEW.quantity,
           updated_at        = datetime('now','localtime')
    WHERE  product_id = NEW.product_id;

    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    VALUES
        (NEW.product_id, 'PURCHASE', NEW.quantity,
         'purchase_items', NEW.purchase_item_id,
         datetime('now','localtime'),
         'Stock increased via purchase item #' || NEW.purchase_item_id);

    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('products', NEW.product_id, 'STOCK_INCREASE',
            'Purchase item ' || NEW.purchase_item_id ||
            ' added qty ' || NEW.quantity);
END;

DROP TRIGGER IF EXISTS trg_sale_item_stock_decrease;
CREATE TRIGGER trg_sale_item_stock_decrease
BEFORE INSERT ON sale_items
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Insufficient stock: not enough units available for this product.')
    WHERE (SELECT quantity_in_stock FROM products WHERE product_id = NEW.product_id) < NEW.quantity;
END;

DROP TRIGGER IF EXISTS trg_sale_item_stock_decrease_after;
CREATE TRIGGER trg_sale_item_stock_decrease_after
AFTER INSERT ON sale_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock - NEW.quantity,
           updated_at        = datetime('now','localtime')
    WHERE  product_id = NEW.product_id;

    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    VALUES
        (NEW.product_id, 'SALE', -NEW.quantity,
         'sale_items', NEW.sale_item_id,
         datetime('now','localtime'),
         'Stock decreased via sale item #' || NEW.sale_item_id);

    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('products', NEW.product_id, 'STOCK_DECREASE',
            'Sale item ' || NEW.sale_item_id ||
            ' removed qty ' || NEW.quantity);
END;

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

DROP TRIGGER IF EXISTS trg_sale_cancellation_restore_stock;
CREATE TRIGGER trg_sale_cancellation_restore_stock
AFTER UPDATE OF status ON sales
FOR EACH ROW
WHEN OLD.status = 'COMPLETED' AND NEW.status = 'CANCELLED'
BEGIN
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock + si.quantity,
           updated_at        = datetime('now','localtime')
    FROM   (SELECT product_id, quantity FROM sale_items WHERE sale_id = NEW.sale_id) AS si
    WHERE  products.product_id = si.product_id;

    INSERT INTO inventory_movements
        (product_id, movement_type, quantity_change,
         reference_type, reference_id, movement_date, notes)
    SELECT product_id, 'CANCELLATION', quantity,
           'sales', NEW.sale_id,
           datetime('now','localtime'),
           'Stock restored: sale #' || NEW.sale_id || ' cancelled'
    FROM   sale_items
    WHERE  sale_id = NEW.sale_id;

    INSERT INTO audit_logs (table_name, record_id, action, details)
    VALUES ('sales', NEW.sale_id, 'SALE_CANCELLED',
            'Sale #' || NEW.sale_id || ' cancelled; stock restored.');
END;
