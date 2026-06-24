# RAG with Gemini — Vector Search and Contextual Q&A

Simple RAG pipeline using Google Gemini for generation and embeddings, with FAISS for vector search.

---

## Technologies

![Python](https://img.shields.io/badge/Python-1F2194?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini%20API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-00599C?style=for-the-badge&logo=meta&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)

---

## About

Implements a retrieval-augmented generation pipeline from scratch. A Markdown file serves as the knowledge base. The pipeline chunks the content with overlap, generates embeddings using `gemini-embedding-001`, stores them in a FAISS index, and answers questions by retrieving the most relevant chunks and passing them as context to the Gemini model.

```
project/
├── reference.md          # Knowledge base
├── main.ipynb            # Pipeline notebook
├── storage/
│   ├── vector_db.index   # FAISS index
│   └── schema_chunks.json
└── app.py
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

Place your `reference.md` in the project root, then open `main.ipynb` and run all cells.

---

## License

This project is licensed under the MIT License.

---

## Contact

[![LinkedIn](https://img.shields.io/badge/LinkedIn-78d?style=for-the-badge&logo=linkedin&logoColor=0A0AAF)](https://www.linkedin.com/in/diogo-oike-kanefuku-23639b223/) 
[![E-mail](https://img.shields.io/badge/-Email-e9a?style=for-the-badge&logo=gmail&logoColor=E94D5F)](mailto:diogooikejapan@gmail.com)
