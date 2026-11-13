
import asyncio
from request_manager import RequestManager


async def main():

    manager = RequestManager(
        worker_count=2,
        queue_capacity=10,
        max_concurrent_calls=2
    )

    await manager.start()

    question = (
        "What is the role of self-attention "
        "in the Transformer architecture?"
    )

    result = await manager.submit_request(
        1,
        question
    )

    print("\n--- FINAL RESULT ---")
    print("Status:", result["status"])

    if result["status"] == "ok":
        print("\nAnswer:")
        print(result["answer"])

        print("\nInput tokens:", result["tokens_in"])
        print("Output tokens:", result["tokens_out"])
        print("Retries:", result["retries"])

        print("\nRetrieved papers:")

        for chunk in result["retrieved_chunks"]:
            print(
                chunk["paper"],
                "| Page:",
                chunk["page"]
            )

    else:
        print("Error:", result.get("reason"))

    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
