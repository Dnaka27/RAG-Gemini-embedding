import time

from google.genai import types
from google.genai.errors import APIError

from .config import EMBEDDING_DIM, EMBEDDING_MODEL


def embed_text(client, text, task="document", max_retries=5):
    """Gera o embedding de um único texto.

    gemini-embedding-2 não usa mais o parâmetro `task_type`: a instrução de
    tarefa vai embutida no próprio texto de entrada. Chamamos o modelo com
    UM texto por vez (nunca uma lista) porque, ao contrário do
    gemini-embedding-001, uma lista de `contents` é agregada em um único
    embedding combinado, em vez de gerar um embedding por item.
    """
    prefix = "task: search query\nquery: " if task == "query" else "task: search document\ntext: "
    formatted = f"{prefix}{text}"

    for attempt in range(max_retries):
        try:
            resp = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=formatted,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
            )
            return resp.embeddings[0].values
        except APIError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
