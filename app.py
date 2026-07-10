import os

import streamlit as st
from dotenv import load_dotenv

import rag

# ----------------------------------------------------
# INITIAL CONFIGURATION
# ----------------------------------------------------
st.set_page_config(page_title="RAG with Gemini", layout="centered")
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY not found in .env")
    st.stop()

client = rag.get_client()

# ----------------------------------------------------
# MAIN LAYOUT
# ----------------------------------------------------
st.title("RAG with Gemini")

st.markdown("""
Upload a **.md** file and the system will automatically:

1. Read the text
2. Apply chunking
3. Generate embeddings with `gemini-embedding-2`
4. Build a ChromaDB vector collection
5. Allow querying your document in natural language
""")

st.divider()

# ----------------------------------------------------
# 1) MARKDOWN FILE UPLOAD
# ----------------------------------------------------
uploaded_file = st.file_uploader("Upload a Markdown file (.md)", type=["md"])

if uploaded_file:
    os.makedirs("storage", exist_ok=True)

    raw_text = uploaded_file.read().decode("utf-8")
    st.success("File successfully loaded!")

    with st.expander("View file content:"):
        st.code(raw_text)

    st.write(f"Text length: `{len(raw_text)}` characters")

    st.divider()

    # ------------------------------------------------
    # 2) RAG PROCESSING (chunking -> embeddings -> ChromaDB)
    # ------------------------------------------------
    st.header("Document Processing")

    max_size = st.slider("Max chunk size:", 500, 2000, 1500)
    overlap = st.slider("Chunk overlap:", 0, max_size - 1, min(100, max_size - 1))

    if st.button("Process Document"):
        st.subheader("Creating chunks...")
        chunks = rag.chunk_text(raw_text, max_size, overlap)
        st.success(f"Total chunks created: {len(chunks)}")

        st.subheader("Generating embeddings with Gemini...")
        progress_bar = st.progress(0)
        embeddings = []

        for i, chunk in enumerate(chunks):
            embeddings.append(rag.embed_text(client, chunk, task="document"))
            progress_bar.progress((i + 1) / len(chunks))

        st.success("Embeddings generated successfully!")

        st.subheader("Building ChromaDB vector collection...")
        collection = rag.reset_collection()
        rag.add_chunks(collection, chunks, embeddings)

        st.success("Vector database created! You can now ask questions below.")

        with st.expander("View generated chunks:"):
            for i, chunk in enumerate(chunks):
                st.markdown(f"**Chunk {i + 1}:**")
                st.code(chunk)
                st.markdown("---")

    st.divider()

    # ------------------------------------------------
    # 3) QUERY (User question)
    # ------------------------------------------------
    st.header("Ask Your Document")

    collection = rag.get_collection()

    if collection.count() > 0:
        question = st.text_input("Type your question:")
        submit_button = st.button("Submit")

        if submit_button:
            st.write("Generating question embedding...")
            query_embedding = rag.embed_text(client, question, task="query")

            st.write("Searching ChromaDB...")
            retrieved_chunks = rag.retrieve(collection, query_embedding, top_k=5)
            context = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)

            st.subheader("Retrieved Context")
            with st.expander("Context used for the prompt:"):
                for i, chunk in enumerate(retrieved_chunks, start=1):
                    st.markdown(f"**Chunk {i}** (distance: {chunk['distance']:.4f})")
                    st.code(chunk["text"])

            st.write("Generating answer with Gemini...")
            answer = rag.generate_answer(client, question, context)

            with st.expander("Generated Answer:", expanded=True):
                st.markdown(answer)
    else:
        st.info("Process a document above before asking questions.")
