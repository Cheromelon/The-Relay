
import csv
from collections import defaultdict

with open("results.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

summary = defaultdict(lambda: defaultdict(int))

for row in rows:
    summary[row["scenario"]][row["status"]] += 1

print("STATUS BREAKDOWN BY SCENARIO")
print("=" * 55)

for scenario, statuses in sorted(summary.items()):
    print(f"\n{scenario}")
    for status, count in statuses.items():
        print(f"  {status}: {count}")

print("\nERROR RECORDS")
print("=" * 55)

for row in rows:
    if row["status"] == "error":
        print(
            f"ID={row['request_id']} | "
            f"Scenario={row['scenario']} | "
            f"Source={row['source']} | "
            f"Latency={row['total_ms']} ms"
        )
