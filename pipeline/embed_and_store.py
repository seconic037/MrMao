"""向量化与ChromaDB入库。离线模式，不访问 HuggingFace。"""
import os, json, time
import chromadb
from sentence_transformers import SentenceTransformer


def _load_model(model_name: str):
    """加载本地嵌入模型（离线）。"""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    return SentenceTransformer(model_name, local_files_only=True)


class _LocalEmbeddingFn:
    """将 sentence-transformers 模型包装为 ChromaDB 兼容的嵌入函数。"""
    def __init__(self, model_name: str):
        self._model = _load_model(model_name)
        self._name = model_name
    def __call__(self, input: list[str]) -> list[list[float]]:
        return self._model.encode(input, normalize_embeddings=True).tolist()
    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self._model.encode(input, normalize_embeddings=True).tolist()
    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self._model.encode(input, normalize_embeddings=True).tolist()
    def name(self):
        return self._name


def embed_and_store(chunks, collection_name="maozedong-works", persist_dir="./data/chroma_v3",
                    model_name="BAAI/bge-small-zh-v1.5", batch_size=100):
    print(f"Loading embedding model: {model_name}")
    emb_fn = _LocalEmbeddingFn(model_name)

    client = chromadb.PersistentClient(path=persist_dir)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(name=collection_name, embedding_function=emb_fn,
                                          metadata={"hnsw:space": "cosine"})

    total = len(chunks)
    print(f"Embedding and storing {total} chunks...")
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        ids = [ch["id"] for ch in batch]
        texts = [ch["text"] for ch in batch]
        metadatas = [{"source": ch["source"], "title": ch["title"],
                      "date": ch.get("date", ""), "chunk_index": ch.get("chunk_index", i)} for ch in batch]
        collection.add(ids=ids, documents=texts, metadatas=metadatas)
        print(f"  Progress: {min(i + batch_size, total)}/{total}")
    print(f"Stored {collection.count()} documents in '{collection_name}'")
    return collection


def load_collection(persist_dir="./data/chroma_v3", collection_name="maozedong-works",
                    model_name="BAAI/bge-small-zh-v1.5") -> chromadb.Collection:
    emb_fn = _LocalEmbeddingFn(model_name)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_collection(name=collection_name, embedding_function=emb_fn)
