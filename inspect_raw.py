
import csv
from pathlib import Path

folder = Path("experiments/raw_results")

for path in sorted(folder.glob("*.csv")):
    print("\nFILE:", path)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print("Columns:", reader.fieldnames)
    print("Rows:", len(rows))

    candidates = []
    for row in rows:
        try:
            value = float(row.get("total_ms") or row.get("user_elapsed_ms") or 0)
            candidates.append((value, row))
        except (ValueError, TypeError):
            pass

    if candidates:
        print("Slowest row:")
        for key, value in sorted(
            candidates, key=lambda x: x[0], reverse=True
        )[0][1].items():
            print(f"  {key}: {value}")
