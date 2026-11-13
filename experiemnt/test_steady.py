
import asyncio
import csv
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Allow imports from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from request_manager import RequestManager


# Experiment configuration
TOTAL_REQUESTS = 10
ARRIVAL_INTERVAL = 0.5

WORKER_COUNT = 3
QUEUE_CAPACITY = 100
MAX_CONCURRENT_CALLS = 3

OUTPUT_PATH = PROJECT_ROOT / "experiments" / "raw_results" / "steady.csv"


async def send_request(manager, request_id):

    question = f"Explain the concept of attention in request {request_id}."

    start_time = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()

    result = await manager.submit_request(
        request_id=request_id,
        question=question
    )

    user_elapsed_ms = (time.perf_counter() - start) * 1000

    manager_elapsed_ms = result.get("end_to_end_ms", 0) or 0

    # Approximate time spent waiting in the queue.
    queue_wait_ms = max(0, user_elapsed_ms - manager_elapsed_ms)

    first_token_ms = result.get("first_token_ms")

    # User-observed first token includes queue waiting.
    if first_token_ms is not None:
        first_token_ms = first_token_ms + queue_wait_ms

    raw_status = result.get("status", "error")

    # Preserve queue_full as an error in the required status field.
    status = "error" if raw_status == "queue_full" else raw_status

    return {
        "request_id": request_id,
        "scenario": "steady",
        "source": "stand-in",
        "start_time": start_time,
        "first_token_ms": first_token_ms,
        "total_ms": round(user_elapsed_ms, 2),
        "status": status,
        "raw_status": raw_status,
        "retries": result.get("retries", 0),
        "tokens_in": result.get("tokens_in"),
        "tokens_out": result.get("tokens_out"),
        "retrieval_setting": "stand-in-no-retrieval",
        "answer_grade": "",
        "queue_wait_ms": round(queue_wait_ms, 2),
        "reason": result.get("reason", "")
    }


async def main():

    print("=" * 60)
    print("STEADY LOAD EXPERIMENT")
    print("=" * 60)

    manager = RequestManager(
        mode="standin",
        worker_count=WORKER_COUNT,
        queue_capacity=QUEUE_CAPACITY,
        max_concurrent_calls=MAX_CONCURRENT_CALLS
    )

    await manager.start()

    tasks = []

    experiment_start = time.perf_counter()

    try:

        for request_id in range(1, TOTAL_REQUESTS + 1):

            print(f"Submitting request {request_id}")

            task = asyncio.create_task(
                send_request(manager, request_id)
            )

            tasks.append(task)

            await asyncio.sleep(ARRIVAL_INTERVAL)

        results = await asyncio.gather(*tasks)

    finally:
        await manager.stop()

    experiment_duration = (
        time.perf_counter() - experiment_start
    )

    # Save raw measurements.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "request_id",
        "scenario",
        "source",
        "start_time",
        "first_token_ms",
        "total_ms",
        "status",
        "raw_status",
        "retries",
        "tokens_in",
        "tokens_out",
        "retrieval_setting",
        "answer_grade",
        "queue_wait_ms",
        "reason"
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    # Summary
    successful = sum(
        row["status"] == "ok"
        for row in results
    )

    failed = len(results) - successful

    print("\n" + "=" * 60)
    print("STEADY LOAD RESULTS")
    print("=" * 60)

    print("Total requests:", len(results))
    print("Successful:", successful)
    print("Failed:", failed)
    print(f"Experiment duration: {experiment_duration:.2f} seconds")

    if results:
        latencies = [row["total_ms"] for row in results]

        print(f"Average total latency: {sum(latencies) / len(latencies):.2f} ms")

    print("\nSaved raw results to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
