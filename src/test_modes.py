
import asyncio
from request_manager import RequestManager


async def run_test(mode):

    print(f"\n========== {mode.upper()} MODE ==========")

    manager = RequestManager(
        mode=mode,
        worker_count=2,
        queue_capacity=10,
        max_concurrent_calls=2
    )

    await manager.start()

    question = "What is self-attention?"

    def display_piece(piece):
        print(piece, end="", flush=True)

    result = await manager.submit_request(
        1,
        question,
        on_piece=display_piece
    )

    print("\n\n--- RESULT ---")

    print("Status:", result["status"])
    print("Mode:", result["mode"])
    print("Retries:", result.get("retries", 0))
    print("Total time:", result.get("end_to_end_ms"))

    if result["status"] == "ok":

        print("Answer:", result["answer"])
        print("Input tokens:", result["tokens_in"])
        print("Output tokens:", result["tokens_out"])
        print("First token:", result.get("first_token_ms"))
        print("Model time:", result.get("total_ms"))

    else:
        print("Reason:", result.get("reason"))

    await manager.stop()


async def main():

    await run_test("standin")

    
    await run_test("real")


if __name__ == "__main__":
    asyncio.run(main())
