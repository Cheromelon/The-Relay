
import fitz
import json
import re
import argparse
from pathlib import Path

PAPERS_DIR = Path("papers")
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

PAPERS = {
    "1706.03762v7.pdf": "Attention Is All You Need",
    "2410.00037v1.pdf": "Moshi: a speech-text foundation model for real-time dialogue",
    "2507.07955v2.pdf": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling"
}


def clean_text(text):
    text = re.sub(r"-\s*\n", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_into_chunks(text, chunk_size, overlap):
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = text.rfind(". ", start, end)

            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

    return chunks


def process_paper(filename, title, chunk_size, overlap):
    pdf_path = PAPERS_DIR / filename

    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF: {pdf_path}")

    document = fitz.open(pdf_path)
    paper_chunks = []

    for page_index, page in enumerate(document):
        page_text = clean_text(page.get_text("text"))

        if not page_text:
            continue

        chunks = split_into_chunks(page_text, chunk_size, overlap)

        for chunk_index, chunk in enumerate(chunks):
            paper_chunks.append({
                "paper": title,
                "filename": filename,
                "page": page_index + 1,
                "chunk_index": chunk_index,
                "text": chunk
            })

    document.close()

    print(f"{title}: {len(paper_chunks)} chunks")

    return paper_chunks


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--tag", type=str, default="default")

    args = parser.parse_args()

    if args.chunk_size <= 0:
        parser.error("chunk-size must be positive")

    if args.overlap < 0 or args.overlap >= args.chunk_size:
        parser.error("overlap must be non-negative and smaller than chunk-size")

    all_chunks = []

    for filename, title in PAPERS.items():
        chunks = process_paper(
            filename,
            title,
            args.chunk_size,
            args.overlap
        )
        all_chunks.extend(chunks)

    output_path = OUTPUT_DIR / f"chunks_{args.tag}.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(all_chunks, file, indent=2, ensure_ascii=False)

    print("\nIngestion completed!")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Overlap: {args.overlap}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
