
import asyncio
from retrieval import RetrievalEngine
from groq_client import GroqClient


async def main():

    retriever = RetrievalEngine()
    retriever.load_index()

    client = GroqClient()

    question = (
        "What is the role of self-attention "
        "in the Transformer architecture?"
    )

    retrieved_chunks = retriever.search(
        question,
        top_k=3
    )

    print("\nGenerating answer using Groq streaming...\n")

    def display_piece(piece):
        print(piece, end="", flush=True)

    result = await client.generate_answer(
        question,
        retrieved_chunks,
        on_piece=display_piece
    )

    print("\n\n--- STREAMING METRICS ---")

    print("First token:", result["first_token_ms"], "ms")
    print("Total time:", result["total_ms"], "ms")
    print("Input tokens:", result["tokens_in"])
    print("Output tokens:", result["tokens_out"])
    print("Streaming:", result["streaming"])


if __name__ == "__main__":
    asyncio.run(main())
