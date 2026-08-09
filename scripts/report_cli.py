"""
PHASE 1 - Part 4: Python + SQL Integration - CLI Reporting Tool
=================================================================
A command-line tool that:
    1. Takes user input for report type (daily / weekly / monthly)
    2. Takes a date range as input
    3. Connects to the SQLite database (data/ecommerce.db)
    4. Generates a summary report:
         - Total orders, revenue, unique customers
         - Top 3 products (by revenue) in the period
         - Comparison with the immediately preceding period of equal length (% change)

Uses ONLY the standard library (sqlite3, datetime, argparse, sys) - no pandas,
no third-party packages - per the assignment's Part 4 requirement.

Interactive mode:
    python scripts/report_cli.py

Non-interactive mode (useful for scripting/testing):
    python scripts/report_cli.py --type monthly --start 2024-01-01 --end 2024-01-31
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "data", "ecommerce.db")

VALID_TYPES = {"daily", "weekly", "monthly"}


def parse_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d")


def previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Returns the immediately preceding period of the same length."""
    duration = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - duration
    return prev_start, prev_end


def fetch_period_summary(conn: sqlite3.Connection, start: datetime, end: datetime) -> dict:
    end_inclusive = end.strftime("%Y-%m-%d") + " 23:59:59"
    start_str = start.strftime("%Y-%m-%d") + " 00:00:00"

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            COUNT(DISTINCT o.order_id)      AS total_orders,
            COALESCE(SUM(oi.revenue), 0)    AS total_revenue,
            COUNT(DISTINCT o.customer_id)   AS unique_customers
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_date BETWEEN ? AND ?
        """,
        (start_str, end_inclusive),
    )
    total_orders, total_revenue, unique_customers = cur.fetchone()
    total_revenue = total_revenue or 0.0

    cur.execute(
        """
        SELECT p.product_name, SUM(oi.revenue) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.order_date BETWEEN ? AND ?
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT 3
        """,
        (start_str, end_inclusive),
    )
    top_products = cur.fetchall()

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "unique_customers": unique_customers,
        "top_products": top_products,
    }


def pct_change(current: float, previous: float) -> str:
    if previous in (0, None):
        return "N/A (no prior data)"
    change = (current - previous) / previous * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"


def print_report(report_type: str, start: datetime, end: datetime,
                  current: dict, prev_start: datetime, prev_end: datetime, previous: dict) -> None:
    print("=" * 70)
    print(f"{report_type.upper()} SUMMARY REPORT")
    print(f"Period: {start.date()} to {end.date()}")
    print("=" * 70)
    print(f"Total Orders       : {current['total_orders']}")
    print(f"Total Revenue      : {current['total_revenue']:.2f}")
    print(f"Unique Customers   : {current['unique_customers']}")
    print()
    print("Top 3 Products (by revenue):")
    if current["top_products"]:
        for i, (name, revenue) in enumerate(current["top_products"], start=1):
            print(f"  {i}. {name:<35} {revenue:>12.2f}")
    else:
        print("  (no product sales in this period)")
    print()
    print(f"Comparison with previous period ({prev_start.date()} to {prev_end.date()}):")
    print(f"  Orders    : {previous['total_orders']:>6}  -> {current['total_orders']:<6}  ({pct_change(current['total_orders'], previous['total_orders'])})")
    print(f"  Revenue   : {previous['total_revenue']:>10.2f}  -> {current['total_revenue']:<10.2f}  ({pct_change(current['total_revenue'], previous['total_revenue'])})")
    print(f"  Customers : {previous['unique_customers']:>6}  -> {current['unique_customers']:<6}  ({pct_change(current['unique_customers'], previous['unique_customers'])})")
    print("=" * 70)


def get_interactive_input() -> tuple[str, datetime, datetime]:
    print("E-commerce Order Analytics - Summary Report Generator")
    print("-" * 55)

    report_type = ""
    while report_type not in VALID_TYPES:
        report_type = input("Report type (daily/weekly/monthly): ").strip().lower()
        if report_type not in VALID_TYPES:
            print(f"  Invalid type. Choose one of: {', '.join(sorted(VALID_TYPES))}")

    start = end = None
    while start is None or end is None:
        try:
            start = parse_date(input("Start date (YYYY-MM-DD): "))
            end = parse_date(input("End date   (YYYY-MM-DD): "))
            if end < start:
                print("  End date must be on or after start date. Try again.")
                start = end = None
        except ValueError:
            print("  Invalid date format. Use YYYY-MM-DD.")

    return report_type, start, end


def main():
    parser = argparse.ArgumentParser(description="E-commerce order analytics CLI reporting tool")
    parser.add_argument("--type", choices=sorted(VALID_TYPES), help="Report type: daily/weekly/monthly")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    if args.type and args.start and args.end:
        report_type = args.type
        start = parse_date(args.start)
        end = parse_date(args.end)
    else:
        report_type, start, end = get_interactive_input()

    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run scripts/load_to_sqlite.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    current = fetch_period_summary(conn, start, end)
    prev_start, prev_end = previous_period(start, end)
    previous = fetch_period_summary(conn, prev_start, prev_end)
    conn.close()

    print_report(report_type, start, end, current, prev_start, prev_end, previous)


if __name__ == "__main__":
    main()
