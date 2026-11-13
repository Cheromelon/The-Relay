
import asyncio
from request_manager import RequestManager


async def main():
    manager = RequestManager(
        worker_count=3,
        queue_capacity=100,
        max_concurrent_calls=3
    )

    await manager.start()

    questions = [
        "What is self-attention?",
        "Explain the Transformer architecture.",
        "What is dynamic chunking?",
        "How does Moshi process speech?",
        "What is multi-head attention?",
        "Explain positional encoding.",
        "What is an encoder?",
        "What is a decoder?",
        "Why do Transformers use attention?",
        "What is autoregressive generation?"
    ]

    print("\nSubmitting 10 requests...\n")

    tasks = [
        asyncio.create_task(
            manager.submit_request(i, question)
        )
        for i, question in enumerate(questions, start=1)
    ]

    results = await asyncio.gather(*tasks)

    print("\n--- Final Results ---")

    for i, result in enumerate(results, start=1):
        print(f"Request {i}: {result['status']}")

    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
