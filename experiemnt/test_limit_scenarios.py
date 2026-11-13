
import asyncio
import csv
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from rate_limiter import RateLimiter


OUTPUT_FILE = "experiments/raw_results/limit_scenarios.csv"


async def run_scenario(
    scenario,
    limiter,
    number_of_requests,
    estimated_tokens=1050
):
    print(f"\n{'=' * 55}")
    print(f"SCENARIO: {scenario}")
    print(f"{'=' * 55}")

    results = []

    for request_id in range(1, number_of_requests + 1):
        start_time = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()

        allowed, reason, retry_after = await limiter.allow_request(
            estimated_tokens
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        status = "ok" if allowed else "rate_limited"

        result = {
            "request_id": request_id,
            "scenario": scenario,
            "source": "stand-in",
            "start_time": start_time,
            "first_token_ms": "",
            "total_ms": round(elapsed_ms, 2),
            "status": status,
            "retries": 0,
            "tokens_in": 750 if allowed else "",
            "tokens_out": 300 if allowed else "",
            "retrieval_setting": "limiter-only",
            "answer_grade": "",
            "reason": reason if not allowed else ""
        }

        results.append(result)

        print(
            f"Request {request_id}: {status}"
            + (f" | Reason: {reason}" if not allowed else "")
        )

    successful = sum(r["status"] == "ok" for r in results)
    rejected = len(results) - successful

    print(f"\nTotal requests: {len(results)}")
    print(f"Accepted: {successful}")
    print(f"Rejected: {rejected}")

    return results


async def main():
    all_results = []

    # Scenario 1:
    # Normal RPM = 8, halved RPM = 4.
    # Send 8 requests to the reduced-limit limiter.
    rpm_limiter = RateLimiter(
        requests_per_minute=4,
        tokens_per_minute=100000,
        requests_per_day=1000,
        tokens_per_day=1000000
    )

    all_results += await run_scenario(
        "per_minute_limit_halved",
        rpm_limiter,
        number_of_requests=8
    )

    # Scenario 2:
    # Daily request budget = 3.
    # Send 5 requests.
    daily_request_limiter = RateLimiter(
        requests_per_minute=1000,
        tokens_per_minute=100000,
        requests_per_day=3,
        tokens_per_day=1000000
    )

    all_results += await run_scenario(
        "daily_request_budget_exhausted",
        daily_request_limiter,
        number_of_requests=5
    )

    # Scenario 3:
    # Daily token budget = 2000.
    # Each request reserves 1050 tokens.
    daily_token_limiter = RateLimiter(
        requests_per_minute=1000,
        tokens_per_minute=100000,
        requests_per_day=1000,
        tokens_per_day=2000
    )

    all_results += await run_scenario(
        "daily_token_budget_exhausted",
        daily_token_limiter,
        number_of_requests=5
    )

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    fieldnames = [
        "request_id",
        "scenario",
        "source",
        "start_time",
        "first_token_ms",
        "total_ms",
        "status",
        "retries",
        "tokens_in",
        "tokens_out",
        "retrieval_setting",
        "answer_grade",
        "reason"
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print("\n" + "=" * 55)
    print("ALL LIMIT SCENARIOS COMPLETED")
    print("=" * 55)
    print(f"Saved results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
