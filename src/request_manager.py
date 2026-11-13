
import asyncio
import time

from retrieval import RetrievalEngine
from groq_client import GroqClient
from standin import StandInModel
from rate_limiter import RateLimiter


class RequestManager:

    def __init__(
        self,
        mode="real",
        worker_count=3,
        queue_capacity=100,
        max_concurrent_calls=3,
        failure_rate=0,
        timeout_rate=0
    ):

        if mode not in ("real", "standin"):
            raise ValueError(
                "Mode must be either 'real' or 'standin'"
            )

        self.mode = mode

        # Bounded request queue
        self.queue = asyncio.Queue(maxsize=queue_capacity)

        # Worker configuration
        self.worker_count = worker_count

        # Limit simultaneous model calls
        self.semaphore = asyncio.Semaphore(
            max_concurrent_calls
        )

        # Application-level rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=1000,
            tokens_per_minute=1000000,
            requests_per_day=10000,
            tokens_per_day=10000000
        )

        # Initialize the selected model
        if self.mode == "real":

            print("Initializing REAL Groq mode...")

            self.retriever = RetrievalEngine()
            self.retriever.load_index()

            self.groq_client = GroqClient()
            self.model = None

        else:

            print("Initializing STAND-IN mode...")

            self.retriever = None
            self.groq_client = None

            # Keep internal stand-in quotas generous.
            # The application-level RateLimiter controls admission.
            self.model = StandInModel(
                requests_per_minute=100000,
                tokens_per_minute=100000000,
                daily_request_limit=100000,
                daily_token_limit=100000000,
                overload_threshold=max_concurrent_calls,
                failure_rate=failure_rate,
                timeout_rate=timeout_rate
            )

    # Estimate tokens for application-level quota checks
    def estimate_tokens(self, question, retrieved_chunks=None):

        if self.mode == "standin":
            return 750 + 300

        context = ""

        for chunk in retrieved_chunks:
            context += chunk["text"]

        # Approximate estimate: 4 characters per token
        input_text = question + context

        estimated_input = len(input_text) // 4

        # Reserve output allowance and prompt overhead
        estimated_output = 700
        prompt_overhead = 150

        return (
            estimated_input
            + estimated_output
            + prompt_overhead
        )

    # Execute selected model with retry logic
    async def generate_with_retry(
        self,
        question,
        retrieved_chunks=None,
        on_piece=None,
        max_retries=3
    ):

        for attempt in range(max_retries + 1):

            try:

                # REAL GROQ MODE
                if self.mode == "real":

                    result = await self.groq_client.generate_answer(
                        question,
                        retrieved_chunks,
                        on_piece=on_piece
                    )

                # STAND-IN MODE
                else:

                    result = await self.model.generate(
                        question,
                        input_tokens=750,
                        output_tokens=300,
                        on_piece=on_piece
                    )

                # Successful response
                if result["status"] == "ok":

                    result["retries"] = attempt
                    return result

                # Retry temporary stand-in failures/timeouts
                if result["status"] not in ("error", "timeout"):

                    result["retries"] = attempt
                    return result

                if attempt == max_retries:

                    result["retries"] = attempt
                    return result

            except Exception as e:

                # Identify retryable Groq errors
                status_code = getattr(e, "status_code", None)
                error_name = type(e).__name__

                retryable = (
                    status_code in (408, 409, 429)
                    or (
                        status_code is not None
                        and status_code >= 500
                    )
                    or error_name in (
                        "APIConnectionError",
                        "APITimeoutError"
                    )
                )

                if not retryable or attempt == max_retries:

                    return {
                        "status": "error",
                        "reason": str(e),
                        "retries": attempt
                    }

            # Exponential backoff: 1, 2, 4 seconds
            wait_time = min(2 ** attempt, 8)

            print(
                f"Temporary failure in {self.mode} mode. "
                f"Retrying in {wait_time}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )

            await asyncio.sleep(wait_time)

        return {
            "status": "error",
            "retries": max_retries
        }

    # Worker processes requests from the queue
    async def worker(self, worker_id):

        while True:

            request = await self.queue.get()

            if request is None:
                self.queue.task_done()
                break

            future = request["future"]
            request_id = request["request_id"]
            question = request["question"]
            on_piece = request["on_piece"]

            try:

                start = time.perf_counter()

                print(
                    f"Worker {worker_id} received "
                    f"Request {request_id}"
                )

                retrieved_chunks = []

                # Retrieve passages only in real mode
                if self.mode == "real":

                    retrieved_chunks = self.retriever.search(
                        question,
                        top_k=3
                    )

                    if not retrieved_chunks:

                        result = {
                            "status": "error",
                            "reason": "No relevant passages retrieved",
                            "retries": 0
                        }

                    else:
                        result = None

                else:
                    result = None

                if result is None:

                    # Estimate token usage
                    estimated_tokens = self.estimate_tokens(
                        question,
                        retrieved_chunks
                    )

                    # Check application-level rate limits
                    allowed, reason, retry_after = (
                        await self.rate_limiter.allow_request(
                            estimated_tokens
                        )
                    )

                    if not allowed:

                        result = {
                            "status": "rate_limited",
                            "reason": reason,
                            "retry_after": retry_after,
                            "retries": 0
                        }

                        print(
                            f"Request {request_id} rejected: "
                            f"{reason}"
                        )

                    else:

                        # Acquire a model-call slot
                        async with self.semaphore:

                            print(
                                f"Worker {worker_id} processing "
                                f"Request {request_id} "
                                f"using {self.mode}"
                            )

                            result = await self.generate_with_retry(
                                question,
                                retrieved_chunks=retrieved_chunks,
                                on_piece=on_piece
                            )

                # End-to-end time including retrieval
                elapsed = (
                    time.perf_counter() - start
                ) * 1000

                result["request_id"] = request_id
                result["mode"] = self.mode
                result["end_to_end_ms"] = round(elapsed, 2)

                print(
                    f"Worker {worker_id} completed "
                    f"Request {request_id} "
                    f"| Status: {result['status']} "
                    f"| Retries: {result.get('retries', 0)} "
                    f"| Total: {elapsed:.2f} ms"
                )

                # Return result to original caller
                if not future.done():
                    future.set_result(result)

            except Exception as e:

                if not future.done():

                    future.set_result({
                        "status": "error",
                        "request_id": request_id,
                        "mode": self.mode,
                        "reason": str(e),
                        "retries": 0
                    })

            finally:

                self.queue.task_done()

    # Submit a request
    async def submit_request(
        self,
        request_id,
        question,
        on_piece=None
    ):

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        request = {
            "request_id": request_id,
            "question": question,
            "on_piece": on_piece,
            "future": future
        }

        # Add request to bounded queue
        try:

            self.queue.put_nowait(request)

        except asyncio.QueueFull:

            return {
                "status": "queue_full",
                "request_id": request_id,
                "mode": self.mode,
                "retries": 0
            }

        return await future

    # Start workers
    async def start(self):

        self.workers = [
            asyncio.create_task(
                self.worker(i + 1)
            )
            for i in range(self.worker_count)
        ]

    # Stop workers safely
    async def stop(self):

        await self.queue.join()

        for _ in range(self.worker_count):
            await self.queue.put(None)

        await asyncio.gather(*self.workers)
