
import json

with open(
    "data/retrieval_evaluation.json",
    "r",
    encoding="utf-8"
) as file:
    results = json.load(file)

for result in results:
    if result["question_id"] == 5 and result["config"] == "C":
        print("Question:", result["question"])
        print("Expected paper:", result["expected_paper_title"])
        print("Retrieved papers:", result["retrieved_papers"])

        print("\nRetrieved passages:")
        for i, chunk in enumerate(result["retrieved_chunks"], 1):
            print(f"\nPassage {i}")
            print("Paper:", chunk["paper"])
            print("Page:", chunk["page"])
            print("Similarity:", round(chunk["score"], 4))
            print("Text:", chunk["text"][:700])
