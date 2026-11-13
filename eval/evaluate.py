"""Evaluate page-level retrieval recall for the included question set."""

import argparse
import json
from pathlib import Path

import chromadb

from src.pdf_rag import extract_chunks, index_chunks, retrieve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Path to the PDF used by the question set")
    parser.add_argument("--k", type=int, default=None)
    args = parser.parse_args()

    question_path = Path(__file__).with_name("questions.json")
    question_data = json.loads(question_path.read_text(encoding="utf-8"))
    k = args.k or question_data["k"]

    pdf_bytes = Path(args.pdf).read_bytes()
    chunks, page_count = extract_chunks(pdf_bytes)
    if not chunks:
        raise SystemExit("No selectable PDF text found; OCR may be required.")

    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(name="retrieval_eval")
    index_chunks(collection, chunks)

    hits = 0
    print(f"Evaluating {len(question_data['questions'])} questions at k={k}")
    print(f"PDF pages: {page_count}; indexed chunks: {len(chunks)}\n")

    for item in question_data["questions"]:
        results = retrieve(collection, item["question"], top_k=k)
        retrieved_pages = [result["page"] for result in results]
        relevant_pages = set(item["relevant_pages"])
        hit = bool(relevant_pages.intersection(retrieved_pages))
        hits += int(hit)
        status = "HIT" if hit else "MISS"
        print(f"[{status}] {item['question']}")
        print(f"      expected={sorted(relevant_pages)} retrieved={retrieved_pages}")

    recall = hits / len(question_data["questions"])
    print(f"\nPage Recall@{k}: {hits}/{len(question_data['questions'])} = {recall:.1%}")


if __name__ == "__main__":
    main()
