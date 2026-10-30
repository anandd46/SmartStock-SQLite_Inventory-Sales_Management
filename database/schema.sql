-- ============================================================
-- database/schema.sql
-- SmartStock - Complete Schema DDL Reference
-- Created by Anand D
-- This file is the SQL reference copy of schema.py
-- Run via: sqlite3 smartstock.db < database/schema.sql
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Table 1: categories
CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT    NOT NULL UNIQUE
                          CHECK(length(trim(category_name)) > 0),
    description   TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Table 2: suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT    NOT NULL CHECK(length(trim(supplier_name)) > 0),
    phone         TEXT,
    email         TEXT,
    address       TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Table 3: customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT    NOT NULL CHECK(length(trim(customer_name)) > 0),
    phone         TEXT,
    email         TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Table 4: products
CREATE TABLE IF NOT EXISTS products (
    product_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name      TEXT    NOT NULL CHECK(length(trim(product_name)) > 0),
    sku               TEXT    NOT NULL UNIQUE CHECK(length(trim(sku)) > 0),
    category_id       INTEGER NOT NULL,
    supplier_id       INTEGER,
    purchase_price    NUMERIC NOT NULL CHECK(purchase_price >= 0),
    selling_price     NUMERIC NOT NULL CHECK(selling_price >= 0),
    quantity_in_stock INTEGER NOT NULL DEFAULT 0 CHECK(quantity_in_stock >= 0),
    reorder_level     INTEGER NOT NULL DEFAULT 5 CHECK(reorder_level >= 0),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- Table 5: purchases
CREATE TABLE IF NOT EXISTS purchases (
    purchase_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id   INTEGER NOT NULL,
    purchase_date TEXT    NOT NULL DEFAULT (date('now','localtime')),
    total_amount  NUMERIC NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
    status        TEXT    NOT NULL DEFAULT 'COMPLETED'
                          CHECK(status IN ('PENDING','COMPLETED','CANCELLED')),
    notes         TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 6: purchase_items
CREATE TABLE IF NOT EXISTS purchase_items (
    purchase_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id      INTEGER NOT NULL,
    product_id       INTEGER NOT NULL,
    quantity         INTEGER NOT NULL CHECK(quantity > 0),
    unit_cost        NUMERIC NOT NULL CHECK(unit_cost >= 0),
    line_total       NUMERIC NOT NULL CHECK(line_total >= 0),
    FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    UNIQUE (purchase_id, product_id)
);

-- Table 7: sales
CREATE TABLE IF NOT EXISTS sales (
    sale_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    INTEGER,
    sale_date      TEXT    NOT NULL DEFAULT (date('now','localtime')),
    total_amount   NUMERIC NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
    payment_method TEXT    NOT NULL DEFAULT 'Cash'
                           CHECK(payment_method IN ('Cash','UPI','Card','Credit')),
    status         TEXT    NOT NULL DEFAULT 'COMPLETED'
                           CHECK(status IN ('COMPLETED','CANCELLED')),
    notes          TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- Table 8: sale_items
CREATE TABLE IF NOT EXISTS sale_items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id      INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL CHECK(quantity > 0),
    unit_price   NUMERIC NOT NULL CHECK(unit_price >= 0),
    line_total   NUMERIC NOT NULL CHECK(line_total >= 0),
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    UNIQUE (sale_id, product_id)
);

-- Table 9: inventory_movements
CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    movement_type   TEXT    NOT NULL
                            CHECK(movement_type IN
                                ('OPENING_STOCK','PURCHASE','SALE',
                                 'ADJUSTMENT','CANCELLATION')),
    quantity_change INTEGER NOT NULL,
    reference_type  TEXT,
    reference_id    INTEGER,
    movement_date   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    notes           TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 10: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id  INTEGER,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier  ON products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchases_supplier ON purchases(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchases_date     ON purchases(purchase_date);
CREATE INDEX IF NOT EXISTS idx_sales_customer     ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_date         ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);
CREATE INDEX IF NOT EXISTS idx_purchase_items_product ON purchase_items(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_product ON inventory_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_date    ON inventory_movements(movement_date);
