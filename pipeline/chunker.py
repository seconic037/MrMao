"""文本分块：将文章按语义边界切分为适合嵌入的段落块。

策略：
- 以「篇」为天然边界，不跨篇
- 篇内按自然段落(\n\n)分割
- 单段过长(>chunk_size)时按句子边界切分
- 相邻块重叠 overlap 字符
"""
import re
import json
import os


def chunk_articles(
    articles: list[dict],
    chunk_size: int = 800,
    overlap: int = 80
) -> list[dict]:
    """将文章列表切分为文本块，每个块附带元数据。"""
    chunks = []
    
    for art in articles:
        source = art["source"]
        title = art["title"]
        date = art.get("date", "")
        content = art["content"]
        
        paragraphs = _split_paragraphs(content)
        article_chunks = _chunk_paragraphs(
            paragraphs, chunk_size, overlap,
            source, title, date
        )
        chunks.extend(article_chunks)
    
    # 统一生成 chunk id
    for i, ch in enumerate(chunks):
        ch["id"] = f"mz_{i:05d}"
        ch["chunk_index"] = i
    
    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """按双换行分割段落，过滤空段。"""
    raw = re.split(r'\n\s*\n', text)
    return [p.strip() for p in raw if p.strip()]


def _chunk_paragraphs(
    paragraphs: list[str],
    chunk_size: int,
    overlap: int,
    source: str,
    title: str,
    date: str
) -> list[dict]:
    """将段落序列组装为 chunk_size 附近的文本块。"""
    chunks = []
    buffer = ""
    
    for para in paragraphs:
        if len(buffer) + len(para) <= chunk_size:
            buffer += para + "\n\n"
        else:
            # 当前 buffer 满了，存为一个chunk
            if buffer.strip():
                chunks.append({
                    "text": buffer.strip(),
                    "source": source,
                    "title": title,
                    "date": date,
                })
                # 下一块：前一块末尾 overlap 字符
                overlap_text = buffer[-overlap:] if len(buffer) > overlap else buffer
                buffer = overlap_text + para + "\n\n"
            else:
                # 单段落就超过 chunk_size，递归按句号切割
                sentences = re.split(r'(?<=[。！？])', para)
                for sent in sentences:
                    if not sent.strip():
                        continue
                    # 超长句子按 chunk_size 切分
                    if len(sent) > chunk_size:
                        if buffer.strip():
                            chunks.append({
                                "text": buffer.strip(),
                                "source": source,
                                "title": title,
                                "date": date,
                            })
                            buffer = ""
                        start = 0
                        while start < len(sent):
                            end = min(start + chunk_size, len(sent))
                            piece = sent[start:end]
                            chunks.append({
                                "text": piece,
                                "source": source,
                                "title": title,
                                "date": date,
                            })
                            if end >= len(sent):
                                break
                            start = end - overlap
                        buffer = sent[-overlap:] if len(sent) > overlap else sent
                        continue

                    if len(buffer) + len(sent) <= chunk_size:
                        buffer += sent
                    else:
                        if buffer.strip():
                            chunks.append({
                                "text": buffer.strip(),
                                "source": source,
                                "title": title,
                                "date": date,
                            })
                        # 句子分支：从前一块末尾取 overlap 字符
                        overlap_text = buffer[-overlap:] if len(buffer) > overlap else buffer
                        buffer = overlap_text + sent
    
    # 最后一个不满的块
    if buffer.strip():
        chunks.append({
            "text": buffer.strip(),
            "source": source,
            "title": title,
            "date": date,
        })
    return chunks


def save_chunks(chunks: list[dict], output_path: str):
    """保存分块结果到 JSONL 文件。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + '\n')
    print(f"Saved {len(chunks)} chunks to {output_path}")
