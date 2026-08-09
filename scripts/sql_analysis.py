"""
PHASE 1 - Part 3: Run all SQL analysis queries
================================================
Parses sql/queries.sql (16 numbered queries), runs each against
data/ecommerce.db, prints a preview, and saves the full result set to
report/query_results/query_XX.csv

Run:
    python scripts/sql_analysis.py
"""

import os
import re
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "data", "ecommerce.db")
SQL_PATH = os.path.join(BASE_DIR, "sql", "queries.sql")
RESULTS_DIR = os.path.join(BASE_DIR, "report", "query_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def parse_queries(sql_text: str) -> list[tuple[int, str, str]]:
    """
    Splits queries.sql into (number, title, sql) tuples based on the
    '-- N. Title' comment markers used in the file.
    """
    pattern = re.compile(r"^-- (\d+)\.\s*(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(sql_text))
    queries = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql_text)
        block = sql_text[start:end]
        # strip leading comment lines, keep the actual SQL
        sql_lines = [ln for ln in block.split("\n")]
        sql = "\n".join(sql_lines).strip()
        queries.append((num, title, sql))
    return queries


def run():
    with open(SQL_PATH) as f:
        sql_text = f.read()

    queries = parse_queries(sql_text)
    conn = sqlite3.connect(DB_PATH)

    print(f"Running {len(queries)} SQL queries against {DB_PATH}\n")

    for num, title, sql in queries:
        print("=" * 80)
        print(f"Query {num}: {title}")
        print("=" * 80)
        try:
            df = pd.read_sql_query(sql, conn)
        except Exception as e:
            print(f"ERROR running query {num}: {e}\n")
            continue

        print(df.head(10).to_string(index=False))
        if len(df) > 10:
            print(f"... ({len(df)} total rows)")

        out_path = os.path.join(RESULTS_DIR, f"query_{num:02d}.csv")
        df.to_csv(out_path, index=False)
        print(f"-> saved {len(df)} rows to {os.path.relpath(out_path, BASE_DIR)}\n")

    conn.close()
    print("All queries executed.")


if __name__ == "__main__":
    run()
