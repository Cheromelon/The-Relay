
import asyncio
import json
import time
import re
from pathlib import Path

import faiss
from groq import RateLimitError

from retrieval import RetrievalEngine
from groq_client import GroqClient


# File paths
QUESTIONS_PATH = Path("data/evaluation_questions.json")
OUTPUT_PATH = Path("data/answer_evaluation_q8_q15.json")

# Configuration D
CHUNK_SIZE = 600
OVERLAP = 100
TOP_K = 5

# Evaluate only these question IDs
SELECTED_QUESTION_IDS = {8, 15}

MAX_RETRIES = 3
REQUEST_PAUSE_SECONDS = 10


def save_results(results):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def get_retry_wait(error, attempt):
    message = str(error)

    match = re.search(
        r"try again in ([0-9.]+)s",
        message,
        re.IGNORECASE
    )

    if match:
        return float(match.group(1)) + 2

    return 10 * (2 ** attempt)


async def generate_with_retry(groq_client, question, retrieved_chunks):

    for attempt in range(MAX_RETRIES + 1):

        try:
            return await groq_client.generate_answer(
                question,
                retrieved_chunks
            )

        except RateLimitError as error:

            if attempt == MAX_RETRIES:
                print("Rate limit persisted. Giving up on this question.")

                return {
                    "status": "rate_limited",
                    "answer": "",
                    "tokens_in": None,
                    "tokens_out": None,
                    "model": None,
                    "first_token_ms": None,
                    "total_ms": None,
                    "streaming": True
                }

            wait_seconds = get_retry_wait(error, attempt)

            print(f"Groq rate limit hit: {error}")
            print(
                f"Retry {attempt + 1}/{MAX_RETRIES} "
                f"after {wait_seconds:.1f} seconds..."
            )

            await asyncio.sleep(wait_seconds)

        except Exception as error:

            print("Request failed:", repr(error))

            return {
                "status": "error",
                "answer": "",
                "tokens_in": None,
                "tokens_out": None,
                "model": None,
                "first_token_ms": None,
                "total_ms": None,
                "streaming": True
            }


async def evaluate():

    # Load all evaluation questions.
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
        all_questions = json.load(file)

    # Select only Q8 and Q15.
    questions = [
        item for item in all_questions
        if item["id"] in SELECTED_QUESTION_IDS
    ]

    if len(questions) != len(SELECTED_QUESTION_IDS):
        raise ValueError(
            "Could not find both Q8 and Q15 in evaluation_questions.json"
        )

    print("Selected questions:", [item["id"] for item in questions])

    print("\nLoading retrieval engine...")

    retriever = RetrievalEngine()

    with open(
        "data/chunks_config_c.json",
        "r",
        encoding="utf-8"
    ) as file:
        retriever.chunks = json.load(file)

    retriever.index = faiss.read_index(
        "data/faiss_config_c.index"
    )

    groq_client = GroqClient()

    all_results = []

    for item in questions:

        question = item["question"]

        print("\n" + "=" * 70)
        print(f"Question {item['id']}: {question}")

        # Retrieve passages using Configuration D.
        retrieval_start = time.perf_counter()

        retrieved_chunks = retriever.search(
            question,
            top_k=TOP_K
        )

        retrieval_ms = (
            time.perf_counter() - retrieval_start
        ) * 1000

        print(f"Retrieved {len(retrieved_chunks)} passages")
        print(f"Retrieval time: {retrieval_ms:.2f} ms")

        # Generate answer with retry handling.
        result = await generate_with_retry(
            groq_client,
            question,
            retrieved_chunks
        )

        print("\nAnswer:")
        print(result["answer"] or "[No answer generated]")

        print("\nPerformance:")
        print("Status:", result["status"])
        print("First token:", result["first_token_ms"], "ms")
        print("Total time:", result["total_ms"], "ms")
        print("Input tokens:", result["tokens_in"])
        print("Output tokens:", result["tokens_out"])

        row = {
            "question_id": item["id"],
            "question": question,
            "expected_paper": item["expected_paper"],
            "config": "D",
            "chunk_size": CHUNK_SIZE,
            "overlap": OVERLAP,
            "top_k": TOP_K,
            "retrieval_ms": round(retrieval_ms, 2),
            "answer": result["answer"],
            "status": result["status"],
            "first_token_ms": result["first_token_ms"],
            "total_ms": result["total_ms"],
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
            "model": result["model"],
            "retrieved_passages": [
                {
                    "paper": chunk["paper"],
                    "page": chunk["page"],
                    "text": chunk["text"]
                }
                for chunk in retrieved_chunks
            ],
            "answer_grade": "pending_manual_review"
        }

        all_results.append(row)

        # Save after each question.
        save_results(all_results)

        if result["status"] == "ok":
            await asyncio.sleep(REQUEST_PAUSE_SECONDS)

    print("\n" + "=" * 70)
    print("Evaluation completed.")
    print("Questions processed:", len(all_results))

    successful = sum(
        row["status"] == "ok"
        for row in all_results
    )

    print("Successful answers:", successful)
    print("Unsuccessful answers:", len(all_results) - successful)
    print("Saved results to:", OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(evaluate())
