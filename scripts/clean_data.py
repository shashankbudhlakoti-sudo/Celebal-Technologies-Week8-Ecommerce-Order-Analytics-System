"""
PHASE 1 - Part 2: Data Cleaning
================================
Reads the raw (messy) CSVs from data/raw/, cleans them, writes cleaned CSVs to
data/cleaned/, and produces a data-quality report at report/data_quality_report.md.

Functions:
    clean_orders()                 - fix date formats, handle NULL customer_ids
    clean_products()               - normalize product names (trim + title case)
    clean_order_items()            - flag PURCHASE vs RETURN, cap discount_percent
    validate_emails()              - return list of customer_ids with invalid emails
    check_referential_integrity()  - find order_items referencing non-existent orders

Run:
    python scripts/clean_data.py
"""

import os
import re
from datetime import datetime

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
REPORT_DIR = os.path.join(BASE_DIR, "report")
os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# 1. clean_orders()
# ---------------------------------------------------------------------------
def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fixes order_date format inconsistencies (DD-MM-YYYY -> YYYY-MM-DD HH:MM:SS)
    and handles NULL/empty customer_id values.

    Returns (cleaned_df, issues_dict)
    """
    df = df.copy()
    issues = {"wrong_date_format_fixed": 0, "null_customer_id_handled": 0}

    def fix_date(value):
        value = str(value).strip()
        # Correct format already
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        # Wrong format: DD-MM-YYYY (date only, no time)
        try:
            dt = datetime.strptime(value, "%d-%m-%Y")
            issues["wrong_date_format_fixed"] += 1
            return dt
        except ValueError:
            pass
        # Fallback: let pandas try to infer, else NaT
        parsed = pd.to_datetime(value, errors="coerce")
        return parsed if not pd.isna(parsed) else pd.NaT

    df["order_date"] = df["order_date"].apply(fix_date)
    df["order_date"] = pd.to_datetime(df["order_date"])

    # NULL / empty customer_id -> mark as guest order instead of dropping the order
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    is_missing = df["customer_id"].isin(["", "nan", "NULL", "None"]) | df["customer_id"].isna()
    issues["null_customer_id_handled"] = int(is_missing.sum())
    df["is_guest_order"] = is_missing.astype(int)
    df.loc[is_missing, "customer_id"] = "UNKNOWN"

    df["status"] = df["status"].str.strip().str.upper()
    df["region_code"] = df["region_code"].str.strip().str.upper()

    return df, issues


# ---------------------------------------------------------------------------
# 2. clean_products()
# ---------------------------------------------------------------------------
def clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Normalizes product_name: trims extra whitespace and converts to Title Case.
    """
    df = df.copy()
    issues = {"product_names_normalized": 0}

    original = df["product_name"].copy()
    df["product_name"] = (
        df["product_name"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.title()
    )
    issues["product_names_normalized"] = int((original.astype(str).str.strip() != df["product_name"]).sum())

    df["category"] = df["category"].str.strip().str.title()
    df["subcategory"] = df["subcategory"].str.strip().str.title()
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce")

    return df, issues


# ---------------------------------------------------------------------------
# 3. clean_order_items()  (supporting cleaner, not explicitly named in spec
#     but needed to make order_items analysis-ready)
# ---------------------------------------------------------------------------
def clean_order_items(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    - Flags each row as PURCHASE or RETURN based on the sign of quantity.
    - Adds quantity_abs (absolute value) for easy aggregation.
    - Caps discount_percent to the valid [0, 100] range (invalid values are
      logged, not silently discarded, so they still show up in the report).
    """
    df = df.copy()
    issues = {"negative_quantity_rows": 0, "zero_quantity_rows": 0, "discount_over_100_capped": 0}

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    issues["negative_quantity_rows"] = int((df["quantity"] < 0).sum())
    issues["zero_quantity_rows"] = int((df["quantity"] == 0).sum())

    df["transaction_type"] = df["quantity"].apply(
        lambda q: "RETURN" if q < 0 else ("ZERO_QTY" if q == 0 else "PURCHASE")
    )
    df["quantity_abs"] = df["quantity"].abs()

    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")
    over_100 = df["discount_percent"] > 100
    issues["discount_over_100_capped"] = int(over_100.sum())
    df.loc[over_100, "discount_percent"] = 100.0
    df.loc[df["discount_percent"] < 0, "discount_percent"] = 0.0

    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount_percent"] / 100)

    return df, issues


# ---------------------------------------------------------------------------
# 4. validate_emails()
# ---------------------------------------------------------------------------
def validate_emails(df: pd.DataFrame) -> list:
    """
    Returns a list of customer_ids whose email is invalid
    (missing '@', missing domain, or otherwise malformed).
    """
    invalid_mask = ~df["email"].astype(str).str.match(EMAIL_RE)
    return df.loc[invalid_mask, "customer_id"].tolist()


# ---------------------------------------------------------------------------
# 5. check_referential_integrity()
# ---------------------------------------------------------------------------
def check_referential_integrity(orders_df: pd.DataFrame, order_items_df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds order_items rows whose order_id does not exist in orders_df.
    Returns the offending rows (empty DataFrame if none found).
    """
    valid_order_ids = set(orders_df["order_id"])
    orphan_mask = ~order_items_df["order_id"].isin(valid_order_ids)
    return order_items_df.loc[orphan_mask]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run():
    print("Loading raw data...")
    customers = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    products = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    orders = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))

    print("Cleaning orders...")
    orders_clean, orders_issues = clean_orders(orders)

    print("Cleaning products...")
    products_clean, products_issues = clean_products(products)

    print("Cleaning order_items...")
    order_items_clean, order_items_issues = clean_order_items(order_items)

    print("Validating emails...")
    invalid_email_ids = validate_emails(customers)

    print("Checking referential integrity...")
    orphan_items = check_referential_integrity(orders_clean, order_items_clean)

    # Drop orphan order_items from the cleaned dataset (kept only in the report for audit)
    order_items_clean_final = order_items_clean.loc[~order_items_clean.index.isin(orphan_items.index)]

    # --- Write cleaned CSVs ---
    customers.to_csv(os.path.join(CLEAN_DIR, "customers.csv"), index=False)
    products_clean.to_csv(os.path.join(CLEAN_DIR, "products.csv"), index=False)
    orders_clean.to_csv(os.path.join(CLEAN_DIR, "orders.csv"), index=False)
    order_items_clean_final.to_csv(os.path.join(CLEAN_DIR, "order_items.csv"), index=False)

    # --- Data quality report ---
    lines = []
    lines.append("# Data Quality Report\n")
    lines.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n")

    lines.append("## orders.csv (clean_orders)")
    lines.append(f"- Total rows processed: {len(orders)}")
    lines.append(f"- Rows with wrong date format fixed (DD-MM-YYYY -> YYYY-MM-DD HH:MM:SS): {orders_issues['wrong_date_format_fixed']}")
    lines.append(f"- Rows with NULL/empty customer_id handled (set to 'UNKNOWN', flagged is_guest_order=1): {orders_issues['null_customer_id_handled']}\n")

    lines.append("## products.csv (clean_products)")
    lines.append(f"- Total rows processed: {len(products)}")
    lines.append(f"- Product names normalized (trimmed + Title Case): {products_issues['product_names_normalized']}\n")

    lines.append("## order_items.csv (clean_order_items)")
    lines.append(f"- Total rows processed: {len(order_items)}")
    lines.append(f"- Negative quantity rows (flagged as RETURN): {order_items_issues['negative_quantity_rows']}")
    lines.append(f"- Zero quantity rows (flagged as ZERO_QTY): {order_items_issues['zero_quantity_rows']}")
    lines.append(f"- discount_percent > 100 capped to 100: {order_items_issues['discount_over_100_capped']}\n")

    lines.append("## customers.csv (validate_emails)")
    lines.append(f"- Total customers: {len(customers)}")
    lines.append(f"- Invalid emails found: {len(invalid_email_ids)}")
    lines.append(f"- Sample invalid-email customer_ids: {invalid_email_ids[:10]}\n")

    lines.append("## Referential Integrity (check_referential_integrity)")
    lines.append(f"- order_items rows referencing a non-existent order_id: {len(orphan_items)}")
    if len(orphan_items):
        lines.append(f"- Orphan order_ids: {sorted(orphan_items['order_id'].unique().tolist())}")
    lines.append("- These rows were EXCLUDED from data/cleaned/order_items.csv (kept only here for audit).\n")

    lines.append("## Output")
    lines.append("- Cleaned CSVs written to `data/cleaned/`")
    lines.append("- This report: `report/data_quality_report.md`")

    report_path = os.path.join(REPORT_DIR, "data_quality_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print("-" * 70)
    print(f"Cleaned CSVs written to: {os.path.abspath(CLEAN_DIR)}")
    print(f"Data quality report written to: {os.path.abspath(report_path)}")
    print("-" * 70)
    print("\n".join(lines))


if __name__ == "__main__":
    run()
