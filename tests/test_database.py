"""
tests/test_database.py
SmartStock - Database Initialization & Schema Tests
Created by Anand D

Tests that the schema creates all expected tables, indexes, and triggers.
Uses a temporary in-memory / temp-file database so the real smartstock.db is never touched.
"""

import unittest
import sqlite3
import tempfile
import os
import sys

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import create_tables
from database.triggers_setup import create_triggers


def build_test_db() -> sqlite3.Connection:
    """Build a fresh, fully initialized in-memory test database."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    create_tables(conn)
    create_triggers(conn)
    return conn


EXPECTED_TABLES = [
    "categories", "suppliers", "customers", "products",
    "purchases", "purchase_items",
    "sales", "sale_items",
    "inventory_movements", "audit_logs"
]

EXPECTED_TRIGGERS = [
    "trg_purchase_item_stock_increase",
    "trg_sale_item_stock_decrease",
    "trg_sale_item_stock_decrease_after",
    "trg_sale_cancellation_restore_stock",
    "trg_product_updated_at",
]


class TestDatabaseSchema(unittest.TestCase):

    def setUp(self):
        self.conn = build_test_db()

    def tearDown(self):
        self.conn.close()

    def _tables(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return [r["name"] for r in rows]

    def _triggers(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        return [r["name"] for r in rows]

    def test_all_expected_tables_exist(self):
        existing = self._tables()
        for t in EXPECTED_TABLES:
            with self.subTest(table=t):
                self.assertIn(t, existing, f"Table '{t}' not found in schema.")

    def test_all_expected_triggers_exist(self):
        existing = self._triggers()
        for trg in EXPECTED_TRIGGERS:
            with self.subTest(trigger=trg):
                self.assertIn(trg, existing, f"Trigger '{trg}' not found.")

    def test_foreign_keys_enabled(self):
        result = self.conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        self.assertEqual(result, 1, "PRAGMA foreign_keys should be ON (1).")

    def test_categories_table_has_required_columns(self):
        cols = {r["name"] for r in
                self.conn.execute("PRAGMA table_info(categories)").fetchall()}
        for col in ("category_id", "category_name", "description", "created_at"):
            self.assertIn(col, cols)

    def test_products_table_has_required_columns(self):
        cols = {r["name"] for r in
                self.conn.execute("PRAGMA table_info(products)").fetchall()}
        for col in ("product_id", "product_name", "sku", "category_id",
                    "quantity_in_stock", "reorder_level",
                    "purchase_price", "selling_price"):
            self.assertIn(col, cols)

    def test_sales_table_has_required_columns(self):
        cols = {r["name"] for r in
                self.conn.execute("PRAGMA table_info(sales)").fetchall()}
        for col in ("sale_id", "customer_id", "sale_date",
                    "total_amount", "payment_method", "status"):
            self.assertIn(col, cols)

    def test_inventory_movements_table_exists(self):
        cols = {r["name"] for r in
                self.conn.execute("PRAGMA table_info(inventory_movements)").fetchall()}
        self.assertIn("movement_type", cols)
        self.assertIn("quantity_change", cols)

    def test_unique_constraint_on_category_name(self):
        self.conn.execute(
            "INSERT INTO categories(category_name) VALUES (?)", ("TestCat",))
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO categories(category_name) VALUES (?)", ("TestCat",))
            self.conn.commit()

    def test_unique_constraint_on_sku(self):
        self.conn.execute(
            "INSERT INTO categories(category_name) VALUES (?)", ("Cat",))
        self.conn.execute("""
            INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price)
            VALUES (?,?,1,10,15)
        """, ("Prod A", "SKU-001"))
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price)
                VALUES (?,?,1,10,15)
            """, ("Prod B", "SKU-001"))
            self.conn.commit()

    def test_products_selling_price_check_constraint(self):
        self.conn.execute(
            "INSERT INTO categories(category_name) VALUES (?)", ("Cat2",))
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO products(product_name, sku, category_id, purchase_price, selling_price)
                VALUES (?,?,1,10,-5)
            """, ("Bad Prod", "SKU-BAD"))
            self.conn.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)

