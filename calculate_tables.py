
import csv
import math
from collections import Counter
from pathlib import Path

with open("results.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def numbers(records, field):
    return [
        float(r[field]) for r in records
        if r[field].strip()
    ]

def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * p
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (pos - low)

def show_stats(records, label):
    first = numbers(records, "first_token_ms")
    total = numbers(records, "total_ms")
    print(f"\n{label} (n={len(records)})")
    for name, values in [("First token", first), ("Total", total)]:
        if values:
            print(
                name,
                "p50", round(percentile(values, .50), 1),
                "p95", round(percentile(values, .95), 1),
                "p99", round(percentile(values, .99), 1),
                "n measured", len(values)
            )
        else:
            print(name, "not measured")

print("========== TABLE 2a: LATENCY ==========")

for scenario in ["steady", "burst", "sustained_overload"]:
    selected = [
        r for r in rows
        if r["scenario"] == scenario and r["status"] == "ok"
    ]
    show_stats(selected, scenario)

print("\n========== TABLE 2b: OUTCOMES ==========")

for scenario in [
    "steady",
    "burst",
    "sustained_overload",
    "per_minute_limit_halved",
    "daily_request_budget_exhausted",
    "daily_token_budget_exhausted",
]:
    selected = [r for r in rows if r["scenario"] == scenario]
    if not selected:
        continue

    counts = Counter(r["status"] for r in selected)
    n = len(selected)

    print(f"\n{scenario}: {n} records")
    print("Status counts:", dict(counts))
    print("Status percentages:", {
        k: round(v / n * 100, 1) for k, v in counts.items()
    })

    retries = [int(r["retries"] or 0) for r in selected]
    print("Average retries:", round(sum(retries) / n, 2))

print("\n========== TABLE 3: ANSWER QUALITY ==========")

qa = [r for r in rows if r["scenario"] == "answer_quality_eval"]
grades = Counter(r["answer_grade"] for r in qa)

print("Questions:", len(qa))
print("Grades:", dict(grades))
print("Correct and cited %:", round(grades["correct"] / len(qa) * 100, 1))

token_totals = [
    float(r["tokens_in"]) + float(r["tokens_out"])
    for r in qa if r["tokens_in"].strip() and r["tokens_out"].strip()
]

if token_totals:
    print("Average tokens per answer:", round(sum(token_totals) / len(token_totals), 1))

show_stats(qa, "Config D answer evaluation")

print("\n========== DATA QUALITY ==========")
print("Total records:", len(rows))
print("Unique IDs:", len({r["request_id"] for r in rows}))
print("Blank answer grades in QA:", sum(not r["answer_grade"] for r in qa))
print("Completed.")
