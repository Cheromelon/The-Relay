
import csv
from collections import Counter

path = "results.csv"

with open(path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

columns = list(rows[0].keys())

# Make duplicate IDs unique using their scenario.
counts = Counter(row["request_id"] for row in rows)
seen = {}

for row in rows:
    old_id = row["request_id"]

    if counts[old_id] > 1:
        seen[old_id] = seen.get(old_id, 0) + 1
        scenario = row["scenario"].replace(" ", "_")
        row["request_id"] = (
            f"{old_id}_{scenario}_{seen[old_id]}"
        )

# Validate uniqueness.
ids = [row["request_id"] for row in rows]

assert len(ids) == len(set(ids)), "Duplicate IDs remain!"

with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

print("Duplicate IDs repaired.")
print("Total records:", len(rows))
print("Unique IDs:", len(set(ids)))
print("Columns:", len(columns))
