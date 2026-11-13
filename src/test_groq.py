
import os
import asyncio

from dotenv import load_dotenv
from groq import AsyncGroq

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

if not MODEL:
    raise ValueError("GROQ_MODEL not found in .env")


# Initialize Groq client
client = AsyncGroq(
    api_key=API_KEY,
    timeout=30.0,
    max_retries=0
)


async def main():

    print("Connecting to Groq...")
    print("Model:", MODEL)

    try:

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI research assistant."
                },
                {
                    "role": "user",
                    "content": "Explain self-attention in the Transformer architecture in 3 sentences."
                }
            ],
            temperature=0.1,
            max_completion_tokens=200
        )

        # Generated answer
        answer = response.choices[0].message.content

        print("\n" + "=" * 60)
        print("GROQ CONNECTION SUCCESSFUL")
        print("=" * 60)

        print("\nGenerated Answer:")
        print(answer)

        # Token usage
        usage = response.usage

        print("\nToken Usage:")
        print("Input tokens:", usage.prompt_tokens)
        print("Output tokens:", usage.completion_tokens)
        print("Total tokens:", usage.total_tokens)

        print("\nModel:", response.model)

        print("\nTest completed successfully!")

    except Exception as e:
        print("\nGroq API request failed!")
        print("Error:", str(e))


if __name__ == "__main__":
    asyncio.run(main())
