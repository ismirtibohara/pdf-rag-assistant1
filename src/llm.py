"""Builds the prompt, calls Gemini, and returns a validated RAGAnswer."""

import os
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


def _clean(result: RAGAnswer, chunks: list[dict]) -> RAGAnswer:
    """Drop invented page numbers and keep confidence in range."""
    valid_pages = {c["page"] for c in chunks}
    result.sources = [s for s in result.sources if s.page in valid_pages]
    result.confidence = max(0.0, min(1.0, result.confidence))
    if not result.found_in_document:
        result.sources = []
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