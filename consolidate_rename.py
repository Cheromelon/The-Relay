
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "experiments" / "raw_results"
REAL_FILE = ROOT / "data" / "real_raw.jsonl"
OUTPUT = ROOT / "results.csv"

COLUMNS = [
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

rows = []


def add_row(record, prefix, limiter_only=False):
    """Convert a raw record into the required results.csv schema."""

    raw_status = record.get("raw_status") or record.get("status", "")

    # Convert internal statuses to the assignment's allowed statuses.
    if raw_status == "queue_full":
        status = "error"
    elif str(raw_status).startswith("rate_limited"):
        status = "rate_limited"
    else:
        status = raw_status

    if status not in {"ok", "rate_limited", "timeout", "error"}:
        status = "error"

    # Limiter-only tests do not invoke the model.
    # Therefore, their model latency and actual token usage are unknown.
    if limiter_only:
        first_token_ms = ""
        total_ms = ""
        tokens_in = ""
        tokens_out = ""
    else:
        first_token_ms = record.get("first_token_ms", "")
        total_ms = record.get("total_ms", "")
        tokens_in = record.get("tokens_in", "")
        tokens_out = record.get("tokens_out", "")

    rows.append({
        "request_id": f"{prefix}_{record.get('request_id', len(rows) + 1)}",
        "scenario": record.get("scenario", ""),
        "source": record.get("source", ""),
        "start_time": record.get("start_time", ""),
        "first_token_ms": first_token_ms,
        "total_ms": total_ms,
        "status": status,
        "retries": record.get("retries", 0),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "retrieval_setting": record.get("retrieval_setting", ""),
        "answer_grade": record.get("answer_grade", ""),
    })


# 1. Real Groq baseline (JSONL)
with open(REAL_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            record = json.loads(line)
            add_row(record, "real")


# 2. Stand-in request-level experiments
for filename, prefix in [
    ("steady.csv", "steady"),
    ("burst.csv", "burst"),
    ("overload.csv", "overload"),
]:
    path = RAW / filename

    with open(path, "r", newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            add_row(record, prefix)


# 3. Limiter-only scenarios
limit_file = RAW / "limit_scenarios.csv"

with open(limit_file, "r", newline="", encoding="utf-8") as f:
    for record in csv.DictReader(f):
        add_row(record, "limit", limiter_only=True)


# 4. Write final CSV
with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)


# 5. Validation and summary
print("CONSOLIDATION COMPLETE")
print("----------------------")
print("Output:", OUTPUT)
print("Total records:", len(rows))
print("Columns:", len(COLUMNS))

print("\nRecords by scenario:")
for scenario in sorted(set(row["scenario"] for row in rows)):
    count = sum(row["scenario"] == scenario for row in rows)
    print(f"{scenario}: {count}")

print("\nRecords by status:")
for status in ["ok", "rate_limited", "timeout", "error"]:
    count = sum(row["status"] == status for row in rows)
    print(f"{status}: {count}")

assert all(list(row.keys()) == COLUMNS for row in rows)
assert all(row["source"] in {"real", "stand-in"} for row in rows)

print("\nValidation passed.")
