"""
PHASE 1 - Part 3: Load cleaned data into SQLite
=================================================
Loads data/cleaned/*.csv into a SQLite database at data/ecommerce.db,
creating proper tables (with types) so the SQL analysis queries can run.

Run:
    python scripts/load_to_sqlite.py
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
DB_PATH = os.path.join(BASE_DIR, "data", "ecommerce.db")

SCHEMA = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id         TEXT PRIMARY KEY,
    customer_name       TEXT,
    email                TEXT,
    registration_date   TEXT,
    customer_type        TEXT
);

CREATE TABLE products (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT,
    category      TEXT,
    subcategory   TEXT,
    cost_price    REAL
);

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT,
    order_date      TEXT,
    status          TEXT,
    region_code     TEXT,
    is_guest_order  INTEGER
);

CREATE TABLE order_items (
    order_item_id     TEXT PRIMARY KEY,
    order_id          TEXT,
    product_id        TEXT,
    quantity          INTEGER,
    unit_price        REAL,
    discount_percent  REAL,
    transaction_type  TEXT,
    quantity_abs      INTEGER,
    revenue           REAL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_items_product ON order_items(product_id);
"""


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()

    tables = {
        "customers": "customers.csv",
        "products": "products.csv",
        "orders": "orders.csv",
        "order_items": "order_items.csv",
    }

    for table, filename in tables.items():
        df = pd.read_csv(os.path.join(CLEAN_DIR, filename))
        df.to_sql(table, conn, if_exists="append", index=False)
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Loaded {table:<15} -> {count} rows")

    conn.close()
    print(f"\nSQLite database ready at: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    run()
