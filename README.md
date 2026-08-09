# Celebal-Technologies-Ecommerce-Order-Analytics-System

## E-commerce Order Analytics System

### Objective

Design and develop an end-to-end data analytics system to process and analyze e-commerce order data using Python and SQL. Generate realistic datasets with intentional inconsistencies, perform data cleaning and validation using Pandas, and ensure data integrity across multiple tables. Implement complex SQL queries including joins, aggregations, window functions, CTEs, and cohort analysis to derive business insights such as customer segmentation, revenue trends, and retention metrics. Build a command-line reporting tool to generate dynamic summaries and handle critical edge cases to ensure robustness and reliability of the system.

### Status — Phase 1 (Python & SQL, local environment): **Complete**

- [x] Part 1 — Data Generation
- [x] Part 2 — Data Cleaning
- [x] Part 3 — SQL Analysis (16 queries)
- [x] Part 4 — Python + SQL CLI Reporting Tool
- [x] Part 5 — Edge Case Handling

### Repository Structure

```
Celebal-Technologies-Ecommerce-Order-Analytics-System/
├── data/
│   ├── raw/                        # Part 1 output — messy source data
│   │   ├── customers.csv           # 500 rows
│   │   ├── products.csv            # 500 rows
│   │   ├── orders.csv              # 800 rows
│   │   └── order_items.csv         # 1800 rows
│   ├── cleaned/                    # Part 2 output — cleaned/normalized CSVs
│   │   ├── customers.csv
│   │   ├── products.csv
│   │   ├── orders.csv
│   │   └── order_items.csv
│   └── ecommerce.db                # Part 3 — SQLite database loaded from data/cleaned/
├── scripts/
│   ├── generate_data.py            # Part 1
│   ├── clean_data.py               # Part 2
│   ├── load_to_sqlite.py           # Part 3 (load step)
│   ├── sql_analysis.py             # Part 3 (runs all 16 queries, saves results)
│   ├── report_cli.py               # Part 4 — CLI reporting tool
│   ├── edge_case_tests.py          # Part 5 — edge case test functions
│   └── run_all.py                  # Orchestrator — runs Parts 1,2,3,5 end-to-end
├── sql/
│   └── queries.sql                 # All 16 SQL queries (commented, numbered)
├── report/
│   ├── data_quality_report.md      # Part 2 — issues found during cleaning
│   └── query_results/              # Part 3 — CSV output of all 16 queries
│       ├── query_01.csv ... query_16.csv
├── screenshots/                    # Rendered terminal output from each stage
│   ├── 01_generate_data.png
│   ├── 02_clean_data.png
│   ├── 03_sql_analysis.png
│   ├── 04_report_cli.png
│   └── 05_edge_case_tests.png
├── .gitignore
└── README.md
```

### How to Run

```bash
pip install pandas faker

# Run everything end-to-end (Parts 1, 2, 3, 5)
python scripts/run_all.py

# Part 4 CLI tool (interactive, or pass args non-interactively)
python scripts/report_cli.py
python scripts/report_cli.py --type monthly --start 2024-01-01 --end 2024-01-31
```

---

## Part 1 — Data Generation

`scripts/generate_data.py` uses **Faker** to generate 4 relational CSVs with the assignment's required intentional data-quality issues:

| File | Rows | Intentional Issues |
|---|---|---|
| `customers.csv` | 500 | ~2% of emails invalid (missing `@` or domain) |
| `products.csv` | 500 | ~15% of product names have extra spaces / inconsistent casing |
| `orders.csv` | 800 | ~5% NULL/empty `customer_id`; ~6% `order_date` in wrong format (`DD-MM-YYYY`) |
| `order_items.csv` | 1800 | ~3% negative `quantity` (returns); 8 rows reference a non-existent `order_id`; a few rows with `discount_percent` > 100 |

**Referential integrity by design:** `order_id` values in `order_items.csv` are sampled from real `orders.csv` order IDs — except for a deliberate ~1% injection of "ghost" order IDs (`O900001`–`O900008`), giving Part 2's `check_referential_integrity()` real broken rows to find while keeping the dataset otherwise consistent.

---

## Part 2 — Data Cleaning

`scripts/clean_data.py` implements:

- **`clean_orders()`** — parses `order_date` (handles both the correct `YYYY-MM-DD HH:MM:SS` format and the malformed `DD-MM-YYYY` format), and handles missing `customer_id` by setting it to `'UNKNOWN'` and flagging the row with `is_guest_order=1` (rather than dropping the order).
- **`clean_products()`** — trims whitespace and normalizes `product_name` to Title Case; also normalizes `category`/`subcategory`.
- **`clean_order_items()`** — flags each row as `PURCHASE`, `RETURN` (negative quantity), or `ZERO_QTY`; caps `discount_percent` to the valid `[0, 100]` range; computes `revenue = quantity × unit_price × (1 − discount_percent/100)`.
- **`validate_emails()`** — returns the list of `customer_id`s with a malformed email.
- **`check_referential_integrity()`** — finds `order_items` rows whose `order_id` doesn't exist in `orders`; these are excluded from the cleaned output and logged in the audit report.

**Output:** cleaned CSVs in `data/cleaned/`, plus a full issue breakdown in `report/data_quality_report.md` (sample from an actual run):

```
- Rows with wrong date format fixed: 39
- Rows with NULL customer_id handled: 40
- Product names normalized: 66
- Negative quantity rows (RETURN): 61
- discount_percent > 100 capped: 9
- Invalid emails found: 7
- order_items referencing a non-existent order_id: 16 (8 distinct orphan order_ids)
```

---

## Part 3 — SQL Analysis (16 queries)

Cleaned data is loaded into `data/ecommerce.db` (SQLite) by `scripts/load_to_sqlite.py`. All 16 queries live in `sql/queries.sql` and are executed/saved by `scripts/sql_analysis.py`.

**Basic:** (1) total revenue per category · (2) top 10 customers by order value · (3) month-wise order count, last 12 months

**Intermediate:** (4) customers with no delivered order · (5) products with more returns than purchases · (6) return rate per category

**Advanced (Window Functions / CTEs / Subqueries):**
(7) running total of revenue per region (window function) · (8) `DENSE_RANK()` of products by revenue per category, ties share a rank · (9) `LAG()` days-between-orders per customer + "At Risk" flag (avg gap > 30 days) · (10) multi-level CTE: monthly revenue per customer → High/Medium/Low categorization → monthly counts · (11) `NTILE(4)` customer quartiles (Platinum/Gold/Silver/Bronze) · (12) year-over-year monthly revenue comparison, handling missing prior-year data · (13) `FIRST_VALUE`/`LAST_VALUE` — first vs. most-recent purchased category, `category_shift` flag · (14) cumulative revenue distribution / % from top customers · (15) cohort analysis by registration month with month 0–3 retention rates · (16) self-join (via `ROW_NUMBER()`) to find each customer's next order

Each query's full result set is saved to `report/query_results/query_01.csv` … `query_16.csv`.

---

## Part 4 — Python + SQL CLI Reporting Tool

`scripts/report_cli.py` — **stdlib only** (`sqlite3`, `argparse`, `datetime`), no pandas/third-party packages.

- Prompts for report type (`daily`/`weekly`/`monthly`) and a date range (or accepts `--type/--start/--end` for non-interactive use).
- Connects to `data/ecommerce.db` and reports: total orders, total revenue, unique customers, top 3 products by revenue.
- Compares the period against the immediately preceding period of equal length, showing `%` change for orders, revenue, and customers.

Example:
```
======================================================================
MONTHLY SUMMARY REPORT
Period: 2024-01-01 to 2024-01-31
======================================================================
Total Orders       : 38
Total Revenue      : 2807407.47
Unique Customers   : 36

Top 3 Products (by revenue):
  1. Feel Storage President                 140723.17
  2. Describe Men Run                       102022.11
  3. Perform Academic Mother                101097.30

Comparison with previous period (2023-12-01 to 2023-12-31):
  Orders    :     42  -> 38      (-9.52%)
  Revenue   : 2961217.78  -> 2807407.47  (-5.19%)
  Customers :     39  -> 36      (-7.69%)
======================================================================
```

---

## Part 5 — Edge Case Handling

`scripts/edge_case_tests.py` — 4 test functions (run with `python scripts/edge_case_tests.py`, or auto-discovered by `pytest`):

1. **`order_items` references a non-existent `order_id`** → caught by `check_referential_integrity()`; the row is excluded from cleaned output and logged for audit.
2. **`discount_percent > 100`** → capped to 100 during cleaning (logged in the data-quality report); revenue floors at 0 instead of going negative.
3. **`quantity == 0`** → flagged as `transaction_type='ZERO_QTY'` (neither purchase nor return), contributes 0 revenue, so it can't silently skew return-rate calculations.
4. **`order_date` in the future** → parses successfully rather than crashing/being dropped; flagged as a candidate for manual review downstream (`order_date > today()`).

All 4 tests pass on every run of `scripts/run_all.py`.

---

## Key Insights

- **Data quality issues compound across a pipeline** — a single malformed date or orphan foreign key, left unhandled, breaks downstream aggregations (e.g., a `DD-MM-YYYY` date silently misparsed would corrupt every date-based query in Part 3).
- **Cleaning decisions should be explicit and logged, not silent** — e.g. capping `discount_percent` at 100 vs. dropping the row are both defensible, but the choice needs to be visible in `data_quality_report.md` for anyone auditing the pipeline.
- **Signed quantity is a clean way to model returns** — treating `quantity < 0` as a return lets the revenue formula `quantity × unit_price × (1 − discount/100)` naturally net out returns without special-casing every aggregate query.
- **Window functions dramatically simplify "compare to previous/first/last" logic** — `LAG`, `FIRST_VALUE`/`LAST_VALUE`, and running-total `SUM() OVER (...)` avoid the self-joins and correlated subqueries that the same logic would otherwise require.
- **Referential integrity must be checked, not assumed** — even a carefully generated synthetic dataset can (and, here, deliberately does) have `order_items` rows pointing at orders that don't exist; production pipelines need an explicit check like `check_referential_integrity()`, not just a `JOIN` that silently drops orphaned rows.
#
