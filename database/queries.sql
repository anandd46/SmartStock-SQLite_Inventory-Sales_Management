-- =============================================================================
-- database/queries.sql
-- SmartStock - Reference SQL Queries
-- Created by Anand D
--
-- This file is for REFERENCE and DOCUMENTATION purposes.
-- All queries are executed programmatically via Python using parameterized
-- placeholders (?). This file shows the SQL patterns used in the application.
-- =============================================================================


-- =============================================================================
-- PRODUCT QUERIES
-- =============================================================================

-- Get all products with category and supplier name
SELECT p.product_id, p.product_name, p.sku,
       c.category_name,
       COALESCE(s.supplier_name, '—') AS supplier_name,
       p.purchase_price, p.selling_price,
       p.quantity_in_stock, p.reorder_level,
       p.created_at
FROM   products p
INNER JOIN categories c ON p.category_id = c.category_id
LEFT  JOIN suppliers  s ON p.supplier_id  = s.supplier_id
ORDER  BY p.product_name;

-- Search products by name or SKU
SELECT * FROM products
WHERE  product_name LIKE '%search_term%' OR sku LIKE '%search_term%';

-- Get low stock products (at or below reorder level but not zero)
SELECT p.product_name, p.sku, c.category_name,
       p.quantity_in_stock, p.reorder_level,
       (p.reorder_level - p.quantity_in_stock) AS shortage
FROM   products p
INNER JOIN categories c ON p.category_id = c.category_id
WHERE  p.quantity_in_stock <= p.reorder_level
  AND  p.quantity_in_stock > 0
ORDER  BY shortage DESC;

-- Get out-of-stock products
SELECT product_name, sku, reorder_level
FROM   products
WHERE  quantity_in_stock = 0;

-- Manual stock adjustment (INSERT movement record, then UPDATE product)
INSERT INTO inventory_movements (product_id, movement_type, quantity_change,
                                  reference_type, notes, movement_date)
VALUES (?, 'ADJUSTMENT', ?, 'MANUAL', ?, datetime('now','localtime'));

UPDATE products
SET    quantity_in_stock = quantity_in_stock + ?
WHERE  product_id = ?;


-- =============================================================================
-- CATEGORY QUERIES
-- =============================================================================

-- Get categories with product count
SELECT c.category_id, c.category_name, c.description,
       COUNT(p.product_id) AS product_count,
       c.created_at
FROM   categories c
LEFT JOIN products p ON c.category_id = p.category_id
GROUP  BY c.category_id
ORDER  BY c.category_name;


-- =============================================================================
-- SUPPLIER QUERIES
-- =============================================================================

-- Supplier with total purchase amount and count
SELECT s.supplier_id, s.supplier_name, s.phone, s.email,
       COUNT(DISTINCT p.purchase_id) AS total_purchases,
       COALESCE(SUM(p.total_amount), 0)  AS total_spent
FROM   suppliers s
LEFT JOIN purchases p ON s.supplier_id = p.supplier_id
GROUP  BY s.supplier_id
ORDER  BY s.supplier_name;

-- Purchase history for one supplier
SELECT p.purchase_id, p.purchase_date, p.total_amount, p.status,
       COUNT(pi.purchase_item_id) AS item_count
FROM   purchases p
LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
WHERE  p.supplier_id = ?
GROUP  BY p.purchase_id
ORDER  BY p.purchase_date DESC;


-- =============================================================================
-- CUSTOMER QUERIES
-- =============================================================================

-- Customer with total purchase amount
SELECT c.customer_id, c.customer_name, c.phone, c.email,
       COUNT(DISTINCT s.sale_id)  AS total_orders,
       COALESCE(SUM(s.total_amount), 0) AS total_spent,
       COALESCE(AVG(s.total_amount), 0) AS avg_order_value
FROM   customers c
LEFT JOIN sales s ON c.customer_id = s.customer_id AND s.status='COMPLETED'
GROUP  BY c.customer_id
ORDER  BY c.customer_name;


-- =============================================================================
-- PURCHASE QUERIES
-- =============================================================================

-- All purchases with supplier name and item count
SELECT p.purchase_id, p.purchase_date, s.supplier_name,
       p.total_amount, p.status,
       COUNT(pi.purchase_item_id) AS item_count
FROM   purchases p
INNER JOIN suppliers     s  ON p.supplier_id  = s.supplier_id
LEFT  JOIN purchase_items pi ON p.purchase_id  = pi.purchase_id
GROUP  BY p.purchase_id
ORDER  BY p.purchase_date DESC;

-- Purchase detail (items)
SELECT pi.purchase_item_id, pi.quantity, pi.unit_cost, pi.line_total,
       p.product_name, p.sku
FROM   purchase_items pi
INNER JOIN products p ON pi.product_id = p.product_id
WHERE  pi.purchase_id = ?;


-- =============================================================================
-- SALE QUERIES
-- =============================================================================

-- All sales with customer name, item count
SELECT s.sale_id, s.sale_date,
       COALESCE(c.customer_name, 'Walk-in') AS customer_name,
       s.total_amount, s.payment_method, s.status,
       COUNT(si.sale_item_id) AS item_count
FROM   sales s
LEFT JOIN customers  c  ON s.customer_id = c.customer_id
LEFT JOIN sale_items si ON s.sale_id     = si.sale_id
GROUP  BY s.sale_id
ORDER  BY s.sale_date DESC, s.sale_id DESC;

-- Sale detail (items)
SELECT si.sale_item_id, si.quantity, si.unit_price, si.line_total,
       p.product_name, p.sku
FROM   sale_items si
INNER JOIN products p ON si.product_id = p.product_id
WHERE  si.sale_id = ?;


-- =============================================================================
-- REPORT QUERIES
-- =============================================================================

-- Daily sales summary between two dates
SELECT s.sale_date,
       COUNT(DISTINCT s.sale_id)              AS transactions,
       SUM(si.quantity)                       AS items_sold,
       ROUND(SUM(si.quantity * si.unit_price),2) AS revenue,
       ROUND(AVG(s.total_amount), 2)          AS avg_order_value
FROM   sales s
LEFT JOIN sale_items si ON s.sale_id = si.sale_id
WHERE  s.status='COMPLETED'
  AND  s.sale_date BETWEEN ? AND ?
GROUP  BY s.sale_date
ORDER  BY s.sale_date;

-- Monthly sales summary for a year
SELECT strftime('%Y-%m', s.sale_date)            AS month,
       COUNT(DISTINCT s.sale_id)                 AS transactions,
       SUM(si.quantity)                          AS items_sold,
       ROUND(SUM(si.quantity * si.unit_price),2) AS revenue,
       ROUND(AVG(s.total_amount),2)              AS avg_order_value
FROM   sales s
LEFT JOIN sale_items si ON s.sale_id = si.sale_id
WHERE  s.status='COMPLETED'
  AND  strftime('%Y', s.sale_date) = ?
GROUP  BY month
ORDER  BY month;

-- Category-wise sales report
SELECT c.category_name,
       COUNT(DISTINCT s.sale_id)              AS total_transactions,
       SUM(si.quantity)                       AS total_items_sold,
       ROUND(SUM(si.line_total),2)            AS total_revenue,
       ROUND(AVG(s.total_amount),2)           AS avg_order_value
FROM   sale_items si
INNER JOIN sales      s  ON si.sale_id    = s.sale_id
INNER JOIN products   p  ON si.product_id = p.product_id
INNER JOIN categories c  ON p.category_id = c.category_id
WHERE  s.status='COMPLETED'
GROUP  BY c.category_id, c.category_name
ORDER  BY total_revenue DESC;

-- Best-selling products (by units sold)
SELECT ROW_NUMBER() OVER (ORDER BY SUM(si.quantity) DESC) AS rank,
       p.product_name, p.sku, c.category_name,
       SUM(si.quantity)          AS units_sold,
       SUM(si.line_total)        AS revenue,
       COUNT(DISTINCT s.sale_id) AS transactions
FROM   sale_items si
INNER JOIN sales      s  ON si.sale_id    = s.sale_id
INNER JOIN products   p  ON si.product_id = p.product_id
INNER JOIN categories c  ON p.category_id = c.category_id
WHERE  s.status='COMPLETED'
GROUP  BY si.product_id
ORDER  BY units_sold DESC
LIMIT  10;

-- Profitability by category
SELECT c.category_name,
       SUM(si.quantity)                                    AS units_sold,
       ROUND(SUM(si.quantity * si.unit_price), 2)         AS revenue,
       ROUND(SUM(si.quantity * p.purchase_price), 2)      AS cost,
       ROUND(SUM(si.quantity * si.unit_price)
             - SUM(si.quantity * p.purchase_price), 2)    AS gross_profit,
       ROUND(
         (SUM(si.quantity * si.unit_price)
          - SUM(si.quantity * p.purchase_price))
         / NULLIF(SUM(si.quantity * si.unit_price),0) * 100,
       1)                                                  AS margin_pct
FROM   sale_items si
INNER JOIN sales      s  ON si.sale_id    = s.sale_id
INNER JOIN products   p  ON si.product_id = p.product_id
INNER JOIN categories c  ON p.category_id = c.category_id
WHERE  s.status='COMPLETED'
GROUP  BY c.category_id, c.category_name
ORDER  BY gross_profit DESC;

-- Stock valuation by category
SELECT c.category_name,
       COUNT(p.product_id)                                    AS total_products,
       SUM(p.quantity_in_stock)                              AS total_units,
       ROUND(SUM(p.quantity_in_stock * p.purchase_price),2)  AS cost_value,
       ROUND(SUM(p.quantity_in_stock * p.selling_price),2)   AS sell_value
FROM   products p
INNER JOIN categories c ON p.category_id = c.category_id
GROUP  BY c.category_id, c.category_name
ORDER  BY sell_value DESC;


-- =============================================================================
-- INVENTORY MOVEMENT LEDGER
-- =============================================================================

SELECT im.movement_id, im.movement_date,
       p.product_name, p.sku,
       im.movement_type, im.quantity_change,
       im.reference_type, im.reference_id, im.notes
FROM   inventory_movements im
INNER JOIN products p ON im.product_id = p.product_id
ORDER  BY im.movement_date DESC, im.movement_id DESC
LIMIT  200;


-- =============================================================================
-- SQLITE PRAGMA REFERENCE QUERIES
-- =============================================================================

-- Enable foreign key enforcement (must be run on every connection)
PRAGMA foreign_keys = ON;

-- Check foreign key status
PRAGMA foreign_keys;

-- Enable WAL mode for better concurrent reads
PRAGMA journal_mode = WAL;

-- Inspect a table's column definitions
PRAGMA table_info('products');

-- List all tables
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- List all triggers
SELECT name, tbl_name FROM sqlite_master WHERE type='trigger';

-- List all indexes
SELECT name, tbl_name FROM sqlite_master WHERE type='index';

