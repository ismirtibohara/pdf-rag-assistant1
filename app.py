import hashlib

import chromadb
import streamlit as st

from src.llm import generate_answer
from src.pdf_rag import extract_chunks, index_chunks, retrieve


st.set_page_config(page_title="PDF RAG Assistant", page_icon="📄")
st.title("📄 PDF RAG Assistant")
st.write(
    "Ask a question about your PDF. The answer is generated only from "
    "passages found in the document, with page citations."
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
        question = st.text_input("What would you like to know about this PDF?")
        submitted = st.form_submit_button("Ask")

    if submitted:
        if not question.strip():
            st.warning("Enter a question to search the PDF.")
        else:
            with st.spinner("Finding relevant passages..."):
                results = retrieve(collection, question, top_k=top_k)

            if not results:
                st.info("No matching passages were found.")
            else:
                with st.spinner("Generating answer..."):
                    answer = generate_answer(question, results)

                if answer.found_in_document:
                    st.subheader("Answer")
                    st.write(answer.answer)

                    if answer.sources:
                        with st.expander("Sources", expanded=True):
                            for source in answer.sources:
                                st.markdown(f"**Page {source.page}**")
                                st.caption(f"“{source.quote}”")

                    st.caption(
                        f"Model's confidence estimate: {answer.confidence:.0%}. "
                        "This is a guess by the model, not a measured score. "
                        "Check the cited pages in the original PDF."
                    )
                else:
                    st.warning(answer.answer)

                with st.expander("Retrieved passages (evidence sent to the model)"):
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