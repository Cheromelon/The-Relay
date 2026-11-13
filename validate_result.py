
import csv
from collections import Counter

path = "results.csv"

required_columns = [
    "request_id",
    "scenario",
    "source",
    "start_time",
    "first_token_ms",
    "total_ms",
    "status",
    "retries",
    "tokens_in",
    "tokens_out",
    "retrieval_setting",
    "answer_grade",
]

with open(path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = reader.fieldnames

print("========== CSV AUDIT ==========")

# 1. Schema
print("\n1. Schema")
print("Correct columns:", columns == required_columns)
print("Column count:", len(columns))

# 2. Record count and IDs
ids = [row["request_id"] for row in rows]
print("\n2. Records")
print("Total records:", len(rows))
print("Unique IDs:", len(set(ids)))
print("Duplicate IDs:", len(ids) - len(set(ids)))

# 3. Sources and scenarios
print("\n3. Sources")
for key, value in Counter(row["source"] for row in rows).items():
    print(key, ":", value)

print("\n4. Scenarios")
for key, value in Counter(row["scenario"] for row in rows).items():
    print(key, ":", value)

# 4. Status values
print("\n5. Status")
for key, value in Counter(row["status"] for row in rows).items():
    print(key, ":", value)

allowed_status = {"ok", "rate_limited", "timeout", "error"}
invalid_status = [
    row["request_id"] for row in rows
    if row["status"] not in allowed_status
]
print("Invalid statuses:", invalid_status)

# 5. Answer grades
print("\n6. Answer grades")
for key, value in Counter(
    row["answer_grade"] or "blank"
    for row in rows
).items():
    print(key, ":", value)

# 6. Missing fields
print("\n7. Missing values")
for field in required_columns:
    missing = sum(not row[field].strip() for row in rows)
    print(f"{field}: {missing}")

# 7. Final checks
checks = {
    "140 records": len(rows) == 140,
    "Unique IDs": len(ids) == len(set(ids)),
    "Correct schema": columns == required_columns,
    "Valid statuses": not invalid_status,
}

print("\n========== FINAL CHECKS ==========")
for name, passed in checks.items():
    print(("PASS" if passed else "CHECK"), "-", name)
