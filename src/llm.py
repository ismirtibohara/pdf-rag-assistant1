"""Builds the prompt, calls Gemini, and returns a validated RAGAnswer."""

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from src.schemas import RAGAnswer

load_dotenv()

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "rag_prompt_v1.txt"
)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_ATTEMPTS = 4


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(f"[Page {c['page']}]\n{c['text']}" for c in chunks)


def build_prompt(question: str, chunks: list[dict]) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{question}", question).replace(
        "{context}", build_context(chunks)
    )


def _squash(text: str) -> str:
    """Lowercase and delete all whitespace, including line breaks.

    PDF extraction often inserts stray spaces or breaks inside a word.
    Comparing the squashed strings still counts those as the same quote.
    """
    return re.sub(r"\s+", "", text).lower()


def _quote_is_in_source(quote: str, page: int, chunks: list[dict]) -> bool:
    """True when the quote is copied from a retrieved chunk on that page."""
    needle = _squash(quote)
    if not needle:
        return False

    for chunk in chunks:
        if chunk["page"] != page:
            continue
        if needle in _squash(chunk["text"]):
            return True
    return False


def _clean(result: RAGAnswer, chunks: list[dict]) -> RAGAnswer:
    """Keep only real citations and clamp confidence to 0–1.

    A citation is kept only when both of these are true:
    - its page number was actually retrieved
    - its quote appears in that page's retrieved text

    Quotes the model invented, paraphrased, or joined with "..." are dropped.
    The written answer is left as-is. If every quote fails, Sources is empty
    and confidence is set to 0 so the UI does not treat it as well supported.
    """
    kept = [
        source
        for source in result.sources
        if _quote_is_in_source(source.quote, source.page, chunks)
    ]
    result.confidence = max(0.0, min(1.0, result.confidence))

    # A refusal should not cite pages. If the model claims it found an
    # answer but every quote was invented or paraphrased, keep the
    # answer text and clear confidence so it is not shown as supported.
    if not result.found_in_document:
        result.sources = []
    elif not kept:
        result.sources = []
        result.confidence = 0.0
    else:
        result.sources = kept
    return result


def _fallback(message: str) -> RAGAnswer:
    return RAGAnswer(
        answer=message, sources=[], confidence=0.0, found_in_document=False
    )


def generate_answer(question: str, chunks: list[dict]) -> RAGAnswer:
    if not chunks:
        return _fallback("I could not find this in the document.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback("GEMINI_API_KEY is missing. Check your .env file.")

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(question, chunks)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RAGAnswer,
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL, contents=prompt, config=config
            )
            result = RAGAnswer.model_validate_json(response.text)
            return _clean(result, chunks)
        except errors.ServerError:
            time.sleep(4 * attempt)  # busy server (503): wait and retry
        except errors.ClientError as e:
            if e.code == 429:  # rate limit: wait and retry
                time.sleep(6 * attempt)
            else:
                return _fallback(f"Model error ({e.code}). Check GEMINI_MODEL.")
        except (ValidationError, ValueError):
            pass  # invalid JSON: try again

    return _fallback("The AI service is busy right now. Please try again.")