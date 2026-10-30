"""
tests/test_products.py
SmartStock - Product Service Tests
Created by Anand D

Tests CRUD operations for the product service using a temporary database.
"""

import unittest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import create_tables
from database.triggers_setup import create_triggers


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    create_tables(conn)
    create_triggers(conn)
    # Seed a category and supplier
    conn.execute("INSERT INTO categories(category_name) VALUES ('Electronics')")
    conn.execute(
        "INSERT INTO suppliers(supplier_name) VALUES ('TechSupplier')")
    conn.commit()
    return conn


# Lightweight inline service functions that use a provided connection
def _create_product(conn, name, sku, cat_id, pp, sp, rl=5):
    cur = conn.execute("""
        INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price, reorder_level)
        VALUES (?,?,?,?,?,?)
    """, (name, sku, cat_id, pp, sp, rl))
    conn.commit()
    return cur.lastrowid


def _get_product(conn, pid):
    return conn.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone()


class TestProductCRUD(unittest.TestCase):

    def setUp(self):
        self.conn = _conn()

    def tearDown(self):
        self.conn.close()

    def test_create_product(self):
        pid = _create_product(self.conn, "Laptop", "SKU-LAP-001", 1, 45000, 55000)
        self.assertIsNotNone(pid)
        self.assertGreater(pid, 0)

    def test_read_product(self):
        pid = _create_product(self.conn, "Mouse", "SKU-MOU-001", 1, 250, 399)
        prod = _get_product(self.conn, pid)
        self.assertIsNotNone(prod)
        self.assertEqual(prod["product_name"], "Mouse")
        self.assertEqual(prod["sku"], "SKU-MOU-001")

    def test_update_product(self):
        pid = _create_product(self.conn, "Keyboard", "SKU-KEY-001", 1, 500, 799)
        self.conn.execute(
            "UPDATE products SET selling_price=? WHERE product_id=?", (899, pid))
        self.conn.commit()
        prod = _get_product(self.conn, pid)
        self.assertEqual(float(prod["selling_price"]), 899.0)

    def test_delete_product_no_transactions(self):
        pid = _create_product(self.conn, "Temp Product", "SKU-TEMP-001", 1, 100, 150)
        self.conn.execute("DELETE FROM products WHERE product_id=?", (pid,))
        self.conn.commit()
        self.assertIsNone(_get_product(self.conn, pid))

    def test_sku_unique_constraint(self):
        _create_product(self.conn, "Prod A", "SKU-DUPE-001", 1, 100, 150)
        with self.assertRaises(sqlite3.IntegrityError):
            _create_product(self.conn, "Prod B", "SKU-DUPE-001", 1, 200, 300)

    def test_initial_stock_is_zero(self):
        pid = _create_product(self.conn, "USB Hub", "SKU-USB-001", 1, 300, 499)
        prod = _get_product(self.conn, pid)
        self.assertEqual(prod["quantity_in_stock"], 0)

    def test_reorder_level_default(self):
        pid = _create_product(self.conn, "HDMI Cable", "SKU-HDMI-001", 1, 150, 249)
        prod = _get_product(self.conn, pid)
        self.assertEqual(prod["reorder_level"], 5)

    def test_negative_selling_price_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            _create_product(self.conn, "Bad Item", "SKU-BAD-001", 1, 100, -1)

    def test_search_by_name(self):
        _create_product(self.conn, "Wireless Mouse", "SKU-WM-001", 1, 500, 799)
        _create_product(self.conn, "Wired Keyboard", "SKU-WK-001", 1, 400, 649)
        rows = self.conn.execute(
            "SELECT * FROM products WHERE product_name LIKE ?",
            ("%Wireless%",)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_name"], "Wireless Mouse")

    def test_product_count_by_category(self):
        _create_product(self.conn, "Product1", "SKU-P1", 1, 100, 150)
        _create_product(self.conn, "Product2", "SKU-P2", 1, 200, 300)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM products WHERE category_id=1"
        ).fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

