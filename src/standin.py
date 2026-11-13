
import asyncio
import random
import time

from collections import deque


class StandInModel:

    def __init__(
        self,
        requests_per_minute=30,
        tokens_per_minute=8000,
        daily_request_limit=1000,
        daily_token_limit=200000,
        overload_threshold=3,
        failure_rate=0.03,
        timeout_rate=0.02
    ):

        # Simulated service limits
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.daily_request_limit = daily_request_limit
        self.daily_token_limit = daily_token_limit

        # Overload configuration
        self.overload_threshold = overload_threshold
        self.active_requests = 0

        # Failure probabilities
        self.failure_rate = failure_rate
        self.timeout_rate = timeout_rate

        # Usage tracking
        self.request_times = deque()
        self.minute_tokens = deque()

        self.daily_requests = 0
        self.daily_tokens = 0

        # Calibrated from five real Groq measurements
        self.base_first_token_ms = 834
        self.base_total_ms = 969

    async def generate(
        self,
        question,
        input_tokens=750,
        output_tokens=300,
        on_piece=None
    ):

        start = time.perf_counter()
        now = time.monotonic()

        # Remove expired minute-level request records
        while (
            self.request_times
            and now - self.request_times[0] >= 60
        ):
            self.request_times.popleft()

        while (
            self.minute_tokens
            and now - self.minute_tokens[0][0] >= 60
        ):
            self.minute_tokens.popleft()

        used_minute_tokens = sum(
            tokens for timestamp, tokens in self.minute_tokens
        )

        total_tokens = input_tokens + output_tokens

        # Check daily request limit
        if self.daily_requests >= self.daily_request_limit:
            return {
                "status": "rate_limited",
                "reason": "Daily request limit exhausted"
            }

        # Check daily token limit
        if self.daily_tokens + total_tokens > self.daily_token_limit:
            return {
                "status": "rate_limited",
                "reason": "Daily token budget exhausted"
            }

        # Check requests per minute
        if len(self.request_times) >= self.requests_per_minute:
            return {
                "status": "rate_limited",
                "reason": "Requests per minute limit exceeded"
            }

        # Check tokens per minute
        if used_minute_tokens + total_tokens > self.tokens_per_minute:
            return {
                "status": "rate_limited",
                "reason": "Tokens per minute limit exceeded"
            }

        # Reserve quota for accepted request
        self.request_times.append(now)
        self.minute_tokens.append((now, total_tokens))

        self.daily_requests += 1
        self.daily_tokens += total_tokens

        # Track concurrent requests
        self.active_requests += 1

        active_at_start = self.active_requests

        try:

            # Simulate overload latency
            overload = max(
                0,
                active_at_start - self.overload_threshold
            )

            load_multiplier = 1 + (0.15 * overload)

            first_token_delay = (
                random.uniform(0.7, 1.2)
                * self.base_first_token_ms
                / 1000
                * load_multiplier
            )

            remaining_delay = max(
                0.05,
                (
                    self.base_total_ms
                    - self.base_first_token_ms
                ) / 1000 * load_multiplier
            )

            # Simulate an internal failure
            if random.random() < self.failure_rate:

                await asyncio.sleep(0.05)

                return {
                    "status": "error",
                    "reason": "Simulated internal server error"
                }

            # Simulate timeout
            if random.random() < self.timeout_rate:

                await asyncio.sleep(2)

                return {
                    "status": "timeout",
                    "reason": "Simulated request timeout"
                }

            # Wait until first piece is generated
            await asyncio.sleep(first_token_delay)

            first_token_ms = (
                time.perf_counter() - start
            ) * 1000

            # Generate simulated response
            response = f"Simulated answer to: {question}."

            # Split response into pieces
            pieces = response.split()

            streamed = []

            # Stream pieces one by one
            for piece in pieces:

                streamed.append(piece + " ")

                if on_piece is not None:
                    on_piece(piece + " ")

                await asyncio.sleep(
                    remaining_delay / max(1, len(pieces))
                )

            total_ms = (
                time.perf_counter() - start
            ) * 1000

            return {
                "status": "ok",
                "answer": "".join(streamed).strip(),
                "first_token_ms": round(first_token_ms, 2),
                "total_ms": round(total_ms, 2),
                "tokens_in": input_tokens,
                "tokens_out": output_tokens,
                "active_requests_at_start": active_at_start,
                "load_multiplier": round(load_multiplier, 2),
                "model": "standin-model",
                "streaming": True
            }

        finally:

            # Always release active request count
            self.active_requests -= 1
