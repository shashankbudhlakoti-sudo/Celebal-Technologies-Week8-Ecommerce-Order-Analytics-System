# Data Quality Report

_Generated: 2026-08-09 04:04:25_

## orders.csv (clean_orders)
- Total rows processed: 800
- Rows with wrong date format fixed (DD-MM-YYYY -> YYYY-MM-DD HH:MM:SS): 39
- Rows with NULL/empty customer_id handled (set to 'UNKNOWN', flagged is_guest_order=1): 40

## products.csv (clean_products)
- Total rows processed: 500
- Product names normalized (trimmed + Title Case): 66

## order_items.csv (clean_order_items)
- Total rows processed: 1800
- Negative quantity rows (flagged as RETURN): 61
- Zero quantity rows (flagged as ZERO_QTY): 0
- discount_percent > 100 capped to 100: 9

## customers.csv (validate_emails)
- Total customers: 500
- Invalid emails found: 7
- Sample invalid-email customer_ids: ['C00061', 'C00178', 'C00179', 'C00240', 'C00281', 'C00288', 'C00387']

## Referential Integrity (check_referential_integrity)
- order_items rows referencing a non-existent order_id: 16
- Orphan order_ids: ['O900001', 'O900002', 'O900003', 'O900004', 'O900005', 'O900006', 'O900007', 'O900008']
- These rows were EXCLUDED from data/cleaned/order_items.csv (kept only here for audit).

## Output
- Cleaned CSVs written to `data/cleaned/`
- This report: `report/data_quality_report.md`