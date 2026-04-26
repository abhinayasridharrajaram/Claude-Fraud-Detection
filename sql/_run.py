"""
_run.py — Execute a SQL file via DuckDB and return a DataFrame.

Usage:
    py sql/_run.py sql/01_schema.sql
    py sql/_run.py sql/01_schema.sql --save outputs/eda/01_schema.parquet
"""

import sys
import os
import duckdb
import pandas as pd

def run_sql(sql_path: str, save_path: str | None = None) -> pd.DataFrame:
    # Always resolve paths relative to the project root (parent of sql/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_dir = os.getcwd()
    os.chdir(project_root)

    try:
        sql = open(sql_path).read()
        con = duckdb.connect()
        df = con.execute(sql).df()
    finally:
        os.chdir(original_dir)

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        if save_path.endswith(".parquet"):
            df.to_parquet(save_path, index=False)
        else:
            df.to_csv(save_path, index=False)
        print(f"Saved to {save_path}")

    return df


if __name__ == "__main__":
    args = sys.argv[1:]
    save = None
    if "--save" in args:
        idx = args.index("--save")
        save = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if not args:
        print("Usage: py sql/_run.py <sql_file> [--save <output_path>]")
        sys.exit(1)

    result = run_sql(args[0], save)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 120)
    print(result.to_string(index=False))
