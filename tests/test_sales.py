"""
tests/test_sales.py
SmartStock - Sales Service Tests
Created by Anand D

Tests that sales correctly decrease stock, that insufficient-stock sales are
rejected, and that sale cancellation restores stock — all via DB triggers.
"""

import unittest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import create_tables
from database.triggers_setup import create_triggers


def _build_db(initial_stock: int = 50):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    create_tables(conn)
    create_triggers(conn)
    conn.execute("INSERT INTO categories(category_name) VALUES ('TestCat')")
    conn.execute("INSERT INTO suppliers(supplier_name)  VALUES ('TestSup')")
    conn.execute("INSERT INTO customers(customer_name)  VALUES ('TestCust')")
    conn.execute("""
        INSERT INTO products(product_name, sku, category_id, supplier_id,
                             purchase_price, selling_price, reorder_level,
                             quantity_in_stock)
        VALUES ('Test Product', 'SKU-T01', 1, 1, 100.0, 150.0, 5, ?)
    """, (initial_stock,))
    conn.commit()
    return conn


def _get_stock(conn, product_id=1):
    return conn.execute(
        "SELECT quantity_in_stock FROM products WHERE product_id=?",
        (product_id,)
    ).fetchone()[0]


def _create_sale(conn, customer_id, items: list[dict], status="COMPLETED") -> int:
    """Minimal sale creation. Items: [{product_id, quantity, unit_price}]"""
    total = sum(i["quantity"] * i["unit_price"] for i in items)
    cur = conn.execute("""
        INSERT INTO sales(customer_id, sale_date, total_amount, payment_method, status)
        VALUES (?, date('now'), ?, 'Cash', ?)
    """, (customer_id, total, status))
    sale_id = cur.lastrowid
    for item in items:
        conn.execute("""
            INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?)
        """, (sale_id, item["product_id"], item["quantity"],
              item["unit_price"], item["quantity"] * item["unit_price"]))
    conn.commit()
    return sale_id


class TestSaleTrigger(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db(initial_stock=50)

    def tearDown(self):
        self.conn.close()

    def test_sale_decreases_stock(self):
        """Stock should fall by sold quantity after trigger fires."""
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 10, "unit_price": 150}])
        self.assertEqual(_get_stock(self.conn), 40)

    def test_sale_exact_stock_succeeds(self):
        """A sale for exactly the available quantity should succeed."""
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 50, "unit_price": 150}])
        self.assertEqual(_get_stock(self.conn), 0)

    def test_sale_exceeds_stock_rejected(self):
        """A sale for more than available stock should raise an error (trigger)."""
        with self.assertRaises(Exception):
            _create_sale(
                self.conn, 1,
                [{"product_id": 1, "quantity": 51, "unit_price": 150}]
            )

    def test_sale_creates_inventory_movement(self):
        """An inventory_movement record with type 'SALE' should be created."""
        before = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='SALE'"
        ).fetchone()[0]
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 5, "unit_price": 150}])
        after = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='SALE'"
        ).fetchone()[0]
        self.assertEqual(after, before + 1)

    def test_multiple_sales_accumulate_deductions(self):
        """Stock should decrease cumulatively across multiple sales."""
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 10, "unit_price": 150}])
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 15, "unit_price": 150}])
        _create_sale(self.conn, 1, [{"product_id": 1, "quantity": 5,  "unit_price": 150}])
        self.assertEqual(_get_stock(self.conn), 20)

    def test_sale_total_matches_sum_of_items(self):
        sid = _create_sale(
            self.conn, 1,
            [{"product_id": 1, "quantity": 4, "unit_price": 150}]
        )
        sale = self.conn.execute(
            "SELECT total_amount FROM sales WHERE sale_id=?", (sid,)
        ).fetchone()
        self.assertAlmostEqual(float(sale["total_amount"]), 600.0)


class TestSaleCancellation(unittest.TestCase):

    def setUp(self):
        self.conn = _build_db(initial_stock=50)

    def tearDown(self):
        self.conn.close()

    def test_cancel_sale_restores_stock(self):
        """Cancelling a sale should restore the deducted stock via trigger."""
        sid = _create_sale(
            self.conn, 1,
            [{"product_id": 1, "quantity": 20, "unit_price": 150}]
        )
        stock_after_sale = _get_stock(self.conn)
        self.assertEqual(stock_after_sale, 30)

        # Cancel the sale
        self.conn.execute(
            "UPDATE sales SET status='CANCELLED' WHERE sale_id=?", (sid,))
        self.conn.commit()
        stock_after_cancel = _get_stock(self.conn)
        self.assertEqual(stock_after_cancel, 50)

    def test_cancel_creates_adjustment_movement(self):
        """A CANCELLATION inventory movement should be logged on cancellation."""
        sid = _create_sale(
            self.conn, 1,
            [{"product_id": 1, "quantity": 10, "unit_price": 150}]
        )
        before = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='CANCELLATION'"
        ).fetchone()[0]
        self.conn.execute(
            "UPDATE sales SET status='CANCELLED' WHERE sale_id=?", (sid,))
        self.conn.commit()
        after = self.conn.execute(
            "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='CANCELLATION'"
        ).fetchone()[0]
        self.assertEqual(after, before + 1)

    def test_stock_never_goes_negative(self):
        """After a successful sale, stock must be non-negative."""
        _create_sale(
            self.conn, 1,
            [{"product_id": 1, "quantity": 50, "unit_price": 150}]
        )
        self.assertGreaterEqual(_get_stock(self.conn), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
