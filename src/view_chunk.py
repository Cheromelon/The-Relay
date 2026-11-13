
import json

with open("data/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

for i, chunk in enumerate(chunks):
    print("\n" + "=" * 100)
    print(f"CHUNK NUMBER: {i + 1}")
    print(f"PAPER: {chunk['paper']}")
    print(f"PAGE: {chunk['page']}")
    print(f"CHUNK INDEX: {chunk['chunk_index']}")
    print("-" * 100)
    print(chunk["text"])
    print("=" * 100)
    
    input("\nPress Enter to view the next chunk...")
