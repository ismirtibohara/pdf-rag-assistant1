"""Scores the PDF RAG assistant on a fixed question set.

Run from the project root:
    python eval/run_eval.py
"""

import json
import re
import sys
import time
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm import generate_answer  # noqa: E402
from src.pdf_rag import extract_chunks, index_chunks, retrieve  # noqa: E402

HERE = Path(__file__).resolve().parent
PDF_PATH = HERE / "ISDNn.pdf"
TEST_SET = HERE / "test_set.json"
REPORT = HERE / "last_report.md"
TOP_K = 3
PAUSE_SECONDS = 2  # small pause between calls to avoid rate limits


def squash(text: str) -> str:
    """Lowercase and remove all whitespace, so PDF spacing glitches don't matter."""
    return re.sub(r"\s+", "", text).lower()


def yes_no(value: bool) -> str:
    return "PASS" if value else "FAIL"


def main() -> None:
    if not PDF_PATH.exists():
        sys.exit(f"Put ISDNn.pdf in the eval folder first: {PDF_PATH}")

    items = json.loads(TEST_SET.read_text(encoding="utf-8"))

    chunks, _ = extract_chunks(PDF_PATH.read_bytes())
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(name="eval_run")
    index_chunks(collection, chunks)
    print(f"Indexed {len(chunks)} chunks. Running {len(items)} questions...\n")

    rows = []
    for item in items:
        question = item["question"]
        kind = item["type"]
        results = retrieve(collection, question, top_k=TOP_K)
        answer = generate_answer(question, results)

        context = squash(" ".join(r["text"] for r in results))
        retrieved_pages = {r["page"] for r in results}
        cited_pages = {s.page for s in answer.sources}
        answer_text = answer.answer.lower()
        row = {"question": question, "type": kind}

        if kind == "unanswerable":
            row["passed"] = not answer.found_in_document
            row["retrieval"] = "-"
            row["citation"] = "-"
            row["keywords"] = "-"
            row["quotes"] = "-"

        elif kind == "answerable":
            expected = set(item["expected_pages"])
            retrieval_hit = bool(expected & retrieved_pages)
            citation_ok = bool(expected & cited_pages)
            keywords_ok = all(k.lower() in answer_text for k in item["keywords"])
            quotes_ok = bool(answer.sources) and all(
                squash(s.quote) in context for s in answer.sources
            )
            row["passed"] = (
                answer.found_in_document
                and retrieval_hit
                and citation_ok
                and keywords_ok
                and quotes_ok
            )
            row["retrieval"] = yes_no(retrieval_hit)
            row["citation"] = yes_no(citation_ok)
            row["keywords"] = yes_no(keywords_ok)
            row["quotes"] = yes_no(quotes_ok)

        else:  # broad
            found = [k for k in item["keywords"] if k.lower() in answer_text]
            row["passed"] = len(found) == len(item["keywords"])
            row["retrieval"] = "-"
            row["citation"] = "-"
            row["keywords"] = f"{len(found)}/{len(item['keywords'])} topics"
            row["quotes"] = "-"

        rows.append(row)
        print(f"{yes_no(row['passed'])}  [{kind}] {question}")
        time.sleep(PAUSE_SECONDS)

    # ----- summary -----
    def rate(kind: str) -> str:
        group = [r for r in rows if r["type"] == kind]
        if not group:
            return "n/a"
        ok = sum(r["passed"] for r in group)
        return f"{ok}/{len(group)}"

    answerable = [r for r in rows if r["type"] == "answerable"]
    retrieval_hits = sum(r["retrieval"] == "PASS" for r in answerable)
    quote_hits = sum(r["quotes"] == "PASS" for r in answerable)

    lines = [
        "# Evaluation report",
        "",
        f"top_k = {TOP_K}",
        "",
        "| Question | Type | Result | Retrieval | Citation | Keywords | Quotes |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['question']} | {r['type']} | {yes_no(r['passed'])} | "
            f"{r['retrieval']} | {r['citation']} | {r['keywords']} | {r['quotes']} |"
        )
    lines += [
        "",
        "## Summary",
        "",
        f"- Answerable questions passed: {rate('answerable')}",
        f"- Retrieval found an expected page: {retrieval_hits}/{len(answerable)}",
        f"- Quotes found in retrieved text: {quote_hits}/{len(answerable)}",
        f"- Correct refusals (not in PDF): {rate('unanswerable')}",
        f"- Broad questions fully covered: {rate('broad')}",
    ]
    report = "\n".join(lines)
    REPORT.write_text(report, encoding="utf-8")

    print("\n" + report)
    print(f"\nSaved to {REPORT}")


if __name__ == "__main__":
    main()