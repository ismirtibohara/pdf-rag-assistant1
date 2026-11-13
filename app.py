import hashlib

import chromadb
import streamlit as st

from src.pdf_rag import extract_chunks, index_chunks, retrieve


st.set_page_config(page_title="PDF RAG Assistant", page_icon="📄")
st.title("📄 PDF RAG Assistant")
st.write(
    "Search your PDF by meaning and inspect the passages and page numbers "
    "behind each result."
)
st.info(
    "This offline-friendly baseline retrieves evidence passages locally. "
    "It does not generate paraphrased answers yet."
)

uploaded_file = st.file_uploader("Choose a PDF", type="pdf")

if uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()

    try:
        chunks, page_count = extract_chunks(pdf_bytes)
    except Exception as error:
        st.error(f"Could not read this PDF: {error}")
        st.stop()

    st.success(f"Loaded {page_count} pages.")

    if not chunks:
        st.warning(
            "No selectable text was found. This may be a scanned PDF and "
            "needs OCR before it can be searched."
        )
        st.stop()

    st.write(f"Prepared **{len(chunks)} chunks** for search.")

    try:
        chroma_client = chromadb.PersistentClient(path="chroma_db")
        pdf_id = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        collection = chroma_client.get_or_create_collection(
            name=f"pdf_{pdf_id}"
        )

        if collection.count() != len(chunks):
            with st.spinner("Indexing this PDF locally..."):
                index_chunks(collection, chunks)
    except Exception as error:
        st.error(f"Could not create the local search index: {error}")
        st.stop()

    top_k = st.slider("Number of passages to retrieve", 1, 5, 3)

    with st.form("search_form"):
        question = st.text_input("What would you like to find in this PDF?")
        submitted = st.form_submit_button("Search")

    if submitted:
        if not question.strip():
            st.warning("Enter a question to search the PDF.")
        else:
            with st.spinner("Searching locally..."):
                results = retrieve(collection, question, top_k=top_k)

            if not results:
                st.info("No matching passages were found.")
            else:
                st.subheader("Relevant passages")
                for rank, result in enumerate(results, start=1):
                    st.markdown(
                        f"**{rank}. Page {result['page']} · "
                        f"Chunk {result['chunk']}**"
                    )
                    st.write(result["text"])
                    st.caption(
                        f"Vector distance: {result['distance']:.3f} "
                        "(lower is closer)"
                    )
                    st.divider()

                st.caption(
                    "Retrieval results are evidence, not a generated answer. "
                    "Check the cited page in the original PDF."
                )
