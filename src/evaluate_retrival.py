
import json
import time
import numpy as np
import faiss

from pathlib import Path
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CONFIGS = {
    "A": {
        "chunks": "data/chunks_config_a.json",
        "index": "data/faiss_config_a.index",
        "top_k": 3
    },
    "B": {
        "chunks": "data/chunks_config_b.json",
        "index": "data/faiss_config_a.index",
        "top_k": 5
    },
    "C": {
        "chunks": "data/chunks_config_c.json",
        "index": "data/faiss_config_c.index",
        "top_k": 3
    },
    "D": {
        "chunks": "data/chunks_config_c.json",
        "index": "data/faiss_config_c.index",
        "top_k": 5
    }
}


def load_chunks(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_or_load_index(model, chunks, index_path):
    index_path = Path(index_path)

    if index_path.exists():
        print(f"Loading existing index: {index_path}")
        return faiss.read_index(str(index_path))

    print(f"Building index: {index_path}")

    texts = [chunk["text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(index_path))

    return index


def estimate_tokens(text):
    # Approximation only, not an exact tokenizer count.
    return max(1, len(text) // 4)


def evaluate():
    with open(
        "data/evaluation_questions.json",
        "r",
        encoding="utf-8"
    ) as file:
        questions = json.load(file)

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    all_results = []

    for config_name, config in CONFIGS.items():

        print(f"\n========== CONFIG {config_name} ==========")

        chunks = load_chunks(config["chunks"])

        # Configurations A and B use identical chunks.
        index_path = (
            "data/faiss_config_a.index"
            if config_name in ("A", "B")
            else config["index"]
        )

        index = build_or_load_index(model, chunks, index_path)

        for item in questions:

            question = item["question"]
            expected_paper = item["expected_paper"]
            expected_title = item["paper_title"]

            start = time.perf_counter()

            query_embedding = model.encode(
                [question],
                normalize_embeddings=True
            )

            query_embedding = np.asarray(
                query_embedding,
                dtype=np.float32
            )

            scores, indices = index.search(
                query_embedding,
                config["top_k"]
            )

            retrieval_ms = (
                time.perf_counter() - start
            ) * 1000

            retrieved = []

            for score, idx in zip(scores[0], indices[0]):

                if idx < 0:
                    continue

                chunk = chunks[int(idx)]

                retrieved.append({
                    "paper": chunk["paper"],
                    "page": chunk["page"],
                    "score": float(score),
                    "text": chunk["text"]
                })

            retrieved_papers = list({
                result["paper"] for result in retrieved
            })

            # Compare the expected title with actual chunk paper titles.
            expected_paper_found = (
                expected_title in retrieved_papers
            )

            context = "\n".join(
                result["text"] for result in retrieved
            )

            row = {
                "config": config_name,
                "question_id": item["id"],
                "question": question,
                "expected_paper": expected_paper,
                "expected_paper_title": expected_title,
                "top_k": config["top_k"],
                "retrieval_ms": round(retrieval_ms, 2),
                "expected_paper_found": expected_paper_found,
                "retrieved_papers": retrieved_papers,
                "estimated_context_tokens": estimate_tokens(context),
                "retrieved_chunks": retrieved
            }

            all_results.append(row)

            print(
                f"Q{item['id']:02d} | "
                f"Expected paper found: {expected_paper_found} | "
                f"Retrieval: {retrieval_ms:.2f} ms | "
                f"Estimated context tokens: "
                f"{row['estimated_context_tokens']}"
            )

    # Save all 45 retrieval results.
    output_path = Path("data/retrieval_evaluation.json")

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            all_results,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nEvaluation completed.")
    print("Total retrieval runs:", len(all_results))
    print("Saved results to:", output_path)


if __name__ == "__main__":
    evaluate()
