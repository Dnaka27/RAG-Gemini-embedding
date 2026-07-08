import chromadb

from .config import COLLECTION_NAME, PERSIST_DIR


def get_collection(persist_dir=PERSIST_DIR, name=COLLECTION_NAME):
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name=name)


def reset_collection(persist_dir=PERSIST_DIR, name=COLLECTION_NAME):
    """Recria a collection do zero (usado ao reprocessar um documento)."""
    client = chromadb.PersistentClient(path=persist_dir)
    if name in {c.name for c in client.list_collections()}:
        client.delete_collection(name=name)
    return client.get_or_create_collection(name=name)


def add_chunks(collection, chunks, embeddings):
    ids = [f"chunk-{i}" for i in range(len(chunks))]
    collection.add(ids=ids, documents=chunks, embeddings=embeddings)


def retrieve(collection, query_embedding, top_k=5):
    """Busca os chunks mais próximos e retorna texto + distância de cada um."""
    result = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return [
        {"text": text, "distance": distance}
        for text, distance in zip(result["documents"][0], result["distances"][0])
    ]
