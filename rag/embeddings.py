import time

from google.genai import types
from google.genai.errors import APIError

from .config import EMBEDDING_DIM, EMBEDDING_MODEL


def embed_text(client, text, task="document", max_retries=5):
    """Generates the embedding for a single text.

    gemini-embedding-2 no longer uses the `task_type` parameter: the task
    instruction is embedded directly in the input text. We call the model
    with ONE text at a time (never a list) because, unlike
    gemini-embedding-001, a list of `contents` is aggregated into a single
    combined embedding, instead of producing one embedding per item.
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
