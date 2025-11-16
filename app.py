import streamlit as st
import os
import numpy as np
import faiss
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# ----------------------------------------------------
# INITIAL CONFIGURATION
# ----------------------------------------------------
st.set_page_config(page_title="RAG with Gemini", layout="centered")
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("❌ GEMINI_API_KEY not found in .env")
    st.stop()

client = genai.Client(api_key=API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"
MODEL_VERSION = "gemini-2.5-flash"

INDEX_PATH = "storage/vector_db.index"
CHUNKS_PATH = "storage/schema_chunks.json"


# ----------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------
def generate_embedding(text, max_retries=5):
    """Generate an embedding with automatic retries."""
    for attempt in range(max_retries):
        try:
            emb = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[text],
                config={"task_type": "RETRIEVAL_DOCUMENT"}
            ).embeddings[0].values

            return np.array(emb, dtype="float32")

        except APIError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def create_chunks(text, max_size=1500, overlap=100):
    """Simple and efficient dynamic chunking."""
    if len(text) <= max_size:
        return [text.strip()]

    chunks = []
    step = max_size - overlap
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


# ====================================================
# ================= MAIN LAYOUT ======================
# ====================================================
st.title("RAG with Gemini")

st.markdown("""
Upload a **.md** file and the system will automatically:

1. Read the text  
2. Apply chunking  
3. Generate embeddings with Gemini  
4. Build the FAISS vector database  
5. Allow querying your document in natural language  
""")

st.divider()


# ----------------------------------------------------
# 1) MARKDOWN FILE UPLOAD
# ----------------------------------------------------
uploaded_file = st.file_uploader("📄 Upload a Markdown file (.md)", type=["md"])

if uploaded_file:
    os.makedirs("storage", exist_ok=True)

    raw_text = uploaded_file.read().decode("utf-8")
    st.success("File successfully loaded!")

    with st.expander("View file content:"):
        st.code(raw_text)

    st.write(f"Text length: **{len(raw_text)}** characters")

    st.divider()

    # ------------------------------------------------
    # 2) RAG PROCESSING (chunking → embeddings → FAISS)
    # ------------------------------------------------
    st.header("⚙️ Document Processing")

    max_size = st.slider("Max chunk size:", 500, 2000, 1500)
    overlap = st.slider("Chunk overlap:", 0, 500, 100)

    if st.button("🔧 Process Document"):
        # ---------- chunking ----------
        st.subheader("Creating chunks...")
        chunks = create_chunks(raw_text, max_size, overlap)
        st.success(f"Total chunks created: {len(chunks)}")

        # ---------- embeddings ----------
        st.subheader("Generating embeddings with Gemini...")
        progress_bar = st.progress(0)
        embeddings = []

        for i, ch in enumerate(chunks):
            emb = generate_embedding(ch)
            embeddings.append(emb)
            progress_bar.progress((i + 1) / len(chunks))

        st.success("Embeddings generated successfully!")

        # ---------- FAISS ----------
        st.subheader("Building FAISS vector database...")
        emb_np = np.array(embeddings).astype("float32")
        index = faiss.IndexFlatL2(emb_np.shape[1])
        index.add(emb_np)

        faiss.write_index(index, INDEX_PATH)
        with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        st.success("🎉 Vector database created! You can now ask questions below.")

        with st.expander("View generated chunks:"):
            for i, ch in enumerate(chunks):
                st.markdown(f"**Chunk {i + 1}:**")
                st.code(ch)
                st.markdown("---")

    st.divider()

    # ------------------------------------------------
    # 3) QUERY (User question)
    # ------------------------------------------------
    st.header("Ask Your Document")

    if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        question = st.text_input("Type your question:")
        
        submit_button = st.button("Submit")

        if submit_button:
            st.write("Generating question embedding...")

            q_emb = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[question],
                config={"task_type": "RETRIEVAL_QUERY"}
            ).embeddings[0].values

            q_emb = np.array(q_emb, dtype="float32")

            # FAISS search
            D, I = index.search(np.array([q_emb]), 5)

            context = "\n\n".join(chunks[i] for i in I[0])

            st.subheader("📚 Retrieved Context")
            with st.expander("Context used for the prompt:"):
                st.code(context)

            prompt = f"""
                Base your answer **only** on the context below:

                {context}

                Question: {question}

                Answer clearly and objectively.
            """

            st.write("Generating answer with Gemini...")

            resp = client.models.generate_content(
                model=MODEL_VERSION,
                contents=[prompt],
                config={"temperature": 0.7}
            )

            answer = resp.candidates[0].content.parts[0].text

            with st.expander("Generated Answer:"):
                st.markdown(answer)
