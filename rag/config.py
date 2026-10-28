EMBEDDING_MODEL = "gemini-embedding-2"
GENERATION_MODEL = "gemini-3.5-flash"
EMBEDDING_DIM = 768  # Matryoshka-truncated: 768 / 1536 / 3072 recommended by Google
MAX_TEXT_CHARS = 400_000  # extracted text, checked before chunking (a small PDF can inflate a lot)
MAX_CHUNKS = 150  # one paid embedding call per chunk, made sequentially
