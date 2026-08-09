"""
PHASE 1 - Part 5: Edge Case Handling
=====================================
Test functions (plain Python, no pytest dependency required - though pytest
will also auto-discover these since they're named test_*) that verify how the
pipeline behaves for tricky/invalid inputs:

    1. order_items row with an order_id NOT in orders
    2. discount_percent > 100
    3. quantity == 0
    4. order_date in the future

Run directly:
    python scripts/edge_case_tests.py

Or with pytest (if installed):
    pytest scripts/edge_case_tests.py -v
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from clean_data import (  # noqa: E402
    check_referential_integrity,
    clean_order_items,
    clean_orders,
)


# ---------------------------------------------------------------------------
# 1. order_items with an order_id not present in orders
# ---------------------------------------------------------------------------
def test_order_item_with_invalid_order_id():
    orders = pd.DataFrame({
        "order_id": ["O1", "O2"],
        "customer_id": ["C1", "C2"],
        "order_date": ["2024-01-01 10:00:00", "2024-01-02 10:00:00"],
        "status": ["DELIVERED", "PLACED"],
        "region_code": ["NORTH", "SOUTH"],
    })
    order_items = pd.DataFrame({
        "order_item_id": ["OI1", "OI2", "OI3"],
        "order_id": ["O1", "O999", "O2"],   # O999 does not exist in orders
        "product_id": ["P1", "P2", "P3"],
        "quantity": [2, 1, 3],
        "unit_price": [100.0, 200.0, 50.0],
        "discount_percent": [10, 0, 5],
    })

    orphans = check_referential_integrity(orders, order_items)

    assert len(orphans) == 1, f"Expected 1 orphan row, got {len(orphans)}"
    assert orphans.iloc[0]["order_id"] == "O999"
    print("PASS: test_order_item_with_invalid_order_id "
          "-> orphan row (order_id=O999) correctly detected and would be excluded "
          "from cleaned order_items (kept only in the audit report).")


# ---------------------------------------------------------------------------
# 2. discount_percent > 100
# ---------------------------------------------------------------------------
def test_discount_over_100():
    order_items = pd.DataFrame({
        "order_item_id": ["OI1"],
        "order_id": ["O1"],
        "product_id": ["P1"],
        "quantity": [2],
        "unit_price": [100.0],
        "discount_percent": [150],   # invalid: > 100
    })

    cleaned, issues = clean_order_items(order_items)

    assert issues["discount_over_100_capped"] == 1
    assert cleaned.iloc[0]["discount_percent"] == 100.0
    # revenue should reflect the CAPPED discount (100%), i.e. zero, not negative
    assert cleaned.iloc[0]["revenue"] == 0.0
    print("PASS: test_discount_over_100 "
          "-> discount_percent=150 is capped to 100 during cleaning "
          "(logged in the data-quality report), revenue floors at 0 instead of going negative.")


# ---------------------------------------------------------------------------
# 3. quantity == 0
# ---------------------------------------------------------------------------
def test_zero_quantity():
    order_items = pd.DataFrame({
        "order_item_id": ["OI1"],
        "order_id": ["O1"],
        "product_id": ["P1"],
        "quantity": [0],
        "unit_price": [500.0],
        "discount_percent": [10],
    })

    cleaned, issues = clean_order_items(order_items)

    assert issues["zero_quantity_rows"] == 1
    assert cleaned.iloc[0]["transaction_type"] == "ZERO_QTY"
    assert cleaned.iloc[0]["revenue"] == 0.0
    print("PASS: test_zero_quantity "
          "-> quantity=0 is flagged as transaction_type='ZERO_QTY' (neither a "
          "purchase nor a return) and contributes 0 revenue, so it can't silently "
          "skew purchase/return counts in the SQL analysis.")


# ---------------------------------------------------------------------------
# 4. order_date in the future
# ---------------------------------------------------------------------------
def test_future_order_date():
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    orders = pd.DataFrame({
        "order_id": ["O1"],
        "customer_id": ["C1"],
        "order_date": [future_date],
        "status": ["PLACED"],
        "region_code": ["NORTH"],
    })

    cleaned, _ = clean_orders(orders)
    is_future = cleaned.iloc[0]["order_date"] > pd.Timestamp.now()

    # clean_orders() parses the date successfully (no crash / no data loss);
    # flagging it as a business-rule violation is a downstream validation concern.
    assert not pd.isna(cleaned.iloc[0]["order_date"])
    assert is_future, "Future date should still parse and remain identifiably in the future"
    print("PASS: test_future_order_date "
          "-> a future order_date parses successfully rather than crashing or being "
          "silently dropped; downstream validation can flag order_date > today() as "
          "a data-quality issue for manual review.")


# ---------------------------------------------------------------------------
def run_all():
    tests = [
        test_order_item_with_invalid_order_id,
        test_discount_over_100,
        test_zero_quantity,
        test_future_order_date,
    ]
    print("=" * 70)
    print("Running Edge Case Tests")
    print("=" * 70)
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__} -> {e}")
    print("=" * 70)
    print(f"{len(tests) - failures}/{len(tests)} edge case tests passed")
    print("=" * 70)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
