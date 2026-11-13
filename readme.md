
# The Relay – LLM Inference and Reliability Pipeline

A Python-based LLM inference pipeline that combines document retrieval, Groq API integration, request management, rate limiting, streaming responses, and load testing.

The project explores how an LLM application behaves under different traffic conditions and how a system can handle rate limits, request failures, and increasing workloads.

---

## 1. Project Overview

The Relay is a small LLM-powered question-answering system built around three research papers.

A user submits a question, the system retrieves relevant passages from the research papers, and a language model generates an answer using the retrieved information.

The project also includes a simulated model service (stand-in) to test system behaviour under different conditions without continuously sending requests to the real API.

### Main Objectives

- Build a retrieval-augmented question-answering pipeline.
- Integrate a real hosted LLM using the Groq API.
- Implement request queues and concurrency control.
- Handle rate limits, failures, and retries.
- Simulate slow responses, failures, and overload using a stand-in model.
- Evaluate latency, throughput, retrieval quality, and answer quality.
- Compare system behaviour under different traffic patterns.

---

## 2. System Architecture

The pipeline consists of the following components:

1. **Document Ingestion:** Extracts text from research papers and divides it into smaller chunks.
2. **Embedding Generation:** Converts text chunks into numerical vector representations.
3. **Vector Search:** Uses FAISS to find passages relevant to the user's question.
4. **LLM Generation:** Sends the question and retrieved passages to the Groq-hosted language model.
5. **Request Manager:** Manages incoming requests using a bounded queue and worker tasks.
6. **Rate Limiter:** Controls request and token admission according to configured limits.
7. **Stand-in Model:** Simulates model latency, streaming, failures, and overload.
8. **Evaluation:** Measures retrieval performance, answer quality, and system reliability.

### High-Level Workflow

```text
              User Question
                    |
                    v
             Request Manager
                    |
                    v
              Request Queue
                    |
                    v
               Rate Limiter
                    |
                    v
             Worker / Semaphore
                    |
                    v
             Document Retrieval
                    |
                    v
               FAISS Search
                    |
                    v
            Retrieved Passages
                    |
                    v
              LLM Generation
                    |
             +------+------+
             |             |
             v             v
          Groq API     Stand-in Model
             |             |
             +------+------+
                    |
                    v
             Generated Answer
                    |
                    v
               User Response
```

---

## 3. Research Paper Library

The retrieval system uses the following three research papers:

| Paper | arXiv Version |
|---|---|
| Attention Is All You Need | 1706.03762v7 |
| Moshi: a speech-text foundation model for real-time dialogue | 2410.00037v1 |
| Dynamic Chunking for End-to-End Hierarchical Sequence Modeling | 2507.07955v2 |

The papers are stored in the `papers/` directory.

---

## 4. Retrieval Pipeline

The ingestion process extracts text from PDF documents using PyMuPDF.

The extracted text is cleaned and divided into overlapping chunks. Sentence boundaries are considered when splitting the text.

Each chunk is converted into an embedding using the `all-MiniLM-L6-v2` sentence-transformer model.

FAISS is used to perform similarity search over the stored embeddings.

For each question, the retriever returns the most relevant passages, which are passed to the language model as context.

### Retrieval Configurations

Four configurations were evaluated by changing chunk size and the number of retrieved passages.

| Configuration | Chunk Size | Overlap | Top-K |
|---|---:|---:|---:|
| A | 1200 | 200 | 3 |
| B | 1200 | 200 | 5 |
| C | 600 | 100 | 3 |
| D | 600 | 100 | 5 |

No reranking was used in these configurations.

### Retrieval Evaluation

The retrieval evaluation used 15 questions.

| Configuration | Expected Paper Found |
|---|---:|
| A | 15/15 |
| B | 15/15 |
| C | 14/15 |
| D | 15/15 |

Configuration D retrieved the expected paper for all 15 questions while using smaller chunks than A and B.

The expected-paper metric checks whether at least one retrieved passage came from the expected paper. It does not independently establish that the passage contains the correct answer.

---

## 5. LLM Integration

The project uses the Groq API to access a hosted language model.

The model used during the recorded experiments was:

`openai/gpt-oss-20b`

The API integration supports streaming responses and records performance information such as:

- Time to first token (TTFT).
- Total response time.
- Input token count.
- Output token count.
- Request status.
- Model information.

API credentials are loaded from environment variables rather than being hardcoded into the source code.

Create a `.env` file locally:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

**Never commit the `.env` file to GitHub.**

---

## 6. Request Management

The request manager controls how incoming requests are processed.

It uses:

- An asynchronous request queue.
- Worker tasks to process requests.
- A semaphore to limit concurrent model calls.
- A bounded queue to prevent unlimited request accumulation.
- A rate limiter to control request and token admission.
- Retry handling for temporary failures and timeouts.

When the queue reaches its configured capacity, new requests are rejected rather than being added indefinitely.

The retry mechanism uses exponential backoff, increasing the waiting time between successive retry attempts.

---

## 7. Stand-in Model

A stand-in model was implemented to simulate a hosted model service.

It allows load testing without depending on the real API for every request.

The stand-in supports:

- Configurable response delays.
- Simulated temporary failures.
- Simulated timeouts.
- Rate-limit behaviour.
- Streaming responses.
- Increased latency under higher concurrency.

The stand-in was calibrated using measurements from the real Groq service.

It is important to distinguish simulated behaviour from actual provider behaviour. Stand-in experiments are used to understand system-level behaviour, not to claim that the real Groq service has identical performance.

---

## 8. Load Testing

Three main traffic patterns were tested using the stand-in model.

| Scenario | Requests | Configuration |
|---|---:|---|
| Steady traffic | 10 | 3 workers, 0.5-second arrival interval |
| Burst traffic | 30 | 3 workers, simultaneous submission |
| Sustained overload | 60 | 3 workers, 0.05-second arrival interval, queue capacity 10 |

Additional rate-limit scenarios were tested by reducing configured application-level quotas.

### Load Test Results

| Metric | Steady | Burst | Sustained Overload |
|---|---:|---:|---:|
| Requests submitted | 10 | 30 | 60 |
| Successful requests | 10 | 30 | 21 |
| Failed/rejected requests | 0 | 0 | 39 |
| Success rate | 100% | 100% | 35% |
| Average total latency | 930.52 ms | 5225.86 ms | 2763.29 ms |
| Peak queue length | Not measured | 27 | 10 |

The sustained overload test demonstrates how a bounded queue protects the system from accepting more work than it can process.

During burst traffic, queue waiting time became a major contributor to overall response latency.

The sustained overload experiment rejected 39 requests when the queue was full. These were queue rejections, not model timeouts.

### Rate-Limit Experiments

Application-level rate-limit scenarios were also tested.

| Scenario | Requests | Accepted | Rejected |
|---|---:|---:|---:|
| Per-minute limit halved | 8 | 4 | 4 |
| Daily request budget exhausted | 5 | 3 | 2 |
| Daily token budget exhausted | 5 | 1 | 4 |

These are simulated application-level quota experiments and should not be interpreted as measurements of Groq's actual account limits.

---

## 9. Answer Quality Evaluation

The answer evaluation used 15 questions across the three research papers with configuration D.

Answers were manually reviewed using four categories:

- `correct`: Answer is supported and appropriately cited.
- `wrong`: Answer is incorrect or does not satisfy the citation requirements.
- `refused_correctly`: The system correctly refuses an unsupported question.
- `refused_wrongly`: The system refuses a question that the papers can answer.

### Recorded Results

| Evaluation Category | Count |
|---|---:|
| Correct | 5 |
| Wrong | 9 |
| Correctly refused | 0 |
| Wrongly refused | 1 |

The correct-and-cited rate was 33.3%.

The evaluation highlighted that retrieving relevant passages alone is not sufficient. The generation stage must also use the evidence correctly and provide citations that identify the paper and page or section.

---

## 10. Project Structure

```text
The_Relay/
│
├── papers/
│   ├── 1706.03762v7.pdf
│   ├── 2410.00037v1.pdf
│   └── 2507.07955v2.pdf
│
├── data/
│   ├── evaluation_questions.json
│   ├── answer_evaluation.json
│   ├── retrieval_evaluation.json
│   └── ...
│
├── src/
│   ├── ingest.py
│   ├── retrieval.py
│   ├── groq_client.py
│   ├── request_manager.py
│   ├── rate_limiter.py
│   ├── standin.py
│   ├── evaluate_answers.py
│   └── evaluate_retrival.py
│
├── experiments/
│   ├── test_steady.py
│   ├── test_burst.py
│   ├── test_overload.py
│   ├── test_limit_scenarios.py
│   └── raw_results/
│
├── results.csv
├── requirements.txt
├── .gitignore
└── README.md
```

The `.env` file is kept locally and must not be committed to the repository.

---

## 11. Installation and Setup

### Prerequisites

- Python 3.11
- A Groq API key
- Git

### Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/the-relay.git
cd the-relay
```

### Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root and add your Groq API key and model name.

### Run the Pipeline

Run document ingestion:

```bash
python src/ingest.py
```

Run retrieval evaluation:

```bash
python src/evaluate_retrival.py
```

Run answer evaluation:

```bash
python src/evaluate_answers.py
```

The experiment scripts can be run individually:

```bash
python experiments/test_steady.py
python experiments/test_burst.py
python experiments/test_overload.py
python experiments/test_limit_scenarios.py
```

**Note:** The evaluation scripts use the corresponding chunk files and FAISS indexes. Ensure these generated artifacts are available before running the experiments.

---

## 12. Results and Reproducibility

The repository includes:

- `results.csv` containing consolidated experiment records.
- Raw CSV files for steady, burst, overload, and rate-limit experiments.
- Retrieval evaluation results.
- Answer evaluation results.
- The original research paper PDFs.

The raw results are retained so that the reported metrics can be independently recalculated.

---

## 13. Limitations and Future Improvements

Some limitations identified during development include:

- The answer-quality evaluation currently uses a relatively small set of 15 questions.
- The expected-paper retrieval metric does not measure passage-level relevance.
- The embedding model has a maximum input sequence length, so longer chunks may be truncated during embedding.
- Some answers were truncated by the configured output-token limit.
- The stand-in model is an approximation and cannot reproduce every behaviour of a real hosted service.
- Real-provider concurrency limits and daily quota recovery were not fully experimentally verified.
- The cost per 1,000 answers was not measured.

### Possible Future Improvements

- Adding a reranking stage to improve retrieval relevance.
- Improving citation validation.
- Expanding the answer evaluation dataset.
- Measuring real-provider performance under carefully controlled concurrency.
- Improving dynamic chunking and retrieval strategies.
- Adding monitoring and visualization for queue length, latency, and token usage.

---

## 14. Conclusion

The Relay demonstrates an end-to-end LLM question-answering pipeline with retrieval, hosted model integration, request management, and a simulated model service.

The experiments show how traffic patterns affect response latency and how bounded queues and rate limiting help control incoming workloads.

The project also highlights an important distinction between retrieval quality and answer quality: finding the right document does not guarantee that the generated response is correct or properly cited.

The goal of this project was not just to build an LLM application, but to understand its performance, reliability, and behaviour under different operating conditions.
