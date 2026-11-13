
import json
from pathlib import Path

for tag in ["config_a", "config_b", "config_c"]:
    path = Path(f"data/chunks_{tag}.json")

    with open(path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    lengths = [len(chunk["text"]) for chunk in chunks]

    print(f"\n{tag}")
    print("-" * 35)
    print("Total chunks:", len(chunks))
    print("Average characters:", round(sum(lengths) / len(lengths), 2))
    print("Shortest chunk:", min(lengths))
    print("Longest chunk:", max(lengths))
