import csv
from pathlib import Path

folder = Path("experiments/raw_results")

for file in folder.glob("*.csv"):
    with open(file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        print(f"\n--- {file.name} ---")
        print("Columns:", reader.fieldnames)
        print("First row:", next(reader, None))

print("\n--- Possible real baseline files ---")
for folder in [Path("experiments"), Path("data")]:
    for file in folder.rglob("*"):
        if file.is_file() and ("real" in file.name.lower() or "baseline" in file.name.lower()):
            print(file)