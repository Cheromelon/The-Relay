import json
from pathlib import Path

path = Path("data/real_raw.jsonl")

with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i == 5:
            break

        try:
            record = json.loads(line)
            print(f"\n--- Record {i + 1} ---")
            print("Keys:", list(record.keys()))
            print(json.dumps(record, indent=2)[:2500])
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)