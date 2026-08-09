"""
Master pipeline runner - executes all phases in order:
    Part 1: generate_data.py     (raw messy CSVs)
    Part 2: clean_data.py        (cleaned CSVs + data quality report)
    Part 3: load_to_sqlite.py    (load cleaned data into SQLite)
    Part 3: sql_analysis.py      (run all 16 SQL queries)
    Part 5: edge_case_tests.py   (edge case validation)

Part 4 (report_cli.py) is interactive/on-demand and is run separately:
    python scripts/report_cli.py

Run:
    python scripts/run_all.py
"""

import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

STEPS = [
    ("Part 1: Data Generation", "generate_data.py"),
    ("Part 2: Data Cleaning", "clean_data.py"),
    ("Part 3: Load to SQLite", "load_to_sqlite.py"),
    ("Part 3: SQL Analysis (16 queries)", "sql_analysis.py"),
    ("Part 5: Edge Case Tests", "edge_case_tests.py"),
]


def main():
    for title, script in STEPS:
        print("\n" + "#" * 78)
        print(f"# {title}")
        print("#" * 78 + "\n")
        try:
            runpy.run_path(str(SCRIPTS_DIR / script), run_name="__main__")
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"\nStep '{title}' exited with code {e.code}. Stopping.")
                sys.exit(e.code)

    print("\n" + "#" * 78)
    print("# Pipeline complete. Run `python scripts/report_cli.py` for the CLI report tool.")
    print("#" * 78)


if __name__ == "__main__":
    main()
