"""
tests/test_reports.py
SmartStock - Report Service Tests
Created by Anand D

Tests that report queries return correct aggregated data from a controlled dataset.
"""

import unittest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import create_tables
from database.triggers_setup import create_triggers


def _build_db_with_data():
    """Build a test database with known sales/purchase data for deterministic assertions."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    create_tables(conn)
    create_triggers(conn)

    # Categories
    conn.execute("INSERT INTO categories(category_name) VALUES ('Electronics')")
    conn.execute("INSERT INTO categories(category_name) VALUES ('Stationery')")
    # Supplier
    conn.execute("INSERT INTO suppliers(supplier_name) VALUES ('Sup A')")
    # Customer
    conn.execute("INSERT INTO customers(customer_name) VALUES ('Cust X')")
    # Products with initial stock
    conn.execute("""
        INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price,
                             reorder_level, quantity_in_stock)
        VALUES ('Laptop', 'SKU-L', 1, 40000, 55000, 2, 50)
    """)
    conn.execute("""
        INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price,
                             reorder_level, quantity_in_stock)
        VALUES ('Pen', 'SKU-P', 2, 5, 15, 10, 200)
    """)
    conn.commit()

    # Create sales with known totals using direct INSERT (bypassing trigger check for simplicity)
    # Sale 1: 2026-01-15  — 2 Laptops  at 55000 each = 110000
    conn.execute("""
        INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
        VALUES (1, '2026-01-15', 110000, 'UPI', 'COMPLETED')
    """)
    sid1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""
        INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
        VALUES (?, 1, 2, 55000, 110000)
    """, (sid1,))

    # Sale 2: 2026-01-15  — 10 Pens at 15 each = 150
    conn.execute("""
        INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
        VALUES (1, '2026-01-15', 150, 'Cash', 'COMPLETED')
    """)
    sid2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""
        INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
        VALUES (?, 2, 10, 15, 150)
    """, (sid2,))

    # Sale 3: 2026-02-10  — 1 Laptop = 55000
    conn.execute("""
        INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
        VALUES (1, '2026-02-10', 55000, 'Card', 'COMPLETED')
    """)
    sid3 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""
        INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
        VALUES (?, 1, 1, 55000, 55000)
    """, (sid3,))

    # CANCELLED sale (should be excluded from reports)
    conn.execute("""
        INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
        VALUES (1, '2026-02-20', 55000, 'Cash', 'CANCELLED')
    """)
    conn.commit()

    return conn


class TestDailySalesReport(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db_with_data()

    def tearDown(self):
        self.conn.close()

    def test_daily_report_sums_correctly(self):
        rows = self.conn.execute("""
            SELECT sale_date,
                   COUNT(DISTINCT sale_id) AS transactions,
                   SUM(total_amount)       AS revenue
            FROM   sales
            WHERE  status='COMPLETED'
              AND  sale_date='2026-01-15'
            GROUP  BY sale_date
        """).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["transactions"], 2)
        self.assertAlmostEqual(float(rows[0]["revenue"]), 110150.0)

    def test_cancelled_sales_excluded_from_report(self):
        rows = self.conn.execute("""
            SELECT COUNT(*) AS c FROM sales WHERE status='COMPLETED'
        """).fetchone()
        total = self.conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
        self.assertEqual(rows["c"], total - 1)  # One cancelled sale


class TestMonthlySalesReport(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db_with_data()

    def tearDown(self):
        self.conn.close()

    def test_monthly_totals(self):
        rows = self.conn.execute("""
            SELECT strftime('%Y-%m', sale_date) AS month,
                   SUM(total_amount) AS revenue
            FROM   sales
            WHERE  status='COMPLETED'
            GROUP  BY month
            ORDER  BY month
        """).fetchall()
        months = {r["month"]: float(r["revenue"]) for r in rows}
        self.assertAlmostEqual(months.get("2026-01", 0), 110150.0)
        self.assertAlmostEqual(months.get("2026-02", 0), 55000.0)
        self.assertNotIn("2026-02-20", months)  # cancelled


class TestBestSellingProducts(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db_with_data()

    def tearDown(self):
        self.conn.close()

    def test_laptop_is_top_seller_by_revenue(self):
        rows = self.conn.execute("""
            SELECT p.product_name, SUM(si.line_total) AS revenue
            FROM   sale_items si
            JOIN   products p ON si.product_id = p.product_id
            JOIN   sales    s ON si.sale_id = s.sale_id
            WHERE  s.status = 'COMPLETED'
            GROUP  BY si.product_id
            ORDER  BY revenue DESC
        """).fetchall()
        self.assertEqual(rows[0]["product_name"], "Laptop")

    def test_pen_has_more_units_sold(self):
        rows = self.conn.execute("""
            SELECT p.product_name, SUM(si.quantity) AS units
            FROM   sale_items si
            JOIN   products p ON si.product_id = p.product_id
            JOIN   sales    s ON si.sale_id = s.sale_id
            WHERE  s.status = 'COMPLETED'
            GROUP  BY si.product_id
            ORDER  BY units DESC
        """).fetchall()
        # Laptop: 3 units, Pen: 10 units
        self.assertEqual(rows[0]["product_name"], "Pen")


class TestCategorySalesReport(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db_with_data()

    def tearDown(self):
        self.conn.close()

    def test_category_report_has_two_categories(self):
        rows = self.conn.execute("""
            SELECT c.category_name, SUM(si.line_total) AS revenue
            FROM   sale_items si
            JOIN   sales    s  ON si.sale_id    = s.sale_id
            JOIN   products p  ON si.product_id = p.product_id
            JOIN   categories c ON p.category_id = c.category_id
            WHERE  s.status = 'COMPLETED'
            GROUP  BY c.category_id
        """).fetchall()
        self.assertEqual(len(rows), 2)

    def test_electronics_revenue_is_correct(self):
        row = self.conn.execute("""
            SELECT SUM(si.line_total) AS revenue
            FROM   sale_items si
            JOIN   sales    s  ON si.sale_id    = s.sale_id
            JOIN   products p  ON si.product_id = p.product_id
            JOIN   categories c ON p.category_id = c.category_id
            WHERE  s.status = 'COMPLETED'
              AND  c.category_name = 'Electronics'
        """).fetchone()
        self.assertAlmostEqual(float(row["revenue"]), 165000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

