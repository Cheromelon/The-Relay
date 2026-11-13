
import asyncio
import time
from collections import deque


class RateLimiter:
    def __init__(
        self,
        requests_per_minute=8,
        tokens_per_minute=100000,
        requests_per_day=1000,
        tokens_per_day=1000000
    ):
        self.rpm_limit = requests_per_minute
        self.tpm_limit = tokens_per_minute
        self.rpd_limit = requests_per_day
        self.tpd_limit = tokens_per_day

        # Entries: (timestamp, estimated_tokens)
        self.minute_usage = deque()
        self.daily_usage = deque()

        # Protect quota checks from concurrent workers
        self.lock = asyncio.Lock()

    def remove_expired(self, now):
        # Remove entries older than 60 seconds
        while (
            self.minute_usage
            and now - self.minute_usage[0][0] >= 60
        ):
            self.minute_usage.popleft()

        # Remove entries older than 24 hours
        while (
            self.daily_usage
            and now - self.daily_usage[0][0] >= 86400
        ):
            self.daily_usage.popleft()

    async def allow_request(self, estimated_tokens):
        async with self.lock:
            now = time.monotonic()

            self.remove_expired(now)

            minute_requests = len(self.minute_usage)
            minute_tokens = sum(
                tokens for _, tokens in self.minute_usage
            )

            daily_requests = len(self.daily_usage)
            daily_tokens = sum(
                tokens for _, tokens in self.daily_usage
            )

            # Check request limits
            if minute_requests + 1 > self.rpm_limit:
                retry_after = max(
                    0,
                    60 - (now - self.minute_usage[0][0])
                )

                return False, "rate_limited_rpm", retry_after

            if daily_requests + 1 > self.rpd_limit:
                retry_after = max(
                    0,
                    86400 - (now - self.daily_usage[0][0])
                )

                return False, "rate_limited_rpd", retry_after

            # Check token limits
            if minute_tokens + estimated_tokens > self.tpm_limit:
                retry_after = max(
                    0,
                    60 - (now - self.minute_usage[0][0])
                ) if self.minute_usage else 60

                return False, "rate_limited_tpm", retry_after

            if daily_tokens + estimated_tokens > self.tpd_limit:
                retry_after = max(
                    0,
                    86400 - (now - self.daily_usage[0][0])
                ) if self.daily_usage else 86400

                return False, "rate_limited_tpd", retry_after

            # Reserve quota for this request
            entry = (now, estimated_tokens)

            self.minute_usage.append(entry)
            self.daily_usage.append(entry)

            return True, "allowed", 0
