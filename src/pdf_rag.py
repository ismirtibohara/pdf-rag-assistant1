"""PDF text extraction, chunking, local indexing, and vector retrieval."""

from io import BytesIO

from pypdf import PdfReader


CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def split_into_chunks(text: str) -> list[str]:
    """Split normalized text into overlapping character chunks."""
    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP

    return chunks


def extract_chunks(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """Extract page text and return chunks that retain PDF page numbers."""
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        for chunk_number, text in enumerate(
            split_into_chunks(page_text), start=1
        ):
            chunks.append(
                {"page": page_number, "chunk": chunk_number, "text": text}
            )

    return chunks, len(reader.pages)


def index_chunks(collection, chunks: list[dict]) -> None:
    """Add or replace chunks and their page metadata in a Chroma collection."""
    if not chunks:
        return

    collection.upsert(
        ids=[f"page_{item['page']}_chunk_{item['chunk']}" for item in chunks],
        documents=[item["text"] for item in chunks],
        metadatas=[
            {"page": item["page"], "chunk": item["chunk"]}
            for item in chunks
        ],
    )


def retrieve(collection, query: str, top_k: int = 3) -> list[dict]:
    """Return the top matching text chunks with page and distance metadata."""
    count = collection.count()
    if count == 0 or not query.strip():
        return []

    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    documents = result["documents"][0] or []
    metadatas = result["metadatas"][0] or []
    distances = result["distances"][0] or []

    return [
        {
            "text": document,
            "page": metadata["page"],
            "chunk": metadata["chunk"],
            "distance": distance,
        }
        for document, metadata, distance in zip(
            documents, metadatas, distances
        )
    ]
