
import os
import csv
import json
import time
import uuid
import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv
from groq import AsyncGroq, RateLimitError, APITimeoutError, APIStatusError

from retrieval import RetrievalEngine

load_dotenv()

MODEL = os.getenv("GROQ_MODEL")
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

if not MODEL:
    raise ValueError("GROQ_MODEL is missing from .env")

client = AsyncGroq(
    api_key=API_KEY,
    timeout=30.0,
    max_retries=0
)

retriever = RetrievalEngine()
retriever.load_index()

QUESTIONS = [
    "What is the role of self-attention in the Transformer architecture?",
    "How does the Transformer encoder process input sequences?",
    "What is the purpose of multi-head attention?",
    "How does Moshi support real-time dialogue?",
    "What is the main idea behind dynamic chunking?"
]

CSV_FILE = "data/results.csv"
RAW_FILE = "data/real_raw.jsonl"

COLUMNS = [
    "request_id", "scenario", "source", "start_time",
    "first_token_ms", "total_ms", "status", "retries",
    "tokens_in", "tokens_out", "retrieval_setting", "answer_grade"
]


async def benchmark_one(question, request_number):
    request_id = str(uuid.uuid4())

    start_time = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()

    finish_reason = None
    first_token_ms = None
    tokens_in = 0
    tokens_out = 0

    answer = ""
    status = "ok"
    error = None
    response_headers = {}

    try:
        # 1. Retrieve relevant passages
        chunks = retriever.search(question, top_k=3)

        context = ""

        for chunk in chunks:
            context += (
                f"\nPaper: {chunk['paper']}"
                f"\nPage: {chunk['page']}"
                f"\nText: {chunk['text']}\n"
            )

        # 2. Send streaming request to Groq
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only using the supplied paper passages. "
                        "Cite paper names and page numbers. "
                        "If the passages do not support an answer, refuse."
                    )
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nPassages:\n{context}"
                }
            ],
            temperature=0.1,
            max_completion_tokens=300,
            stream=True,
        )

        # 3. Process streamed chunks
        async for chunk in stream:

            if chunk.choices:
                choice = chunk.choices[0]

                # Capture the reason generation stopped
                if choice.finish_reason is not None:
                    finish_reason = choice.finish_reason

                text = choice.delta.content

                if text:
                    if first_token_ms is None:
                        first_token_ms = (
                            time.perf_counter() - start
                        ) * 1000

                    answer += text

            # 4. Capture token usage from final streaming chunk
            usage = getattr(
                getattr(chunk, "x_groq", None),
                "usage",
                None
            )

            if usage is None:
                usage = getattr(chunk, "usage", None)

            if usage:
                tokens_in = usage.prompt_tokens or 0
                tokens_out = usage.completion_tokens or 0

        # 5. Capture response headers
        response = getattr(stream, "response", None)

        if response is not None:
            response_headers = dict(response.headers)

    except RateLimitError as e:
        status = "rate_limited"
        error = str(e)

    except APITimeoutError as e:
        status = "timeout"
        error = str(e)

    except APIStatusError as e:
        status = "error"
        error = str(e)

    except Exception as e:
        status = "error"
        error = repr(e)

    # 6. Calculate total latency
    total_ms = (time.perf_counter() - start) * 1000

    # 7. Create structured CSV record
    row = {
        "request_id": request_id,
        "scenario": "real_finish_check",
        "source": "real",
        "start_time": start_time,
        "first_token_ms": (
            round(first_token_ms, 2)
            if first_token_ms is not None else ""
        ),
        "total_ms": round(total_ms, 2),
        "status": status,
        "retries": 0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "retrieval_setting": "top3",
        "answer_grade": ""
    }

    # 8. Append result to CSV
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)

        if f.tell() == 0:
            writer.writeheader()

        writer.writerow(row)

    # 9. Preserve complete raw response
    raw_record = {
        **row,
        "question": question,
        "answer": answer,
        "finish_reason": finish_reason,
        "error": error,
        "response_headers": response_headers
    }

    with open(RAW_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(raw_record) + "\n")

    # 10. Print results
    print(f"\nRequest {request_number}: {status}")
    print(f"First token: {row['first_token_ms']} ms")
    print(f"Total time: {row['total_ms']} ms")
    print(f"Input tokens: {tokens_in}")
    print(f"Output tokens: {tokens_out}")
    print(f"Finish reason: {finish_reason}")

    if error:
        print("Error:", error)


async def main():
    # One request only: inspect finish reason
    question = QUESTIONS[0]

    print("Running finish-reason check...")

    await benchmark_one(question, 1)


if __name__ == "__main__":
    asyncio.run(main())
