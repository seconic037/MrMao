"""生成 NPC 当前所用知识库的情况文件（markdown）。

从已加载的 ChromaDB collection 拉取元数据，统计来源分布并写入
`新知识放这里/NPC知识库情况.md`。服务启动时由 web/app.py 调用。
"""
import os
import json
from collections import Counter
from datetime import datetime


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "新知识放这里")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "NPC知识库情况.md")


def generate_knowledge_usage(collection, model_name: str = "BAAI/bge-small-zh-v1.5",
                             persist_dir: str = "") -> str:
    """从 collection 生成知识库情况 markdown，返回文件路径。

    collection: 已加载的 ChromaDB collection（须支持 get(include=['metadatas']))
    """
    metas = collection.get(include=["metadatas"])["metadatas"]
    total = len(metas)

    # 来源分布（source 字段）
    src_counter = Counter(m.get("source", "未知") for m in metas)

    # 知识扩展内部细分（source=知识扩展 时按 title 统计）
    ext_counter = Counter(
        m.get("title", "未知") for m in metas if m.get("source") == "知识扩展"
    )

    # 语料量估算：每块 ~800 字（chunker 默认 chunk_size=800）
    est_chars = total * 800

    lines = []
    lines.append("# 🧠 NPC 当前知识库情况")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **总块数（文档数）**：{total}")
    lines.append(f"- **预估语料量**：约 {est_chars/10000:.0f} 万字")
    lines.append(f"- **向量库路径**：`{persist_dir or 'data/chroma_v3'}`")
    lines.append(f"- **Collection**：`{getattr(collection, 'name', 'maozedong-works')}`")
    lines.append(f"- **嵌入模型**：`{model_name}`")
    lines.append("")
    lines.append("## 来源分布")
    lines.append("")
    lines.append("| 来源 | 块数 | 占比 |")
    lines.append("|------|-----:|-----:|")
    for src, cnt in src_counter.most_common():
        pct = cnt / total * 100 if total else 0
        lines.append(f"| {src} | {cnt} | {pct:.1f}% |")
    lines.append("")
    lines.append("## 知识扩展细分")
    lines.append("")
    lines.append("| 条目 | 块数 |")
    lines.append("|------|-----:|")
    for title, cnt in ext_counter.most_common():
        lines.append(f"| {title} | {cnt} |")
    lines.append("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[knowledge_usage] 已生成: {OUTPUT_FILE} ({total} docs)")
    return OUTPUT_FILE
