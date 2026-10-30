# SmartStock — Database Design

**Created by Anand D**

---

## Entity-Relationship Overview

SmartStock uses a normalized relational schema with 10 tables.
All relationships are enforced using SQLite FOREIGN KEY constraints with `PRAGMA foreign_keys = ON`.

```
categories ◄──── products ◄──── purchase_items ◄──── purchases ────► suppliers
                    │
                    └──── sale_items ◄──── sales ────► customers
                    │
                    └──── inventory_movements
```

---

## Table Descriptions

### 1. `categories`
Stores product categories (e.g., Electronics, Stationery).

| Column | Type | Constraints |
|---|---|---|
| category_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| category_name | TEXT | NOT NULL, UNIQUE |
| description | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

### 2. `suppliers`
Stores supplier (vendor) information.

| Column | Type | Constraints |
|---|---|---|
| supplier_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| supplier_name | TEXT | NOT NULL, UNIQUE |
| phone | TEXT | |
| email | TEXT | |
| address | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

### 3. `customers`
Stores customer information. Sales may also be recorded without a linked customer (walk-in).

| Column | Type | Constraints |
|---|---|---|
| customer_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| customer_name | TEXT | NOT NULL |
| phone | TEXT | |
| email | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

### 4. `products`
Central product table. Linked to categories and optionally to a preferred supplier.

| Column | Type | Constraints |
|---|---|---|
| product_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| product_name | TEXT | NOT NULL |
| sku | TEXT | NOT NULL, UNIQUE |
| category_id | INTEGER | NOT NULL, FK → categories(category_id) RESTRICT |
| supplier_id | INTEGER | FK → suppliers(supplier_id) SET NULL |
| purchase_price | REAL | NOT NULL, CHECK ≥ 0 |
| selling_price | REAL | NOT NULL, CHECK ≥ 0 |
| quantity_in_stock | INTEGER | NOT NULL, DEFAULT 0, CHECK ≥ 0 |
| reorder_level | INTEGER | NOT NULL, DEFAULT 5, CHECK ≥ 0 |
| created_at | TEXT | DEFAULT datetime('now','localtime') |
| updated_at | TEXT | DEFAULT datetime('now','localtime') |

> **Note:** `quantity_in_stock` is updated **exclusively by triggers**. Python services never write to this column directly (except for opening stock and manual adjustments).

---

### 5. `purchases`
Purchase order header. One purchase per supplier per transaction.

| Column | Type | Constraints |
|---|---|---|
| purchase_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| supplier_id | INTEGER | NOT NULL, FK → suppliers(supplier_id) RESTRICT |
| purchase_date | TEXT | NOT NULL |
| total_amount | REAL | NOT NULL, CHECK ≥ 0 |
| status | TEXT | DEFAULT 'COMPLETED', CHECK IN ('PENDING','COMPLETED','CANCELLED') |
| notes | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

### 6. `purchase_items`
Individual product lines within a purchase order.

| Column | Type | Constraints |
|---|---|---|
| purchase_item_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| purchase_id | INTEGER | NOT NULL, FK → purchases(purchase_id) CASCADE |
| product_id | INTEGER | NOT NULL, FK → products(product_id) RESTRICT |
| quantity | INTEGER | NOT NULL, CHECK > 0 |
| unit_cost | REAL | NOT NULL, CHECK ≥ 0 |
| line_total | REAL | GENERATED ALWAYS AS (quantity * unit_cost) — or computed at insert |

**Trigger:** `trg_purchase_item_stock_increase` fires AFTER INSERT and:
- Increases `products.quantity_in_stock` by `quantity`.
- Inserts a record into `inventory_movements` with `movement_type = 'PURCHASE'`.

---

### 7. `sales`
Sale transaction header. Customer is optional (walk-in).

| Column | Type | Constraints |
|---|---|---|
| sale_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| customer_id | INTEGER | FK → customers(customer_id) SET NULL |
| sale_date | TEXT | NOT NULL |
| total_amount | REAL | NOT NULL, CHECK ≥ 0 |
| payment_method | TEXT | DEFAULT 'Cash', CHECK IN ('Cash','UPI','Card','Credit') |
| status | TEXT | DEFAULT 'COMPLETED', CHECK IN ('COMPLETED','CANCELLED') |
| notes | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

### 8. `sale_items`
Individual product lines within a sale.

| Column | Type | Constraints |
|---|---|---|
| sale_item_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| sale_id | INTEGER | NOT NULL, FK → sales(sale_id) CASCADE |
| product_id | INTEGER | NOT NULL, FK → products(product_id) RESTRICT |
| quantity | INTEGER | NOT NULL, CHECK > 0 |
| unit_price | REAL | NOT NULL, CHECK ≥ 0 |
| line_total | REAL | NOT NULL |

**Triggers:**
- `trg_sale_item_stock_decrease` (BEFORE INSERT): checks if `quantity_in_stock >= quantity`. Aborts with error if insufficient.
- `trg_sale_item_stock_decrease_after` (AFTER INSERT): decreases `quantity_in_stock` and logs to `inventory_movements`.

---

### 9. `inventory_movements`
Audit ledger for all stock changes.

| Column | Type | Constraints |
|---|---|---|
| movement_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| product_id | INTEGER | NOT NULL, FK → products(product_id) RESTRICT |
| movement_type | TEXT | NOT NULL, CHECK IN ('PURCHASE','SALE','SALE_RETURN','ADJUSTMENT','OPENING_STOCK') |
| quantity_change | INTEGER | NOT NULL |
| reference_type | TEXT | |
| reference_id | INTEGER | |
| movement_date | TEXT | DEFAULT datetime('now','localtime') |
| notes | TEXT | |

---

### 10. `audit_logs`
General-purpose audit log for application-level events.

| Column | Type | Constraints |
|---|---|---|
| log_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| event_type | TEXT | NOT NULL |
| table_name | TEXT | |
| record_id | INTEGER | |
| description | TEXT | |
| created_at | TEXT | DEFAULT datetime('now','localtime') |

---

## Indexes

| Index Name | Table | Column(s) | Purpose |
|---|---|---|---|
| idx_products_sku | products | sku | Fast SKU lookups |
| idx_products_category | products | category_id | Category filter joins |
| idx_products_supplier | products | supplier_id | Supplier filter joins |
| idx_purchases_supplier | purchases | supplier_id | Supplier purchase history |
| idx_purchases_date | purchases | purchase_date | Date range queries |
| idx_sales_customer | sales | customer_id | Customer sales history |
| idx_sales_date | sales | sale_date | Date range queries |
| idx_sale_items_sale | sale_items | sale_id | Sale detail joins |
| idx_purchase_items_purchase | purchase_items | purchase_id | Purchase detail joins |
| idx_inventory_movements_product | inventory_movements | product_id | Movement ledger by product |

---

## Normalization

The schema follows **Third Normal Form (3NF)**:
- Every non-key attribute depends on the whole primary key (2NF satisfied).
- No non-key attribute depends on another non-key attribute (3NF satisfied).
- `categories` is separated from `products` to avoid repeating category descriptions.
- `suppliers` and `customers` are independent entities, not embedded in transactions.
- `inventory_movements` avoids recalculating stock by maintaining an audit trail.

---

## Data Integrity Strategy

| Mechanism | Purpose |
|---|---|
| PRIMARY KEY | Uniquely identifies each row |
| FOREIGN KEY | Enforces referential integrity across tables |
| UNIQUE | Prevents duplicate SKUs and category names |
| NOT NULL | Prevents missing required data |
| CHECK | Enforces business rules (e.g., non-negative prices, valid status) |
| TRIGGER (BEFORE) | Rejects business rule violations before data is written |
| TRIGGER (AFTER) | Automates cascading updates after valid inserts/updates |

---

## Created by Anand D · MCA Academic Mini-Project

