"""
PHASE 1 - Part 1: Data Generation
==================================
Generates 4 realistic-but-messy CSV files for the E-commerce Order Analytics System:

    data/raw/customers.csv
    data/raw/products.csv
    data/raw/orders.csv
    data/raw/order_items.csv

Intentional data-quality issues (as required by the assignment):
    - 5%  of orders.csv rows have a NULL/empty customer_id
    - 3%  of order_items.csv rows have a negative quantity (returns)
    - Some orders.csv rows have order_date in the WRONG format (DD-MM-YYYY instead of YYYY-MM-DD HH:MM:SS)
    - Some products.csv product_name values have extra spaces / inconsistent casing
    - 2%  of customers.csv emails are invalid (missing '@' or missing domain)
    - A handful of order_items.csv rows deliberately reference an order_id that
      does NOT exist in orders.csv (referential-integrity issue, found later by
      check_referential_integrity())

Run:
    python scripts/generate_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

N_CUSTOMERS = 500
N_PRODUCTS = 500
N_ORDERS = 800
N_ORDER_ITEMS = 1800

CATEGORIES = {
    "Electronics": ["Mobiles", "Laptops", "Headphones", "Cameras", "Accessories"],
    "Clothing": ["Men", "Women", "Kids", "Footwear", "Winterwear"],
    "Home": ["Kitchen", "Furniture", "Decor", "Bedding", "Storage"],
    "Books": ["Fiction", "Non-Fiction", "Comics", "Academic", "Children"],
}
REGIONS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
CUSTOMER_TYPES = ["REGULAR", "PREMIUM", "VIP"]
ORDER_STATUSES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]


# ---------------------------------------------------------------------------
# 1. customers.csv
# ---------------------------------------------------------------------------
def generate_customers():
    rows = []
    start = datetime(2021, 1, 1)
    end = datetime(2024, 12, 31)

    for i in range(1, N_CUSTOMERS + 1):
        customer_id = f"C{i:05d}"
        name = fake.name()
        email = fake.email()

        # ~2% invalid emails (missing @ or missing domain)
        if random.random() < 0.02:
            if random.random() < 0.5:
                email = email.replace("@", "")               # missing @
            else:
                email = email.split("@")[0] + "@"             # missing domain

        reg_date = start + timedelta(days=random.randint(0, (end - start).days))
        customer_type = random.choices(CUSTOMER_TYPES, weights=[70, 22, 8])[0]

        rows.append(
            [customer_id, name, email, reg_date.strftime("%Y-%m-%d"), customer_type]
        )

    path = os.path.join(RAW_DIR, "customers.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "customer_name", "email", "registration_date", "customer_type"])
        w.writerows(rows)

    print(f"customers.csv written -> {len(rows)} rows")
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# 2. products.csv
# ---------------------------------------------------------------------------
def generate_products():
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        product_id = f"P{i:05d}"
        category = random.choice(list(CATEGORIES.keys()))
        subcategory = random.choice(CATEGORIES[category])
        base_name = f"{fake.word().capitalize()} {subcategory[:-1] if subcategory.endswith('s') else subcategory} {fake.word().capitalize()}"

        product_name = base_name
        # messy product names: extra spaces / mixed case for ~15% of rows
        if random.random() < 0.15:
            variant = random.random()
            if variant < 0.34:
                product_name = "   " + base_name + "   "        # extra spaces
            elif variant < 0.67:
                product_name = base_name.upper()                 # ALL CAPS
            else:
                product_name = base_name.lower()                 # all lower

        cost_price = round(random.uniform(50, 25000), 2)

        rows.append([product_id, product_name, category, subcategory, cost_price])

    path = os.path.join(RAW_DIR, "products.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "product_name", "category", "subcategory", "cost_price"])
        w.writerows(rows)

    print(f"products.csv written -> {len(rows)} rows")
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# 3. orders.csv
# ---------------------------------------------------------------------------
def generate_orders(customer_ids):
    rows = []
    start = datetime(2023, 1, 1)
    end = datetime(2024, 12, 31, 23, 59, 59)

    order_ids = []
    for i in range(1, N_ORDERS + 1):
        order_id = f"O{i:06d}"
        order_ids.append(order_id)

        # 5% NULL customer_id
        if random.random() < 0.05:
            customer_id = ""
        else:
            customer_id = random.choice(customer_ids)

        order_dt = start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

        # Most rows correct format YYYY-MM-DD HH:MM:SS; ~6% wrong format DD-MM-YYYY (date only)
        if random.random() < 0.06:
            order_date_str = order_dt.strftime("%d-%m-%Y")
        else:
            order_date_str = order_dt.strftime("%Y-%m-%d %H:%M:%S")

        status = random.choices(
            ORDER_STATUSES, weights=[10, 15, 55, 12, 8]
        )[0]
        region_code = random.choice(REGIONS)

        rows.append([order_id, customer_id, order_date_str, status, region_code])

    path = os.path.join(RAW_DIR, "orders.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "customer_id", "order_date", "status", "region_code"])
        w.writerows(rows)

    print(f"orders.csv written -> {len(rows)} rows "
          f"(NULL customer_id in ~5%, wrong date format in ~6%)")
    return order_ids


# ---------------------------------------------------------------------------
# 4. order_items.csv
# ---------------------------------------------------------------------------
def generate_order_items(order_ids, product_ids):
    rows = []
    # deliberately include a handful of order_ids that don't exist in orders.csv
    ghost_order_ids = [f"O{900000+i}" for i in range(1, 9)]  # 8 orphan order_ids

    for i in range(1, N_ORDER_ITEMS + 1):
        item_id = f"OI{i:06d}"

        if random.random() < 0.01 and ghost_order_ids:
            order_id = random.choice(ghost_order_ids)  # referential integrity issue
        else:
            order_id = random.choice(order_ids)

        product_id = random.choice(product_ids)
        quantity = random.randint(1, 5)

        # 3% negative quantity (returns)
        if random.random() < 0.03:
            quantity = -abs(quantity)

        unit_price = round(random.uniform(100, 30000), 2)
        discount_percent = round(random.uniform(0, 40), 1)  # occasionally push >100 for edge-case testing
        if random.random() < 0.005:
            discount_percent = round(random.uniform(101, 150), 1)  # intentional invalid edge case

        rows.append([item_id, order_id, product_id, quantity, unit_price, discount_percent])

    path = os.path.join(RAW_DIR, "order_items.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["order_item_id", "order_id", "product_id", "quantity", "unit_price", "discount_percent"])
        w.writerows(rows)

    print(f"order_items.csv written -> {len(rows)} rows "
          f"(~3% negative quantity, {len(ghost_order_ids)} orphan order_id references, "
          f"a few discount_percent > 100)")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating raw (messy) e-commerce dataset...")
    print("-" * 70)
    customer_ids = generate_customers()
    product_ids = generate_products()
    order_ids = generate_orders(customer_ids)
    generate_order_items(order_ids, product_ids)
    print("-" * 70)
    print(f"All raw CSV files written to: {os.path.abspath(RAW_DIR)}")
