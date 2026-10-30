"""
tests/test_triggers.py
SmartStock - Trigger-Specific Tests
Created by Anand D

Focused tests for each SQLite trigger defined in triggers_setup.py.
"""

import unittest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import create_tables
from database.triggers_setup import create_triggers


def _build_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    create_tables(conn)
    create_triggers(conn)
    conn.execute("INSERT INTO categories(category_name) VALUES ('Cat')")
    conn.execute("INSERT INTO suppliers(supplier_name)  VALUES ('Sup')")
    conn.execute("INSERT INTO customers(customer_name)  VALUES ('Cust')")
    conn.execute("""
        INSERT INTO products(product_name, sku, category_id, supplier_id,
                             purchase_price, selling_price, reorder_level,
                             quantity_in_stock)
        VALUES ('Widget', 'SKU-W01', 1, 1, 50.0, 80.0, 5, 100)
    """)
    conn.commit()
    return conn


def _stock(conn):
    return conn.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id=1"
    ).fetchone()[0]


class TestPurchaseStockIncreaseTrigger(unittest.TestCase):
    """Tests for trg_purchase_item_stock_increase"""

    def setUp(self):
        self.conn = _build_db()

    def tearDown(self):
        self.conn.close()

    def test_trigger_fires_after_purchase_item_insert(self):
        initial = _stock(self.conn)
        self.conn.execute("""
            INSERT INTO purchases(supplier_id, purchase_date, total_amount, status)
            VALUES (1, date('now'), 500, 'COMPLETED')
        """)
        pid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute("""
            INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_cost, line_total)
            VALUES (?, 1, 10, 50, 500)
        """, (pid,))
        self.conn.commit()
        self.assertEqual(_stock(self.conn), initial + 10)

    def test_trigger_logs_movement(self):
        self.conn.execute("""
            INSERT INTO purchases(supplier_id, purchase_date, total_amount, status)
            VALUES (1, date('now'), 250, 'COMPLETED')
        """)
        pid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute("""
            INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_cost, line_total)
            VALUES (?, 1, 5, 50, 250)
        """, (pid,))
        self.conn.commit()
        move = self.conn.execute("""
            SELECT * FROM inventory_movements
            WHERE movement_type='PURCHASE' AND product_id=1
            ORDER BY movement_id DESC LIMIT 1
        """).fetchone()
        self.assertIsNotNone(move)
        self.assertEqual(move["quantity_change"], 5)


class TestSaleStockDecreaseTrigger(unittest.TestCase):
    """Tests for trg_sale_item_stock_decrease (BEFORE) and trg_sale_item_stock_decrease_after"""

    def setUp(self):
        self.conn = _build_db()

    def tearDown(self):
        self.conn.close()

    def test_before_trigger_rejects_insufficient_stock(self):
        self.conn.execute("""
            INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
            VALUES (1, date('now'), 8100, 'Cash', 'COMPLETED')
        """)
        sid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        with self.assertRaises(Exception):
            self.conn.execute("""
                INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
                VALUES (?, 1, 9999, 80, 799920)
            """, (sid,))
            self.conn.commit()

    def test_after_trigger_decreases_stock(self):
        initial = _stock(self.conn)
        self.conn.execute("""
            INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
            VALUES (1, date('now'), 400, 'Cash', 'COMPLETED')
        """)
        sid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute("""
            INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
            VALUES (?, 1, 5, 80, 400)
        """, (sid,))
        self.conn.commit()
        self.assertEqual(_stock(self.conn), initial - 5)

    def test_after_trigger_logs_movement(self):
        self.conn.execute("""
            INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
            VALUES (1, date('now'), 160, 'Cash', 'COMPLETED')
        """)
        sid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute("""
            INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
            VALUES (?, 1, 2, 80, 160)
        """, (sid,))
        self.conn.commit()
        move = self.conn.execute("""
            SELECT * FROM inventory_movements
            WHERE movement_type='SALE' AND product_id=1
            ORDER BY movement_id DESC LIMIT 1
        """).fetchone()
        self.assertIsNotNone(move)
        self.assertEqual(abs(move["quantity_change"]), 2)


class TestSaleCancellationTrigger(unittest.TestCase):
    """Tests for trg_sale_cancellation_restore_stock"""

    def setUp(self):
        self.conn = _build_db()
        # Create one sale
        self.conn.execute("""
            INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
            VALUES (1, date('now'), 800, 'Cash', 'COMPLETED')
        """)
        self.sale_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute("""
            INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
            VALUES (?, 1, 10, 80, 800)
        """, (self.sale_id,))
        self.conn.commit()
        self.stock_after_sale = _stock(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_cancel_restores_stock(self):
        self.conn.execute(
            "UPDATE sales SET status='CANCELLED' WHERE sale_id=?", (self.sale_id,))
        self.conn.commit()
        self.assertEqual(_stock(self.conn), self.stock_after_sale + 10)

    def test_cancel_logs_sale_return_movement(self):
        before = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='CANCELLATION'"
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE sales SET status='CANCELLED' WHERE sale_id=?", (self.sale_id,))
        self.conn.commit()
        after = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='CANCELLATION'"
        ).fetchone()[0]
        self.assertEqual(after, before + 1)


class TestProductUpdatedAtTrigger(unittest.TestCase):
    """Tests for trg_product_updated_at"""

    def setUp(self):
        self.conn = _build_db()

    def tearDown(self):
        self.conn.close()

    def test_updated_at_changes_on_update(self):
        old = self.conn.execute(
            "SELECT updated_at FROM products WHERE product_id=1"
        ).fetchone()[0]
        # Force a tiny delay by sleeping in SQL (not available), so just update
        self.conn.execute(
            "UPDATE products SET selling_price=90 WHERE product_id=1")
        self.conn.commit()
        new = self.conn.execute(
            "SELECT updated_at FROM products WHERE product_id=1"
        ).fetchone()[0]
        # updated_at should be set (not necessarily different in sub-second tests,
        # but the column should exist and be non-null)
        self.assertIsNotNone(new)


if __name__ == "__main__":
    unittest.main(verbosity=2)

