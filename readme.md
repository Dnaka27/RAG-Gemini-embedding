# RAG with Gemini — Vector Search and Contextual Q&A

Simple RAG pipeline using Google Gemini for generation and embeddings, with ChromaDB for vector search.

---

## Technologies

![Python](https://img.shields.io/badge/Python-1F2194?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini%20API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-00599C?style=for-the-badge&logo=meta&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

---

## About

Implements a retrieval-augmented generation pipeline from scratch. A Markdown file serves as the knowledge base. The pipeline chunks the content with overlap, generates embeddings using `gemini-embedding-2`, stores them in a ChromaDB collection persisted to disk, and answers questions using `gemini-3.5-flash` by retrieving the most relevant chunks and passing them as context.

Two equivalent entry points share the same core logic, organized as the `rag/` package:

- **`main.ipynb`** — the pipeline explained step by step, with detailed markdown cells
- **`app.py`** — the same pipeline behind a Streamlit UI

> `gemini-embedding-2` is a recent multimodal embedding model. Its embedding space is **not compatible** with the older `gemini-embedding-001` — re-embed your data if migrating.

```
project/
├── data/
│   └── reference.md      # Knowledge base
├── main.ipynb            # Pipeline notebook (explained step by step)
├── app.py                # Streamlit app
├── rag/                  # Core pipeline package
│   ├── config.py         # Model names, dimensions, storage paths
│   ├── client.py         # Gemini client
│   ├── chunking.py       # Dynamic chunking
│   ├── embeddings.py     # gemini-embedding-2 calls (with retry)
│   ├── vector_store.py   # ChromaDB collection helpers
│   └── generation.py     # gemini-3.5-flash answer generation
└── storage/
    └── chroma_db/        # ChromaDB persisted collection (generated on first run)
```

---

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate

pip install -r requirement.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_key_here
```

Get your key at [Google AI Studio](https://aistudio.google.com/).

Then, either:

- **Notebook**: place your `reference.md` in `data/`, open `main.ipynb` and run all cells, or
- **Streamlit app**: run `streamlit run app.py` and upload any `.md` file through the UI (no need to touch `data/`)

---

## License

This project is licensed under the MIT License.

---

## Contact

[![LinkedIn](https://img.shields.io/badge/LinkedIn-78d?style=for-the-badge&logo=linkedin&logoColor=0A0AAF)](https://www.linkedin.com/in/diogo-oike-kanefuku-23639b223/) 
[![E-mail](https://img.shields.io/badge/-Email-e9a?style=for-the-badge&logo=gmail&logoColor=E94D5F)](mailto:diogooikejapan@gmail.com)
