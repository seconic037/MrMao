"""向量化与ChromaDB入库。

流程：
1. 加载 sentence-transformers 嵌入模型（BAAI/bge-small-zh-v1.5）
2. 对每个 chunk.text 生成向量
3. 存入 ChromaDB collection，附带元数据
"""
import chromadb
from chromadb.utils import embedding_functions
import json
import os
import time


def create_embedding_fn(model_name: str):
    """创建嵌入函数。优先使用 sentence-transformers 本地模型。"""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name
    )


def embed_and_store(
    chunks: list[dict],
    collection_name: str = "maozedong-works",
    persist_dir: str = "./data/chroma_db",
    model_name: str = "BAAI/bge-small-zh-v1.5",
    batch_size: int = 100
):
    """将文本块向量化后存入 ChromaDB。
    
    Args:
        chunks: 文本块列表，每块含 id, text, source, title, date
        collection_name: ChromaDB collection 名称
        persist_dir: ChromaDB 持久化目录
        model_name: sentence-transformers 模型名
        batch_size: 批处理大小
    
    Returns:
        chromadb.Collection
    """
    print(f"Loading embedding model: {model_name}")
    emb_fn = create_embedding_fn(model_name)
    
    client = chromadb.PersistentClient(path=persist_dir)
    
    # 如果 collection 已存在，删除重建（幂等管道）
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"}
    )
    
    total = len(chunks)
    print(f"Embedding and storing {total} chunks...")
    
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        ids = [ch["id"] for ch in batch]
        texts = [ch["text"] for ch in batch]
        metadatas = [
            {
                "source": ch["source"],
                "title": ch["title"],
                "date": ch.get("date", ""),
                "chunk_index": ch.get("chunk_index", i)
            }
            for ch in batch
        ]
        
        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
        
        progress = min(i + batch_size, total)
        print(f"  Progress: {progress}/{total}")
    
    print(f"Stored {collection.count()} documents in '{collection_name}'")
    return collection


def load_collection(
    persist_dir: str = "./data/chroma_db",
    collection_name: str = "maozedong-works",
    model_name: str = "BAAI/bge-small-zh-v1.5"
) -> chromadb.Collection:
    """加载已有的 ChromaDB collection（在线服务用）。"""
    emb_fn = create_embedding_fn(model_name)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_collection(
        name=collection_name,
        embedding_function=emb_fn
    )
