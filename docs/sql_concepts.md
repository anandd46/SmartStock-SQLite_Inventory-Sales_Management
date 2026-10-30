# SmartStock — SQL Concepts Demonstrated

**Created by Anand D**  
**MCA Academic Mini-Project — SQLite Database Management System**

---

This document maps every major SQLite/SQL concept used in SmartStock to the specific file
and query where it appears. Use this during your viva to explain each concept confidently.

---

## 1. DDL — Data Definition Language

### CREATE TABLE
File: `database/schema.py` and `database/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS products (
    product_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name      TEXT    NOT NULL,
    sku               TEXT    NOT NULL UNIQUE,
    category_id       INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    purchase_price    REAL    NOT NULL CHECK (purchase_price >= 0),
    selling_price     REAL    NOT NULL CHECK (selling_price >= 0),
    quantity_in_stock INTEGER NOT NULL DEFAULT 0 CHECK (quantity_in_stock >= 0)
);
```

### CREATE INDEX
```sql
CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku);
CREATE INDEX IF NOT EXISTS idx_sales_date   ON sales (sale_date);
```

### CREATE TRIGGER
File: `database/triggers_setup.py` and `database/triggers.sql`

```sql
CREATE TRIGGER IF NOT EXISTS trg_purchase_item_stock_increase
AFTER INSERT ON purchase_items
BEGIN
    UPDATE products
    SET    quantity_in_stock = quantity_in_stock + NEW.quantity
    WHERE  product_id = NEW.product_id;
END;
```

---

## 2. DML — Data Manipulation Language

### INSERT with Parameterized Queries
File: `services/product_service.py`

```sql
INSERT INTO products (product_name, sku, category_id, purchase_price, selling_price, reorder_level)
VALUES (?, ?, ?, ?, ?, ?)
```
All queries use `?` placeholders — **never** string concatenation — to prevent SQL injection.

### UPDATE
File: `services/product_service.py`

```sql
UPDATE products
SET    product_name=?, sku=?, category_id=?, purchase_price=?, selling_price=?, reorder_level=?,
       updated_at=datetime('now','localtime')
WHERE  product_id=?
```

### DELETE with FK Check
File: `services/product_service.py`

```sql
DELETE FROM products WHERE product_id=?
```
(Guarded by a pre-check for referenced sale_items / purchase_items before executing.)

---

## 3. DQL — Data Query Language

### Simple SELECT with WHERE
```sql
SELECT * FROM products WHERE product_name LIKE ?
```

### JOIN — INNER JOIN
File: `services/report_service.py`

```sql
SELECT c.category_name, SUM(si.line_total) AS revenue
FROM   sale_items si
INNER JOIN sales      s  ON si.sale_id    = s.sale_id
INNER JOIN products   p  ON si.product_id = p.product_id
INNER JOIN categories c  ON p.category_id = c.category_id
WHERE  s.status = 'COMPLETED'
GROUP  BY c.category_id
ORDER  BY revenue DESC
```

### JOIN — LEFT JOIN
```sql
SELECT s.sale_id, COALESCE(c.customer_name, 'Walk-in') AS customer_name
FROM   sales s
LEFT JOIN customers c ON s.customer_id = c.customer_id
```

### Aggregate Functions
```sql
SELECT COUNT(*), SUM(total_amount), AVG(total_amount), MAX(sale_date), MIN(sale_date)
FROM   sales
WHERE  status = 'COMPLETED'
```

### GROUP BY with HAVING
```sql
SELECT category_id, COUNT(*) AS product_count
FROM   products
GROUP  BY category_id
HAVING COUNT(*) > 0
```

### ORDER BY
```sql
SELECT * FROM products ORDER BY quantity_in_stock ASC, product_name ASC
```

### LIMIT and OFFSET
```sql
SELECT * FROM products LIMIT 20 OFFSET 0
```

---

## 4. SQLite Date & Time Functions

```sql
-- Current date
SELECT date('now', 'localtime')

-- Current datetime
SELECT datetime('now', 'localtime')

-- Group by year-month
SELECT strftime('%Y-%m', sale_date) AS month ...

-- Date arithmetic (last 30 days)
WHERE sale_date >= date('now', 'localtime', '-30 days')
```

---

## 5. Constraints

| Constraint | Example |
|---|---|
| PRIMARY KEY | `product_id INTEGER PRIMARY KEY AUTOINCREMENT` |
| FOREIGN KEY | `REFERENCES categories(category_id) ON DELETE RESTRICT` |
| UNIQUE | `sku TEXT NOT NULL UNIQUE` |
| NOT NULL | `product_name TEXT NOT NULL` |
| CHECK | `CHECK (selling_price >= 0)` |
| DEFAULT | `quantity_in_stock INTEGER NOT NULL DEFAULT 0` |

---

## 6. Triggers

| Trigger | Event | Effect |
|---|---|---|
| `trg_purchase_item_stock_increase` | AFTER INSERT on purchase_items | Increases `quantity_in_stock` |
| `trg_sale_item_stock_decrease` | BEFORE INSERT on sale_items | Aborts if stock insufficient |
| `trg_sale_item_stock_decrease_after` | AFTER INSERT on sale_items | Decreases `quantity_in_stock` |
| `trg_sale_cancellation_restore_stock` | AFTER UPDATE on sales | Restores stock if status → CANCELLED |
| `trg_product_updated_at` | AFTER UPDATE on products | Updates `updated_at` timestamp |

---

## 7. Subqueries and CTEs

Used in monthly sales report:
```sql
SELECT sale_date, COUNT(*), SUM(total_amount)
FROM (
    SELECT s.sale_date, s.sale_id, s.total_amount
    FROM   sales s
    WHERE  s.sale_date LIKE '2026-01%' AND s.status='COMPLETED'
)
GROUP BY sale_date
```

---

## 8. COALESCE for NULL Handling

```sql
SELECT COALESCE(c.customer_name, 'Walk-in Customer') AS customer_name
FROM   sales s
LEFT JOIN customers c ON s.customer_id = c.customer_id
```

---

## 9. PRAGMA Statements

```sql
PRAGMA foreign_keys = ON;   -- Enable FK enforcement (per connection)
PRAGMA journal_mode = WAL;  -- Enable Write-Ahead Logging for concurrency
PRAGMA table_info('products');  -- Inspect column definitions
```

---

## 10. Parameterized Queries (Security)

SmartStock uses **only parameterized queries** with `?` placeholders.
String interpolation into SQL is **never** used.

```python
# CORRECT — parameterized
conn.execute("SELECT * FROM products WHERE sku = ?", (sku,))

# WRONG — never done in SmartStock (SQL injection risk)
conn.execute(f"SELECT * FROM products WHERE sku = '{sku}'")
```

---

## Created by Anand D · MCA Academic Mini-Project

