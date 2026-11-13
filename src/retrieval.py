
import json
import numpy as np
import faiss

from pathlib import Path
from sentence_transformers import SentenceTransformer


# Configuration
CHUNKS_PATH = Path("data/chunks.json")
INDEX_PATH = Path("data/faiss.index")
EMBEDDINGS_PATH = Path("data/embeddings.npy")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class RetrievalEngine:

    def __init__(self):
        print("Loading embedding model...")

        self.model = SentenceTransformer(MODEL_NAME)
        self.chunks = None
        self.index = None

    def build_index(self):

        print("Loading chunks...")

        with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
            self.chunks = json.load(file)

        texts = [chunk["text"] for chunk in self.chunks]

        print(f"Generating embeddings for {len(texts)} chunks...")

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True
        )

        embeddings = np.asarray(embeddings, dtype=np.float32)

        # Create FAISS index
        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)

        # Add all embeddings to the index
        self.index.add(embeddings)

        # Save index and embeddings
        faiss.write_index(self.index, str(INDEX_PATH))
        np.save(EMBEDDINGS_PATH, embeddings)

        print("\nIndex created successfully!")
        print("Embedding shape:", embeddings.shape)
        print("FAISS index size:", self.index.ntotal)

    def load_index(self):

        with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
            self.chunks = json.load(file)

        self.index = faiss.read_index(str(INDEX_PATH))

        print("Existing FAISS index loaded!")

    def search(self, query, top_k=3):

        if self.index is None:
            raise RuntimeError("Build or load the index first.")

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32
        )

        scores, indices = self.index.search(query_embedding, top_k)

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx < 0:
                continue

            chunk = self.chunks[int(idx)]

            results.append({
                "paper": chunk["paper"],
                "page": chunk["page"],
                "text": chunk["text"],
                "similarity_score": float(score)
            })

        return results


if __name__ == "__main__":

    engine = RetrievalEngine()

    engine.build_index()

    while True:

        query = input("\nEnter your question (or 'exit'): ")

        if query.lower() == "exit":
            break

        results = engine.search(query, top_k=3)

        print("\nRETRIEVED PASSAGES")
        print("=" * 80)

        for i, result in enumerate(results):

            print(f"\nResult {i + 1}")
            print("Paper:", result["paper"])
            print("Page:", result["page"])
            print("Similarity:", round(result["similarity_score"], 4))
            print("Text:", result["text"])
            print("-" * 80)
