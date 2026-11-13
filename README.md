# PDF RAG Assistant

A PDF semantic search app built with Python, Streamlit, pypdf, and ChromaDB.

## Live demo

[Open PDF RAG Assistant](https://pdf-rag-assistant1-fsygsdfxayn3ifpgvyqggb.streamlit.app/)
[View the GitHub repository](https://github.com/ismirtibohara/pdf-rag-assistant1)

## What it does

- Extracts selectable text from an uploaded PDF.
- Splits each page into overlapping chunks and keeps page metadata.
- Uses ChromaDB's default embedding function for semantic vector search.
- Displays the most relevant passages with their PDF page numbers.
- Stores the local vector index in `chroma_db/`.

This is a **retrieval baseline**. It finds and displays evidence passages; it does not generate paraphrased answers yet.

## Architecture

```mermaid
flowchart LR
    A[PDF upload] --> B[pypdf text extraction]
    B --> C[Page-aware overlapping chunks]
    C --> D[ChromaDB vector index]
    E[Question] --> F[Embedding and similarity search]
    D --> F
    F --> G[Ranked passages with page citations]
