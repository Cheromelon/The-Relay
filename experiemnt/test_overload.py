
import asyncio
import csv
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Import RequestManager from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from request_manager import RequestManager


# Experiment configuration
TOTAL_REQUESTS = 60
ARRIVAL_INTERVAL = 0.05

WORKER_COUNT = 3
QUEUE_CAPACITY = 10
MAX_CONCURRENT_CALLS = 3

OUTPUT_PATH = (
    PROJECT_ROOT / "experiments"
    / "raw_results"
    / "overload.csv"
)


async def send_request(manager, request_id):

    question = (
        f"Explain the concept of attention "
        f"in request {request_id}."
    )

    start_time = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()

    result = await manager.submit_request(
        request_id=request_id,
        question=question
    )

    user_elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    manager_elapsed_ms = (
        result.get("end_to_end_ms", 0) or 0
    )

    queue_wait_ms = max(
        0,
        user_elapsed_ms - manager_elapsed_ms
    )

    first_token_ms = result.get("first_token_ms")

    if first_token_ms is not None:
        first_token_ms += queue_wait_ms

    raw_status = result.get("status", "error")

    # Map queue_full to error in the required status column.
    # Keep the original value in raw_status.
    status = (
        "error" if raw_status == "queue_full"
        else raw_status
    )

    return {
        "request_id": request_id,
        "scenario": "sustained_overload",
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


async def monitor_queue(manager, samples, stop_event):

    while not stop_event.is_set():

        queue_size = manager.queue.qsize()

        samples.append({
            "time": time.perf_counter(),
            "queue_length": queue_size
        })

        await asyncio.sleep(0.01)


async def main():

    print("=" * 60)
    print("SUSTAINED OVERLOAD EXPERIMENT")
    print("=" * 60)

    manager = RequestManager(
        mode="standin",
        worker_count=WORKER_COUNT,
        queue_capacity=QUEUE_CAPACITY,
        max_concurrent_calls=MAX_CONCURRENT_CALLS
    )

    await manager.start()

    tasks = []
    queue_samples = []

    stop_monitor = asyncio.Event()

    monitor_task = asyncio.create_task(
        monitor_queue(
            manager,
            queue_samples,
            stop_monitor
        )
    )

    experiment_start = time.perf_counter()

    try:

        # Submit requests continuously at 20 requests/second.
        for request_id in range(1, TOTAL_REQUESTS + 1):

            task = asyncio.create_task(
                send_request(manager, request_id)
            )

            tasks.append(task)

            await asyncio.sleep(ARRIVAL_INTERVAL)

        print("\nAll requests submitted.")

        results = await asyncio.gather(*tasks)

    finally:

        await manager.stop()

        stop_monitor.set()
        await monitor_task

    experiment_duration = (
        time.perf_counter() - experiment_start
    )

    # Calculate peak queue length from sampled measurements.
    peak_queue_length = max(
        (sample["queue_length"] for sample in queue_samples),
        default=0
    )

    # Save request-level raw results.
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

    with open(
        OUTPUT_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    # Save queue-depth measurements separately.
    QUEUE_OUTPUT_PATH = (
        PROJECT_ROOT / "experiments"
        / "raw_results"
        / "overload_queue_depth.csv"
    )

    with open(
        QUEUE_OUTPUT_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["time", "queue_length"]
        )

        writer.writeheader()

        for sample in queue_samples:
            writer.writerow({
                "time": round(
                    sample["time"] - experiment_start,
                    4
                ),
                "queue_length": sample["queue_length"]
            })

    # Summary
    successful = sum(
        row["status"] == "ok"
        for row in results
    )

    queue_rejected = sum(
        row["raw_status"] == "queue_full"
        for row in results
    )

    rate_limited = sum(
        row["status"] == "rate_limited"
        for row in results
    )

    failed = len(results) - successful

    print("\n" + "=" * 60)
    print("SUSTAINED OVERLOAD RESULTS")
    print("=" * 60)

    print("Total requests:", len(results))
    print("Successful:", successful)
    print("Failed:", failed)
    print("Queue rejected:", queue_rejected)
    print("Rate limited:", rate_limited)
    print("Peak queue length:", peak_queue_length)

    print(
        f"Experiment duration: "
        f"{experiment_duration:.2f} seconds"
    )

    print(
        f"Success rate: "
        f"{successful / len(results) * 100:.2f}%"
    )

    if results:

        completed_latencies = [
            row["total_ms"]
            for row in results
            if row["status"] == "ok"
        ]

        if completed_latencies:
            average_latency = (
                sum(completed_latencies)
                / len(completed_latencies)
            )

            print(
                f"Average successful-request latency: "
                f"{average_latency:.2f} ms"
            )

    print("\nSaved request results to:")
    print(OUTPUT_PATH)

    print("\nSaved queue-depth measurements to:")
    print(QUEUE_OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
