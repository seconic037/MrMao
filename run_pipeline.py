"""一键运行离线数据处理管道：TXT解析 → 分块 → 向量化入库

步骤：
1. TXT 文本解析 (pipeline/txt_parser.py) — 从 data/txt/ 提取结构化文章
2. book-to-skill 知识萃取 (交互式)
3. 文本分块 (pipeline/chunker.py)
4. 向量化入库 (pipeline/embed_and_store.py)

用法：python run_pipeline.py
"""
import sys
import os
import json
import glob
import time
from dotenv import load_dotenv

load_dotenv()


def main():
    print("=" * 60)
    print("  毛选思维引擎 — 离线数据处理管道")
    print("=" * 60)

    # ── Step 1: TXT 解析 ──────────────────────────
    print("\n[1/4] TXT 文本解析...")
    from pipeline.txt_parser import extract_all, save_extracted

    txt_dir = "data/txt"
    fulltext_files = glob.glob(f"{txt_dir}/**/*_全文.txt", recursive=True)
    if not fulltext_files:
        print(f"  ⚠️  {txt_dir}/ 中没有找到 _全文.txt 文件")
        print(f"  请将毛选 TXT 文件放入 {txt_dir}/ 后重试")
        sys.exit(1)

    t0 = time.time()
    all_articles = extract_all(txt_dir)
    save_extracted(all_articles, "data/extracted")
    print(f"  共提取 {len(all_articles)} 篇 (耗时 {time.time()-t0:.1f}s)")

    # ── Step 2: book-to-skill 知识萃取 ─────────────
    kb_path = "knowledge/maozedong-knowledge-base.md"
    if os.path.exists(kb_path) and os.path.getsize(kb_path) > 500:
        print(f"\n[2/4] book-to-skill 知识萃取: 已就绪 ({kb_path})")
    else:
        print("\n[2/4] book-to-skill 知识萃取: ⚠️  知识库尚未生成")
        print("  在 Reasonix 中运行: /book-to-skill data/extracted/")
        print("  手动将萃取结果保存到 knowledge/maozedong-knowledge-base.md")

    # ── Step 3: 文本分块 ──────────────────────────
    print("\n[3/4] 文本分块...")
    from pipeline.chunker import chunk_articles, save_chunks

    t0 = time.time()
    chunks = chunk_articles(all_articles, chunk_size=800, overlap=80)
    save_chunks(chunks, "data/extracted/chunks.jsonl")
    print(f"  共产生 {len(chunks)} 个文本块 (耗时 {time.time()-t0:.1f}s)")

    # ── Step 4: 向量化入库 ──────────────────────────
    print("\n[4/4] 向量化入库...")
    from pipeline.embed_and_store import embed_and_store

    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    print(f"  嵌入模型: {model_name}")
    print(f"  首次运行将下载模型 (~400MB)，请耐心等待...")

    t0 = time.time()
    collection = embed_and_store(
        chunks,
        collection_name="maozedong-works",
        persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"),
        model_name=model_name,
        batch_size=100
    )
    elapsed = time.time() - t0
    print(f"  入库完成: {collection.count()} 条记录 (耗时 {elapsed:.1f}s)")

    # ── 完成 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  管道完成！")
    print(f"    - 文章: {len(all_articles)} 篇")
    print(f"    - 文本块: {len(chunks)} 个")
    print(f"  启动服务: python run_server.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
