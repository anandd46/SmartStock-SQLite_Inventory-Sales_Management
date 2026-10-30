"""
tests/test_purchases.py
SmartStock - Purchase Service Tests
Created by Anand D

Tests that purchases correctly increase product stock via the database trigger.
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
    # Seed required data
    conn.execute("INSERT INTO categories(category_name) VALUES ('TestCat')")
    conn.execute("INSERT INTO suppliers(supplier_name) VALUES ('TestSupplier')")
    conn.execute("""
        INSERT INTO products(product_name, sku, category_id, supplier_id,
                             purchase_price, selling_price, reorder_level)
        VALUES ('Test Product', 'SKU-TEST-01', 1, 1, 100.0, 150.0, 5)
    """)
    conn.commit()
    return conn


def _create_purchase(conn, supplier_id, items: list[dict]) -> int:
    """Minimal purchase creation. Items: [{product_id, quantity, unit_cost}]"""
    total = sum(i["quantity"] * i["unit_cost"] for i in items)
    cur = conn.execute("""
        INSERT INTO purchases(supplier_id, purchase_date, total_amount, status)
        VALUES (?, date('now'), ?, 'COMPLETED')
    """, (supplier_id, total))
    purchase_id = cur.lastrowid
    for item in items:
        line_total = item["quantity"] * item["unit_cost"]
        conn.execute("""
            INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_cost, line_total)
            VALUES (?, ?, ?, ?, ?)
        """, (purchase_id, item["product_id"], item["quantity"],
              item["unit_cost"], line_total))
    conn.commit()
    return purchase_id


def _get_stock(conn, product_id: int) -> int:
    return conn.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id=?",
        (product_id,)
    ).fetchone()[0]


class TestPurchaseTrigger(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db()
        self.initial_stock = _get_stock(self.conn, 1)

    def tearDown(self):
        self.conn.close()

    def test_purchase_increases_stock(self):
        """Stock should increase by purchased quantity after trigger fires."""
        _create_purchase(self.conn, 1, [{"product_id": 1, "quantity": 20, "unit_cost": 100}])
        stock = _get_stock(self.conn, 1)
        self.assertEqual(stock, self.initial_stock + 20)

    def test_multiple_purchase_items_accumulate(self):
        """Three separate purchases should all be reflected in stock."""
        _create_purchase(self.conn, 1, [{"product_id": 1, "quantity": 10, "unit_cost": 100}])
        _create_purchase(self.conn, 1, [{"product_id": 1, "quantity": 15, "unit_cost": 100}])
        _create_purchase(self.conn, 1, [{"product_id": 1, "quantity": 5,  "unit_cost": 100}])
        stock = _get_stock(self.conn, 1)
        self.assertEqual(stock, self.initial_stock + 30)

    def test_purchase_creates_inventory_movement(self):
        """An inventory_movement record should be created with type 'PURCHASE'."""
        before = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='PURCHASE'"
        ).fetchone()[0]
        _create_purchase(self.conn, 1, [{"product_id": 1, "quantity": 5, "unit_cost": 100}])
        after = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='PURCHASE'"
        ).fetchone()[0]
        self.assertEqual(after, before + 1)

    def test_purchase_total_matches_sum_of_items(self):
        """Purchase total_amount should equal sum of line totals."""
        pid = _create_purchase(
            self.conn, 1,
            [{"product_id": 1, "quantity": 3, "unit_cost": 100}]
        )
        purchase = self.conn.execute(
            "SELECT total_amount FROM purchases WHERE purchase_id=?", (pid,)
        ).fetchone()
        self.assertAlmostEqual(float(purchase["total_amount"]), 300.0)

    def test_purchase_requires_valid_supplier(self):
        """FK constraint should reject invalid supplier_id."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO purchases(supplier_id, purchase_date, total_amount, status)
                VALUES (999, date('now'), 100, 'COMPLETED')
            """)
            self.conn.commit()

    def test_purchase_requires_valid_product(self):
        """FK constraint should reject invalid product_id in purchase_items."""
        self.conn.execute("""
            INSERT INTO purchases(supplier_id, purchase_date, total_amount, status)
            VALUES (1, date('now'), 100, 'COMPLETED')
        """)
        purchase_id = self.conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_cost, line_total)
                VALUES (?, 9999, 10, 100, 1000)
            """, (purchase_id,))
            self.conn.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)

