
import os
import time

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL")

if not API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

if not MODEL:
    raise ValueError("GROQ_MODEL is missing from .env")


class GroqClient:

    def __init__(self):
        self.client = AsyncGroq(
            api_key=API_KEY,
            timeout=30.0,
            max_retries=0
        )

    async def generate_answer(
        self,
        question,
        retrieved_chunks,
        on_piece=None
    ):

        # Build context from retrieved passages
        context = ""

        for i, chunk in enumerate(retrieved_chunks, start=1):
            context += (
                f"\nPassage {i}\n"
                f"Paper: {chunk['paper']}\n"
                f"Page: {chunk['page']}\n"
                f"Text: {chunk['text']}\n"
            )

        system_prompt = """
You are a research assistant answering questions using only the
provided passages from three research papers.

Rules:
1. Answer only using information in the provided passages.
2. Do not use outside knowledge.
3. Cite factual claims using the paper name and page number.
4. If the passages do not contain enough information, clearly say:
   "The provided papers do not contain enough information to answer this."
5. Never invent facts or citations.
"""

        start_time = time.perf_counter()

        first_token_ms = None
        answer_parts = []
        tokens_in = None
        tokens_out = None

        # Request streaming response
        stream = await self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Retrieved passages:\n{context}"
                    )
                }
            ],
            temperature=0.1,
            max_completion_tokens=1000,
            stream=True
        )

        # Receive generated pieces one by one
        async for chunk in stream:

            # Capture token usage if provider sends it
            usage = getattr(chunk, "usage", None)

            if usage is not None:
                tokens_in = usage.prompt_tokens
                tokens_out = usage.completion_tokens

            if not chunk.choices:
                continue

            piece = chunk.choices[0].delta.content

            if piece:

                if first_token_ms is None:
                    first_token_ms = (
                        time.perf_counter() - start_time
                    ) * 1000

                answer_parts.append(piece)

                # Send each piece to the caller immediately
                if on_piece is not None:
                    on_piece(piece)

        total_ms = (
            time.perf_counter() - start_time
        ) * 1000

        answer = "".join(answer_parts)

        return {
            "status": "ok",
            "answer": answer,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model": MODEL,
            "first_token_ms": first_token_ms,
            "total_ms": total_ms,
            "streaming": True
        }
