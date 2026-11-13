
import asyncio

from standin import StandInModel


async def main():

    model = StandInModel(
        failure_rate=0,
        timeout_rate=0
    )

    question = "What is self-attention?"

    print("\nStand-in streaming test:\n")

    def display_piece(piece):
        print(piece, end="", flush=True)

    result = await model.generate(
        question,
        input_tokens=750,
        output_tokens=300,
        on_piece=display_piece
    )

    print("\n\n--- METRICS ---")

    print("Status:", result["status"])
    print("First token:", result["first_token_ms"], "ms")
    print("Total time:", result["total_ms"], "ms")
    print("Input tokens:", result["tokens_in"])
    print("Output tokens:", result["tokens_out"])
    print("Streaming:", result["streaming"])


if __name__ == "__main__":
    asyncio.run(main())
