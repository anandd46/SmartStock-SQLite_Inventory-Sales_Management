"""
database/seed.py
SmartStock - Seed / Demo Data Generator
Created by Anand D

Inserts realistic demonstration data.
Safe to call: checks for existing data before inserting.
Use reset_demo_data() to wipe and re-seed cleanly.
"""

import sqlite3
import logging
from database.connection import get_connection, close_connection

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# SEED DATA DEFINITIONS
# ------------------------------------------------------------------

CATEGORIES = [
    ("Electronics",       "Phones, tablets, laptops, accessories"),
    ("Mobile Accessories","Cases, chargers, cables, earphones"),
    ("Computers",         "Desktops, laptops, peripherals"),
    ("Home Appliances",   "Fans, mixers, irons, refrigerators"),
    ("Stationery",        "Pens, notebooks, files, staplers"),
    ("Grocery",           "Daily essentials, packaged food"),
    ("Personal Care",     "Soaps, shampoos, creams, toothpaste"),
    ("Sports & Fitness",  "Gym equipment, outdoor sports goods"),
    ("Books",             "Academic and general books"),
    ("Clothing",          "Shirts, trousers, traditional wear"),
]

SUPPLIERS = [
    ("TechZone Distributors",  "9876543210", "techzone@example.com",    "45 Market Street, Bangalore"),
    ("Sunrise Electronics",    "9123456780", "sunrise@example.com",      "12 Gandhi Road, Chennai"),
    ("Metro Wholesalers",      "9988776655", "metro@example.com",        "88 Commercial Area, Mumbai"),
    ("Global Traders",         "9001122334", "global@example.com",       "22 MG Road, Hyderabad"),
    ("Prime Distributors",     "9345678901", "prime@example.com",        "7 Nehru Nagar, Pune"),
    ("FastLine Supplies",      "9556677889", "fastline@example.com",     "33 Station Road, Kolkata"),
    ("BrightStar Wholesale",   "9667788990", "brightstar@example.com",   "19 Ring Road, Delhi"),
    ("Apex Goods",             "9778899001", "apex@example.com",         "55 Industrial Zone, Ahmedabad"),
    ("Royal Imports",          "9889900112", "royal@example.com",        "6 Port Area, Kochi"),
    ("ValueMart Suppliers",    "9990011223", "valuemart@example.com",    "40 Commercial St, Jaipur"),
    ("National Distributors",  "9112233445", "national@example.com",     "11 Central Ave, Lucknow"),
    ("Heritage Trading Co.",   "9223344556", "heritage@example.com",     "77 Heritage Road, Mysuru"),
]

CUSTOMERS = [
    ("Ravi Kumar",      "9811234567", "ravi.kumar@mail.com"),
    ("Priya Sharma",    "9822345678", "priya.sharma@mail.com"),
    ("Arjun Mehta",     "9833456789", "arjun.mehta@mail.com"),
    ("Sneha Reddy",     "9844567890", "sneha.reddy@mail.com"),
    ("Vikram Singh",    "9855678901", "vikram.singh@mail.com"),
    ("Ananya Nair",     "9866789012", "ananya.nair@mail.com"),
    ("Rohit Verma",     "9877890123", "rohit.verma@mail.com"),
    ("Kavitha Das",     "9888901234", "kavitha.das@mail.com"),
    ("Suresh Pillai",   "9899012345", "suresh.pillai@mail.com"),
    ("Meena Iyer",      "9810123456", "meena.iyer@mail.com"),
    ("Deepak Joshi",    "9821234567", "deepak.joshi@mail.com"),
    ("Lakshmi Rao",     "9832345678", "lakshmi.rao@mail.com"),
    ("Mohan Gupta",     "9843456789", "mohan.gupta@mail.com"),
    ("Pooja Mishra",    "9854567890", "pooja.mishra@mail.com"),
    ("Ganesh Patil",    "9865678901", "ganesh.patil@mail.com"),
    ("Sunita Agarwal",  "9876789012", "sunita.agarwal@mail.com"),
    ("Kiran Bose",      "9887890123", "kiran.bose@mail.com"),
    ("Ajay Choudhary",  "9898901234", "ajay.choudhary@mail.com"),
    ("Rekha Tiwari",    "9809012345", "rekha.tiwari@mail.com"),
    ("Harish Kapoor",   "9820123456", "harish.kapoor@mail.com"),
    ("Divya Menon",     "9831234567", "divya.menon@mail.com"),
    ("Sanjay Patel",    "9842345678", "sanjay.patel@mail.com"),
    ("Asha Bhatt",      "9853456789", "asha.bhatt@mail.com"),
    ("Nitin Sharma",    "9864567890", "nitin.sharma@mail.com"),
    ("Radha Kumari",    "9875678901", "radha.kumari@mail.com"),
    ("Tarun Malhotra",  "9886789012", "tarun.malhotra@mail.com"),
    ("Chitra Venkat",   "9897890123", "chitra.venkat@mail.com"),
    ("Ashok Rajan",     "9808901234", "ashok.rajan@mail.com"),
    ("Shruti Nambiar",  "9819012345", "shruti.nambiar@mail.com"),
    ("Pavan Desai",     "9830123456", "pavan.desai@mail.com"),
]

# Products: (name, sku, cat_idx, sup_idx, purchase_price, selling_price, reorder_level)
# Indexes are 1-based to match AUTOINCREMENT IDs
PRODUCTS = [
    # Electronics (cat 1)
    ("Samsung Galaxy A54",    "SKU-E001", 1, 1,  22000, 26999, 5),
    ("Redmi Note 12",         "SKU-E002", 1, 2,  13500, 16999, 8),
    ("OnePlus Nord CE3",      "SKU-E003", 1, 1,  18000, 22499, 5),
    ("Realme 11 Pro",         "SKU-E004", 1, 2,  16000, 19999, 6),
    ("Vivo Y100",             "SKU-E005", 1, 3,  17000, 20999, 5),
    # Mobile Accessories (cat 2)
    ("USB-C Charging Cable",  "SKU-A001", 2, 4,   120,   249, 20),
    ("Wireless Earbuds",      "SKU-A002", 2, 4,   950,  1799, 15),
    ("Phone Tempered Glass",  "SKU-A003", 2, 5,    45,    99, 30),
    ("Mobile Back Cover",     "SKU-A004", 2, 5,    80,   199, 25),
    ("65W Fast Charger",      "SKU-A005", 2, 4,   650,  1299, 12),
    # Computers (cat 3)
    ("HP Laptop 15s",         "SKU-C001", 3, 1,  38000, 45999, 3),
    ("Dell Inspiron 14",      "SKU-C002", 3, 1,  42000, 51999, 3),
    ("Logitech Wireless Mouse","SKU-C003",3, 6,   450,   999, 10),
    ("Mechanical Keyboard",   "SKU-C004", 3, 6,  1200,  2499, 8),
    ("USB Hub 4-Port",        "SKU-C005", 3, 7,   280,   599, 12),
    # Home Appliances (cat 4)
    ("Table Fan 16 inch",     "SKU-H001", 4, 8,  1800,  2799, 5),
    ("Electric Iron 1000W",   "SKU-H002", 4, 8,   700,  1299, 8),
    ("Hand Blender",          "SKU-H003", 4, 9,  1200,  1999, 5),
    ("Room Heater 2000W",     "SKU-H004", 4, 8,  2200,  3499, 4),
    ("LED Desk Lamp",         "SKU-H005", 4, 7,   450,   899, 10),
    # Stationery (cat 5)
    ("A4 Notebook 200 Pages", "SKU-S001", 5, 10,   40,    99, 50),
    ("Ball Pen Pack 10",      "SKU-S002", 5, 10,   35,    79, 40),
    ("Stapler with Pins",     "SKU-S003", 5, 10,  150,   299, 20),
    ("Highlighter Set 5",     "SKU-S004", 5, 10,   80,   179, 25),
    ("File Folder A4",        "SKU-S005", 5, 11,   25,    59, 60),
    # Grocery (cat 6)
    ("Basmati Rice 5kg",      "SKU-G001", 6, 11,  280,   399, 30),
    ("Refined Oil 1L",        "SKU-G002", 6, 11,  130,   175, 25),
    ("Toor Dal 1kg",          "SKU-G003", 6, 12,   90,   135, 20),
    ("Sugar 1kg",             "SKU-G004", 6, 12,   42,    65, 30),
    ("Tea Powder 250g",       "SKU-G005", 6, 12,   85,   130, 20),
    # Personal Care (cat 7)
    ("Dove Soap 100g",        "SKU-P001", 7, 3,   35,    65, 30),
    ("Head & Shoulders 400ml","SKU-P002", 7, 3,  180,   299, 20),
    ("Colgate Toothpaste 200g","SKU-P003",7, 3,   70,   120, 25),
    ("Gillette Shaving Cream","SKU-P004", 7, 3,   90,   160, 15),
    ("Nivea Face Cream 50ml", "SKU-P005", 7, 3,  150,   265, 15),
    # Sports (cat 8)
    ("Yoga Mat 6mm",          "SKU-SP01", 8, 9,  350,   699, 10),
    ("Dumbbell Set 5kg",      "SKU-SP02", 8, 9,  800,  1499, 6),
    ("Skipping Rope",         "SKU-SP03", 8, 9,   80,   199, 15),
    ("Badminton Racket Set",  "SKU-SP04", 8, 9,  600,  1199, 8),
    ("Water Bottle 1L",       "SKU-SP05", 8, 10,  90,   199, 20),
    # Books (cat 9)
    ("Python Programming",    "SKU-B001", 9, 11, 280,   499, 10),
    ("DBMS Concepts",         "SKU-B002", 9, 11, 260,   450, 10),
    ("Data Structures",       "SKU-B003", 9, 11, 290,   520, 8),
    ("Operating Systems",     "SKU-B004", 9, 11, 270,   480, 8),
    ("Computer Networks",     "SKU-B005", 9, 12, 250,   440, 8),
    # Clothing (cat 10)
    ("Cotton T-Shirt (M)",    "SKU-CL01",10, 12, 180,   399, 20),
    ("Formal Shirt (M)",      "SKU-CL02",10, 12, 350,   699, 15),
    ("Denim Jeans (32)",      "SKU-CL03",10, 12, 600,  1199, 10),
    ("Track Pants",           "SKU-CL04",10, 12, 220,   499, 15),
    ("Ethnic Kurta",          "SKU-CL05",10, 12, 400,   849, 12),
]

# Opening stock: (sku, qty) – only items that need initial stock
OPENING_STOCK = {
    "SKU-E001": 25, "SKU-E002": 40, "SKU-E003": 20, "SKU-E004": 30, "SKU-E005": 22,
    "SKU-A001": 150,"SKU-A002": 80, "SKU-A003": 200,"SKU-A004": 120,"SKU-A005": 60,
    "SKU-C001": 15, "SKU-C002": 12, "SKU-C003": 70, "SKU-C004": 45, "SKU-C005": 90,
    "SKU-H001": 30, "SKU-H002": 50, "SKU-H003": 25, "SKU-H004": 20, "SKU-H005": 60,
    "SKU-S001": 200,"SKU-S002": 250,"SKU-S003": 80, "SKU-S004": 100,"SKU-S005": 300,
    "SKU-G001": 100,"SKU-G002": 80, "SKU-G003": 120,"SKU-G004": 150,"SKU-G005": 90,
    "SKU-P001": 120,"SKU-P002": 60, "SKU-P003": 100,"SKU-P004": 50, "SKU-P005": 40,
    "SKU-SP01": 35, "SKU-SP02": 20, "SKU-SP03": 55, "SKU-SP04": 25, "SKU-SP05": 80,
    "SKU-B001": 45, "SKU-B002": 40, "SKU-B003": 35, "SKU-B004": 38, "SKU-B005": 32,
    "SKU-CL01": 60, "SKU-CL02": 45, "SKU-CL03": 30, "SKU-CL04": 50, "SKU-CL05": 35,
}

# Historical purchases: (supplier_idx, date, items: [(sku, qty, unit_cost)])
HISTORICAL_PURCHASES = [
    (1, "2025-07-15", [("SKU-E001",10,21500),("SKU-E002",20,13000),("SKU-A001",100,115)]),
    (2, "2025-07-20", [("SKU-E003",8, 17500),("SKU-E004",15,15500),("SKU-A002",40,900)]),
    (4, "2025-08-02", [("SKU-A001",80, 115),("SKU-A005",30,620),("SKU-A003",150,42)]),
    (1, "2025-08-10", [("SKU-C001",6, 37000),("SKU-C002",5,41000),("SKU-C003",30,430)]),
    (8, "2025-08-20", [("SKU-H001",15,1750),("SKU-H002",25,680),("SKU-H005",30,430)]),
    (10,"2025-09-05", [("SKU-S001",100,38),("SKU-S002",150,32),("SKU-S005",200,22)]),
    (11,"2025-09-12", [("SKU-G001",60,275),("SKU-G002",50,125),("SKU-G003",70,88)]),
    (3, "2025-09-18", [("SKU-P001",80,33),("SKU-P002",40,172),("SKU-P003",60,67)]),
    (9, "2025-10-01", [("SKU-SP01",20,330),("SKU-SP02",10,780),("SKU-SP03",30,75)]),
    (11,"2025-10-08", [("SKU-B001",25,270),("SKU-B002",20,255),("SKU-B003",18,282)]),
    (6, "2025-10-15", [("SKU-CL01",30,175),("SKU-CL02",20,340),("SKU-CL03",15,585)]),
    (2, "2025-10-22", [("SKU-E005",12,16500),("SKU-A004",60,76),("SKU-A005",20,630)]),
]

# Historical sales: (customer_idx_or_None, date, payment, items: [(sku, qty)])
HISTORICAL_SALES = [
    (1,    "2025-07-16", "Cash",   [("SKU-E001",2),("SKU-A001",5)]),
    (2,    "2025-07-18", "UPI",    [("SKU-E002",1),("SKU-A002",2)]),
    (3,    "2025-07-25", "Card",   [("SKU-C001",1),("SKU-C003",2)]),
    (None, "2025-07-28", "Cash",   [("SKU-S001",3),("SKU-S002",5)]),
    (4,    "2025-08-03", "UPI",    [("SKU-G001",2),("SKU-G002",3)]),
    (5,    "2025-08-07", "Cash",   [("SKU-P001",4),("SKU-P003",3)]),
    (6,    "2025-08-12", "Card",   [("SKU-H001",1),("SKU-H005",2)]),
    (7,    "2025-08-18", "UPI",    [("SKU-E002",2),("SKU-A001",10)]),
    (8,    "2025-08-25", "Cash",   [("SKU-SP01",1),("SKU-SP03",2)]),
    (9,    "2025-09-02", "UPI",    [("SKU-B001",2),("SKU-B002",1)]),
    (10,   "2025-09-08", "Card",   [("SKU-CL01",3),("SKU-CL04",2)]),
    (None, "2025-09-14", "Cash",   [("SKU-G003",5),("SKU-G004",4)]),
    (11,   "2025-09-20", "UPI",    [("SKU-E003",1),("SKU-A002",1)]),
    (12,   "2025-09-25", "Cash",   [("SKU-C003",1),("SKU-C004",1)]),
    (13,   "2025-10-01", "Card",   [("SKU-H002",1),("SKU-H003",1)]),
    (14,   "2025-10-05", "UPI",    [("SKU-P002",2),("SKU-P005",1)]),
    (15,   "2025-10-09", "Cash",   [("SKU-S003",1),("SKU-S004",2)]),
    (16,   "2025-10-12", "Card",   [("SKU-E004",1),("SKU-A005",1)]),
    (None, "2025-10-15", "Cash",   [("SKU-G001",3),("SKU-G005",4)]),
    (17,   "2025-10-18", "UPI",    [("SKU-SP02",1),("SKU-SP05",2)]),
    (18,   "2025-10-20", "Card",   [("SKU-B003",1),("SKU-B005",2)]),
    (19,   "2025-10-22", "Cash",   [("SKU-CL02",2),("SKU-CL05",1)]),
    (20,   "2025-10-24", "UPI",    [("SKU-E001",1),("SKU-A003",5)]),
    (1,    "2025-10-25", "Card",   [("SKU-E002",3),("SKU-A001",20)]),
    (2,    "2025-10-26", "Cash",   [("SKU-C002",1),("SKU-C005",2)]),
    (None, "2025-10-27", "UPI",    [("SKU-H004",1),("SKU-H005",1)]),
    (3,    "2025-10-28", "Cash",   [("SKU-G002",5),("SKU-G004",6)]),
]


# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------

def _table_has_data(conn: sqlite3.Connection, table: str) -> bool:
    """Return True if the table contains at least one row."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0] > 0


def _get_product_id(conn: sqlite3.Connection, sku: str) -> int | None:
    """Return product_id for a given SKU, or None."""
    row = conn.execute("SELECT product_id FROM products WHERE sku = ?", (sku,)).fetchone()
    return row["product_id"] if row else None


def _get_selling_price(conn: sqlite3.Connection, product_id: int) -> float:
    row = conn.execute("SELECT selling_price FROM products WHERE product_id = ?",
                       (product_id,)).fetchone()
    return row["selling_price"] if row else 0.0


# ------------------------------------------------------------------
# SEED FUNCTIONS
# ------------------------------------------------------------------

def seed_categories(conn: sqlite3.Connection) -> None:
    if _table_has_data(conn, "categories"):
        logger.info("Categories already seeded – skipping.")
        return
    conn.executemany(
        "INSERT INTO categories (category_name, description) VALUES (?, ?)",
        CATEGORIES
    )
    logger.info(f"Seeded {len(CATEGORIES)} categories.")


def seed_suppliers(conn: sqlite3.Connection) -> None:
    if _table_has_data(conn, "suppliers"):
        logger.info("Suppliers already seeded – skipping.")
        return
    conn.executemany(
        "INSERT INTO suppliers (supplier_name, phone, email, address) VALUES (?, ?, ?, ?)",
        SUPPLIERS
    )
    logger.info(f"Seeded {len(SUPPLIERS)} suppliers.")


def seed_customers(conn: sqlite3.Connection) -> None:
    if _table_has_data(conn, "customers"):
        logger.info("Customers already seeded – skipping.")
        return
    conn.executemany(
        "INSERT INTO customers (customer_name, phone, email) VALUES (?, ?, ?)",
        CUSTOMERS
    )
    logger.info(f"Seeded {len(CUSTOMERS)} customers.")


def seed_products(conn: sqlite3.Connection) -> None:
    if _table_has_data(conn, "products"):
        logger.info("Products already seeded – skipping.")
        return
    conn.executemany("""
        INSERT INTO products
            (product_name, sku, category_id, supplier_id,
             purchase_price, selling_price, reorder_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, PRODUCTS)
    logger.info(f"Seeded {len(PRODUCTS)} products.")


def seed_opening_stock(conn: sqlite3.Connection) -> None:
    """
    Set opening stock directly (bypassing purchase triggers) via direct
    UPDATE on products and INSERT into inventory_movements.
    Checks inventory_movements for 'OPENING_STOCK' to avoid re-seeding.
    """
    already = conn.execute(
        "SELECT COUNT(*) FROM inventory_movements WHERE movement_type='OPENING_STOCK'"
    ).fetchone()[0]
    if already > 0:
        logger.info("Opening stock already recorded – skipping.")
        return

    for sku, qty in OPENING_STOCK.items():
        pid = _get_product_id(conn, sku)
        if not pid:
            logger.warning(f"Opening stock: product SKU {sku} not found.")
            continue
        conn.execute(
            "UPDATE products SET quantity_in_stock = quantity_in_stock + ?, "
            "updated_at = datetime('now','localtime') WHERE product_id = ?",
            (qty, pid)
        )
        conn.execute("""
            INSERT INTO inventory_movements
                (product_id, movement_type, quantity_change,
                 reference_type, movement_date, notes)
            VALUES (?, 'OPENING_STOCK', ?, 'seed', datetime('now','localtime'),
                    'Initial opening stock from seed data')
        """, (pid, qty))
    logger.info(f"Opening stock applied for {len(OPENING_STOCK)} products.")


def seed_purchases(conn: sqlite3.Connection) -> None:
    """Insert historical purchase transactions. Stock is updated by the trigger."""
    if _table_has_data(conn, "purchases"):
        logger.info("Purchases already seeded – skipping.")
        return

    for sup_idx, pdate, items in HISTORICAL_PURCHASES:
        # Calculate total
        total = sum(qty * cost for _, qty, cost in items)
        cursor = conn.execute("""
            INSERT INTO purchases (supplier_id, purchase_date, total_amount, status)
            VALUES (?, ?, ?, 'COMPLETED')
        """, (sup_idx, pdate, total))
        purchase_id = cursor.lastrowid

        for sku, qty, cost in items:
            pid = _get_product_id(conn, sku)
            if not pid:
                logger.warning(f"Purchase seed: SKU {sku} not found.")
                continue
            line_total = qty * cost
            # INSERT triggers trg_purchase_item_stock_increase automatically
            conn.execute("""
                INSERT INTO purchase_items
                    (purchase_id, product_id, quantity, unit_cost, line_total)
                VALUES (?, ?, ?, ?, ?)
            """, (purchase_id, pid, qty, cost, line_total))

    logger.info(f"Seeded {len(HISTORICAL_PURCHASES)} purchase transactions.")


def seed_sales(conn: sqlite3.Connection) -> None:
    """Insert historical sales. Stock is decreased by the trigger."""
    if _table_has_data(conn, "sales"):
        logger.info("Sales already seeded – skipping.")
        return

    for cust_idx, sdate, payment, items in HISTORICAL_SALES:
        # Calculate total using current selling prices
        total = 0.0
        item_rows = []
        for sku, qty in items:
            pid = _get_product_id(conn, sku)
            if not pid:
                logger.warning(f"Sale seed: SKU {sku} not found.")
                continue
            price = _get_selling_price(conn, pid)
            line_total = qty * price
            total += line_total
            item_rows.append((pid, qty, price, line_total))

        if not item_rows:
            continue

        cursor = conn.execute("""
            INSERT INTO sales
                (customer_id, sale_date, total_amount, payment_method, status)
            VALUES (?, ?, ?, ?, 'COMPLETED')
        """, (cust_idx, sdate, total, payment))
        sale_id = cursor.lastrowid

        for pid, qty, price, line_total in item_rows:
            try:
                conn.execute("""
                    INSERT INTO sale_items
                        (sale_id, product_id, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                """, (sale_id, pid, qty, price, line_total))
            except sqlite3.Error as e:
                logger.warning(f"Skipping sale item (pid={pid}, qty={qty}): {e}")

    logger.info(f"Seeded historical sales transactions.")


# ------------------------------------------------------------------
# MAIN ENTRY POINTS
# ------------------------------------------------------------------

def seed_all(db_path: str = None) -> None:
    """
    Seed all demo data in the correct dependency order.
    Each section is idempotent – safe to call multiple times.
    """
    conn = get_connection(db_path)
    try:
        seed_categories(conn)
        seed_suppliers(conn)
        seed_customers(conn)
        seed_products(conn)
        seed_opening_stock(conn)
        seed_purchases(conn)
        seed_sales(conn)
        conn.commit()
        logger.info("All seed data committed successfully.")
        print("[OK] Seed data inserted successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Seed data failed: {e}")
        print(f"[ERROR] Seed data failed: {e}")
        raise
    finally:
        close_connection(conn)


def reset_and_reseed(db_path: str = None) -> None:
    """
    WARNING: Deletes all data and re-seeds from scratch.
    Only use for development / demo reset.
    """
    conn = get_connection(db_path)
    try:
        # Disable FK temporarily to allow truncation in any order
        conn.execute("PRAGMA foreign_keys = OFF;")
        for table in ["audit_logs", "inventory_movements",
                      "sale_items", "sales",
                      "purchase_items", "purchases",
                      "products", "customers", "suppliers", "categories"]:
            conn.execute(f"DELETE FROM {table}")
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        logger.info("All tables cleared for re-seed.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Reset failed: {e}")
        raise
    finally:
        close_connection(conn)

    seed_all(db_path)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("⚠️  Resetting and re-seeding demo data...")
        reset_and_reseed()
    else:
        print("🌱 Seeding demo data (safe mode)...")
        seed_all()
