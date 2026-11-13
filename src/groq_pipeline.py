
import asyncio

from retrieval import RetrievalEngine
from groq_client import GroqClient


async def main():
    # 1. Load the retrieval engine
    retriever = RetrievalEngine()
    retriever.load_index()

    # 2. Initialize Groq
    groq = GroqClient()

    # 3. Get the user's question
    question = input("\nEnter your question: ")

    # 4. Retrieve the top 3 relevant passages
    retrieved_chunks = retriever.search(question, top_k=3)

    print("\n--- Retrieved Passages ---")

    for chunk in retrieved_chunks:
        print(f"\nPaper: {chunk['paper']}")
        print(f"Page: {chunk['page']}")
        print(f"Similarity: {chunk['similarity_score']:.4f}")
        print(f"Text: {chunk['text'][:300]}...")

    # 5. Generate an answer using Groq
    result = await groq.generate_answer(question, retrieved_chunks)

    print("\n--- Generated Answer ---")
    print(result["answer"])

    print("\n--- Token Usage ---")
    print("Model:", result["model"])
    print("Input tokens:", result["tokens_in"])
    print("Output tokens:", result["tokens_out"])


if __name__ == "__main__":
    asyncio.run(main())
