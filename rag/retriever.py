"""RAG 检索器：向量相似度 + BM25 关键词混合检索，RRF 融合排序。"""
from dataclasses import dataclass
from typing import Optional

import jieba
from rank_bm25 import BM25Okapi


@dataclass
class SearchResult:
    """单个检索结果的数据结构。"""
    text: str
    source: str
    title: str
    date: str = ""
    score: float = 0.0
    chunk_id: str = ""


class Retriever:
    """混合检索器：ChromaDB 向量检索 + BM25 关键词检索，RRF 融合。

    Args:
        collection: ChromaDB Collection 实例。
        bm25_weight: BM25 得分在融合中的权重 (0-1)，默认 0.3。
    """

    def __init__(self, collection, bm25_weight: float = 0.3):
        self.collection = collection
        self.bm25_weight = bm25_weight
        self._build_bm25()

    def _build_bm25(self):
        """从 collection 拉取全部文档，构建 BM25 索引。"""
        all_docs = self.collection.get()
        self._documents: list[str] = all_docs.get("documents", [])
        self._metadatas: list[dict] = all_docs.get("metadatas", [])
        self._ids: list[str] = all_docs.get("ids", [])

        if self._documents:
            tokenized = [list(jieba.cut(doc)) for doc in self._documents]
            self._bm25: Optional[BM25Okapi] = BM25Okapi(tokenized)
        else:
            self._bm25 = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """执行混合检索。

        1. ChromaDB 向量检索 top-10
        2. BM25 关键词检索 top-5
        3. RRF 融合排序
        4. 返回 top_k 结果

        Args:
            query: 用户查询字符串。
            top_k: 返回结果数量。

        Returns:
            list[SearchResult]: 按得分降序排列的检索结果。
        """
        n_docs = len(self._documents)
        if n_docs == 0:
            return []

        # 1. 向量检索 (top-10)
        n_vector = min(10, n_docs)
        vr = self.collection.query(query_texts=[query], n_results=n_vector)

        v_scores: dict[str, float] = {}
        for idx, cid in enumerate(vr["ids"][0]):
            dist = vr.get("distances", [[0]])[0][idx]
            v_scores[cid] = 1.0 / (1.0 + dist) if dist else 1.0

        # 2. BM25 关键词检索 (top-5)
        b_scores: dict[str, float] = {}
        if self._bm25:
            query_tokens = list(jieba.cut(query))
            scores = self._bm25.get_scores(query_tokens)
            # 取 BM25 得分最高的 top-5
            n_bm25 = min(5, len(scores))
            top_idx = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:n_bm25]
            max_score = max(scores) if scores and max(scores) > 0 else 1.0
            for idx in top_idx:
                b_scores[self._ids[idx]] = scores[idx] / max_score

        # 3. RRF 融合（加权线性融合）
        combined: dict[str, float] = {}
        all_cids = set(v_scores.keys()) | set(b_scores.keys())
        for cid in all_cids:
            v = v_scores.get(cid, 0.0)
            b = b_scores.get(cid, 0.0)
            combined[cid] = v * (1.0 - self.bm25_weight) + b * self.bm25_weight

        # 按融合得分降序排序，取 top_k
        sorted_ids = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 构建 id -> index 映射
        id_idx = {cid: i for i, cid in enumerate(self._ids)}

        results: list[SearchResult] = []
        for cid, score in sorted_ids:
            if cid not in id_idx:
                continue
            pos = id_idx[cid]
            meta = self._metadatas[pos] if pos < len(self._metadatas) else {}
            results.append(
                SearchResult(
                    text=self._documents[pos],
                    source=meta.get("source", ""),
                    title=meta.get("title", ""),
                    date=meta.get("date", ""),
                    score=round(score, 4),
                    chunk_id=cid,
                )
            )

        return results
