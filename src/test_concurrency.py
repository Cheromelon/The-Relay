
import asyncio

from standin import StandInModel


async def send_request(model, request_number):

    result = await model.generate(
        question=f"What is self-attention? Request {request_number}",
        input_tokens=750,
        output_tokens=300
    )

    print(
        f"Request {request_number} | "
        f"Status: {result['status']} | "
        f"First token: {result.get('first_token_ms', 'N/A')} ms | "
        f"Total: {result.get('total_ms', 'N/A')} ms | "
        f"Load: {result.get('load_multiplier', 'N/A')}"
    )

    return result


async def main():

    model = StandInModel(
        overload_threshold=3,
        failure_rate=0,
        timeout_rate=0
    )

    print("Sending 6 concurrent requests...\n")

    start = asyncio.get_running_loop().time()

    results = await asyncio.gather(
        *[
            send_request(model, i)
            for i in range(1, 7)
        ]
    )

    elapsed = asyncio.get_running_loop().time() - start

    successful = sum(
        1 for result in results
        if result["status"] == "ok"
    )

    print("\n--- Concurrency Test Summary ---")
    print("Total requests:", len(results))
    print("Successful:", successful)
    print("Failed or rejected:", len(results) - successful)
    print("Total wall-clock time:", round(elapsed, 2), "seconds")


if __name__ == "__main__":
    asyncio.run(main())
