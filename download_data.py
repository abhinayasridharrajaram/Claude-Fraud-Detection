"""
Helper to verify data/creditcard.csv is in place.

The dataset requires a free Kaggle account to download — we don't automate that
login. Instead, this script just checks whether the CSV is where it should be
and prints the right instructions if not.
"""

from pathlib import Path
import sys

CSV = Path("data/creditcard.csv")
EXPECTED_ROWS = 284_807

def main() -> int:
    if not CSV.exists():
        print("[ ] data/creditcard.csv not found.")
        print()
        print("Download it from:")
        print("  https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        print("Unzip and place `creditcard.csv` at `data/creditcard.csv`.")
        return 1

    try:
        import duckdb
    except ImportError:
        print("[ ] duckdb not installed. Run:")
        print("    python -m pip install --user duckdb pandas scikit-learn umap-learn matplotlib pyarrow")
        return 1

    rows = duckdb.connect().execute(
        f"SELECT COUNT(*) FROM '{CSV.as_posix()}'"
    ).fetchone()[0]

    if rows != EXPECTED_ROWS:
        print(f"[!] Row count is {rows:,}, expected {EXPECTED_ROWS:,}.")
        print("    The file may be truncated. Redownload from Kaggle.")
        return 1

    print(f"[x] data/creditcard.csv OK — {rows:,} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())