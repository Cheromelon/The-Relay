
import csv
import shutil
from pathlib import Path
from collections import Counter

path = Path("results.csv")
backup = Path("results_before_grading.csv")

grades = {
    1: "wrong",
    2: "correct",
    3: "correct",
    4: "correct",
    5: "wrong",
    6: "wrong",
    7: "wrong",
    8: "correct",
    9: "wrong",
    10: "refused_wrongly",
    11: "wrong",
    12: "correct",
    13: "wrong",
    14: "wrong",
    15: "wrong",
}

with path.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
    columns = list(rows[0].keys())

if not backup.exists():
    shutil.copy2(path, backup)

updated = 0

for row in rows:
    if row["scenario"] == "answer_quality_eval":
        qid = int(row["request_id"].split("_")[-1])
        row["answer_grade"] = grades[qid]
        updated += 1

assert updated == 15

with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

qa_rows = [r for r in rows if r["scenario"] == "answer_quality_eval"]
counts = Counter(r["answer_grade"] for r in qa_rows)

print("Updated QA rows:", updated)
print("Grade distribution:")
for grade in [
    "correct", "wrong", "refused_correctly", "refused_wrongly"
]:
    print(f"{grade}: {counts[grade]}")

print("Correct and cited:", f"{counts['correct'] / 15 * 100:.1f}%")
print("Wrong:", f"{counts['wrong'] / 15 * 100:.1f}%")
print("Correctly refused:", f"{counts['refused_correctly'] / 15 * 100:.1f}%")
print("Wrongly refused:", f"{counts['refused_wrongly'] / 15 * 100:.1f}%")
print("Backup:", backup)
