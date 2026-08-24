import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import chromadb

from src.ingestion.pipeline import process_and_index_pdf
from src.rag.pipeline import answer_question


st.set_page_config(page_title="Privacy Analyst", layout="wide")

CUSTOM_CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}

.block-container {
    padding-top: 2.5rem;
    max-width: 900px;
}

h1 {
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.app-subtitle {
    color: #6B6B6B;
    font-size: 0.9rem;
    margin-top: -0.8rem;
    margin-bottom: 2rem;
}

section[data-testid="stSidebar"] {
    border-right: 1px solid #E5E5E3;
}

section[data-testid="stSidebar"] h2 {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6B6B6B;
}

.doc-list-item {
    padding: 0.4rem 0;
    border-bottom: 1px solid #EDEDEB;
    font-size: 0.9rem;
    color: #3B3B3B;
}

.stButton button {
    border-radius: 6px;
    border: 1px solid #D9D9D6;
    background-color: #FFFFFF;
    color: #1A1A1A;
    font-weight: 500;
}

.stButton button:hover {
    border-color: #3B3B3B;
    color: #3B3B3B;
}

div[data-testid="stChatMessage"] {
    border-radius: 10px;
}

.source-item {
    font-size: 0.85rem;
    color: #4A4A4A;
    padding: 0.25rem 0;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(path="data/chroma_db")
    return client.get_or_create_collection(
        name="private_documents",
        metadata={"hnsw:space": "cosine"},
    )

collection = get_collection()

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown("## Documents")
    st.caption("All processing happens locally. No file ever leaves this computer.")

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded_file is not None:
        if st.button("Process and index", use_container_width=True):
            uploads_folder = Path("data")
            uploads_folder.mkdir(exist_ok=True)
            destination_path = uploads_folder / uploaded_file.name

            with open(destination_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Extracting text, generating chunks, and indexing..."):
                num_chunks = process_and_index_pdf(str(destination_path), collection)

            st.success(f"Indexed '{uploaded_file.name}' ({num_chunks} fragments).")

    st.divider()
    st.markdown("## Indexed documents")
    metadatas = collection.get()["metadatas"]
    unique_documents = sorted(set(m["source_document"] for m in metadatas)) if metadatas else []
    if unique_documents:
        for doc in unique_documents:
            st.markdown(f'<div class="doc-list-item">{doc}</div>', unsafe_allow_html=True)
    else:
        st.caption("No documents indexed yet.")

st.markdown("# Privacy Analyst")
st.markdown(
    '<div class="app-subtitle">Chat with your sensitive documents. Fully local, no internet connection required.</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(
                        f'<div class="source-item">{source["document"]} — page {source["page"]}</div>',
                        unsafe_allow_html=True,
                    )

user_question = st.chat_input("Ask a question about your documents...")

if user_question:
    st.session_state.history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.write(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating an answer..."):
            if not unique_documents:
                answer_text = "No documents indexed yet. Upload a PDF from the sidebar first."
                sources = []
            else:
                result = answer_question(user_question, collection)
                answer_text = result["answer"]
                sources = result["sources"]

        st.write(answer_text)
        if sources:
            with st.expander("Sources"):
                for source in sources:
                    st.markdown(
                        f'<div class="source-item">{source["document"]} — page {source["page"]}</div>',
                        unsafe_allow_html=True,
                    )

    st.session_state.history.append({
        "role": "assistant",
        "content": answer_text,
        "sources": sources,
    })
