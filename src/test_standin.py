
import asyncio

from standin import StandInModel


async def main():
    model = StandInModel()

    result = await model.generate(
        question="What is self-attention?",
        input_tokens=750,
        output_tokens=300
    )

    print("\n--- Stand-in Result ---")

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
