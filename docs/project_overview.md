# SmartStock — Project Overview

**Created by Anand D**
**MCA Academic Mini-Project — SQLite Database Management System**

---

## What is SmartStock?

SmartStock is a lightweight, relational database-driven inventory and sales management application built
for small shops, retail businesses, and educational demonstration purposes.

It stores product information, categories, supplier details, customer records, purchase orders,
sales transactions, and a full inventory movement ledger — all inside a single SQLite database file.

The application provides a clean web interface powered by Streamlit, and all business logic relies on
real SQL queries, database constraints, and triggers rather than Python calculations.

---

## Why Was SmartStock Built?

The project was built to:

1. Demonstrate practical SQLite knowledge in a realistic business context.
2. Implement CRUD operations against a normalized relational database.
3. Use SQL aggregate functions, joins, GROUP BY, and date functions for reporting.
4. Show how database triggers can automate business rules (stock management).
5. Enforce data integrity using PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, and NOT NULL constraints.
6. Provide a working, testable, and resume-worthy portfolio project.

---

## Target Audience

- MCA / BCA / BSc CS students learning SQLite and relational databases.
- Developers wanting a self-contained SQLite + Python + Streamlit reference project.
- Small business owners who want a simple stock tracking tool.

---

## What SmartStock Is Not

- It is **not** an accounting or tax management system.
- It is **not** a cloud-hosted or enterprise-grade application.
- It is **not** a fully compliant business software product.

It is an educational demonstration application suitable for academic submission and portfolio use.

---

## Key Capabilities

| Capability | Implementation |
|---|---|
| Product management | CRUD with SKU uniqueness and category/supplier FK |
| Category management | CRUD with delete protection |
| Supplier management | CRUD with purchase history view |
| Customer management | CRUD with sales history view |
| Purchase recording | Multi-item, trigger-driven stock increase |
| Sales recording | Multi-item, trigger-driven stock decrease with stock check |
| Sale cancellation | Trigger-driven stock restoration |
| Low stock alerts | SQL query with reorder level comparison |
| Inventory valuation | Category-wise cost and retail value |
| Movement ledger | Complete audit trail of all stock changes |
| Daily sales report | SQL GROUP BY date |
| Monthly sales report | SQL GROUP BY year/month |
| Category report | Multi-table JOIN with GROUP BY |
| Best sellers | Ranked by units sold and revenue |
| Profitability report | Revenue vs. cost per category |
| Sales trends | Time-series chart data from SQL |
| Database Explorer | Live schema inspector + SQL Lab |
| Automated tests | 30+ unit tests using isolated in-memory databases |

---

## Technology Choices

| Component | Technology | Reason |
|---|---|---|
| Database | SQLite | Serverless, zero-config, educational standard |
| DB Access | Python sqlite3 | Built-in, no ORM overhead, teaches raw SQL |
| UI | Streamlit | Simple, Python-native, no frontend coding |
| Charts | Plotly | Interactive charts with minimal setup |
| Data | Pandas | DataFrame display in Streamlit tables |
| Testing | unittest | Built-in Python, no extra dependencies |
| VCS | Git + GitHub | Standard professional version control |

---

## Created by Anand D · MCA Academic Mini-Project

