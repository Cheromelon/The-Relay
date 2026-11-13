
import json

for tag in ["config_a", "config_c"]:
    path = f"data/chunks_{tag}.json"

    with open(path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    print(f"\n{tag}")
    print("Unique paper names:")

    names = sorted(set(chunk["paper"] for chunk in chunks))

    for name in names:
        print(repr(name))
