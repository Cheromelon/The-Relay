
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RESULTS_FILE = ROOT / "results.csv"
ANSWER_FILE = ROOT / "data" / "answer_evaluation.json"
BACKUP_FILE = ROOT / "results_before_answer_eval.csv"

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

# Load existing results
with open(RESULTS_FILE, newline="", encoding="utf-8") as f:
    existing_rows = list(csv.DictReader(f))

existing_ids = {
    row["request_id"] for row in existing_rows
}

# Load the 15 answer-evaluation records
with open(ANSWER_FILE, encoding="utf-8") as f:
    evaluations = json.load(f)

if not isinstance(evaluations, list):
    raise ValueError("Expected answer_evaluation.json to contain a list.")

if len(evaluations) != 15:
    raise ValueError(
        f"Expected 15 answer evaluations, found {len(evaluations)}."
    )

new_rows = []

for item in evaluations:
    question_id = item.get("question_id")

    if question_id is None:
        raise ValueError("An evaluation is missing question_id.")

    request_id = f"qa_{int(question_id):02d}"

    # Avoid duplicate rows if this script is run again.
    if request_id in existing_ids:
        continue

    config = item.get("config", "D")
    chunk_size = item.get("chunk_size", "")
    overlap = item.get("overlap", "")
    top_k = item.get("top_k", "")

    retrieval_setting = (
        f"config_{config}_"
        f"chunk{chunk_size}_"
        f"overlap{overlap}_"
        f"topk{top_k}"
    )

    status = item.get("status", "error")

    if status not in {"ok", "rate_limited", "timeout", "error"}:
        status = "error"

    new_rows.append({
        "request_id": request_id,
        "scenario": "answer_quality_eval",
        "source": "real",
        "start_time": "",
        "first_token_ms": item.get("first_token_ms", ""),
        "total_ms": item.get("total_ms", ""),
        "status": status,
        "retries": 0,
        "tokens_in": item.get("tokens_in", ""),
        "tokens_out": item.get("tokens_out", ""),
        "retrieval_setting": retrieval_setting,
        # Leave blank until manually graded.
        "answer_grade": "",
    })


# Back up the original results only once.
if not BACKUP_FILE.exists():
    shutil.copy2(RESULTS_FILE, BACKUP_FILE)

# Add new records.
all_rows = existing_rows + new_rows

# Write final results.
with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(all_rows)

print("ANSWER EVALUATION MERGED")
print("------------------------")
print("Existing records:", len(existing_rows))
print("New QA records:", len(new_rows))
print("Final records:", len(all_rows))
print("Backup:", BACKUP_FILE)
print("Output:", RESULTS_FILE)

print("\nQA records by status:")
for status in ["ok", "rate_limited", "timeout", "error"]:
    count = sum(row["status"] == status for row in new_rows)
    print(f"{status}: {count}")

print("\nValidation:")
assert all(list(row.keys()) == COLUMNS for row in all_rows)
assert len({row["request_id"] for row in all_rows}) == len(all_rows)

print("Passed.")
