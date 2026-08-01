#!/usr/bin/env python
"""新知识自动归类工具
用法: python tools/ingest_knowledge.py

扫描 新知识放这里/ 目录:
  - .txt 文件 → data/txt/知识扩展/（语料库，需重跑管道）
  - .md 文件 → knowledge/framework/（框架层，按主题合并或新建）

处理完成后打印当前知识库架构。
"""
import os, shutil, sys
from pathlib import Path

# Windows 控制台默认 GBK，无法输出 emoji；强制 UTF-8 避免 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
INBOX = ROOT / "新知识放这里"
TXT_DIR = ROOT / "data" / "txt" / "知识扩展"
MD_DIR = ROOT / "knowledge" / "framework"
ARCHIVE = ROOT / "新知识放这里" / "_已处理"

TXT_DIR.mkdir(parents=True, exist_ok=True)
MD_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE.mkdir(parents=True, exist_ok=True)

# 主题分类关键词（题材为书籍等大型内容，直接存放为txt，无需分类）
TOPIC_RULES = {
    "经济学": ["经济", "资本", "市场", "贸易", "货币", "金融", "马歇尔", "斯密", "费特"],
    "哲学": ["哲学", "思维", "逻辑", "辩证", "形而上学"],
    "历史": ["历史", "史", "朝代", "战争", "革命", "党史"],
    "兵法战略": ["兵法", "战略", "三十六计", "孙子"],
    "文学": ["文学", "诗", "词", "小说", "名著"],
    "科学": ["科学", "数学", "物理", "化学", "生物", "统计"],
}

# 非知识文件，不参与归类（README 是目录说明；NPC知识库情况.md 是服务启动自动生成的查看文件）
AUTO_GENERATED = {"NPC知识库情况.md", "README.md"}

def classify_md(filename: str) -> str:
    """根据文件名推断主题，返回目标文件名。"""
    basename = os.path.splitext(filename)[0]
    for topic, keywords in TOPIC_RULES.items():
        for kw in keywords:
            if kw in basename:
                return f"{topic}.md"
    # 默认用原文件名
    return basename + ".md"

def print_structure():
    """打印当前知识库架构。"""
    print("\n" + "="*60)
    print("  📚 MrMao 知识库架构")
    print("="*60)
    
    # 框架层
    fw_files = sorted(MD_DIR.glob("*.md"))
    print(f"\n🧠 思维框架层 (knowledge/framework/) — {len(fw_files)} 个")
    print("   每轮对话注入 think prompt，提供方法论和概念框架")
    for f in fw_files:
        size = f.stat().st_size
        print(f"   ├─ {f.name} ({size//1024}KB)")
    
    # 语料层
    txt_files = sorted(TXT_DIR.glob("*.txt"))
    total_size = sum(f.stat().st_size for f in txt_files)
    print(f"\n📖 语料库层 (data/txt/知识扩展/) — {len(txt_files)} 个")
    print(f"   总大小: {total_size//1024//1024}MB，RAG 检索按需召回")
    # 按主题分组显示
    topics = {}
    for f in txt_files:
        name = f.stem.replace("_plus","").replace("PLUS","").replace("_BTS","")
        for t, kws in TOPIC_RULES.items():
            if any(kw in name for kw in kws):
                topics.setdefault(t, []).append(f.name)
                break
        else:
            topics.setdefault("其他", []).append(f.name)
    for t, files in sorted(topics.items()):
        print(f"   [{t}] {len(files)} 个")
        for fn in files[:3]:
            print(f"      · {fn[:40]}")
        if len(files) > 3:
            print(f"      · ... 等 {len(files)} 个")
    
    print(f"\n📥 待处理: 新知识放这里/ ({len(list(INBOX.glob('*.txt')))+len(list(INBOX.glob('*.md')))} 个文件)")
    print("   运行 python tools/ingest_knowledge.py 自动归类\n")

def main():
    txts = [f for f in INBOX.glob("*.txt") if f.name not in AUTO_GENERATED]
    mds = [f for f in INBOX.glob("*.md") if f.name not in AUTO_GENERATED]
    
    if not txts and not mds:
        print("📭 新知识放这里/ 没有待处理文件")
        print_structure()
        return
    
    for f in txts:
        dest = TXT_DIR / f.name
        shutil.copy2(f, dest)
        shutil.move(str(f), str(ARCHIVE / f.name))
        print(f"  📖 TXT → data/txt/知识扩展/{f.name}")
    
    for f in mds:
        target_name = classify_md(f.name)
        dest = MD_DIR / target_name
        if dest.exists():
            # 追加合并
            with open(dest, "a", encoding="utf-8") as df:
                df.write("\n\n---\n")
                df.write(f.read_text(encoding="utf-8"))
            print(f"  🧠 MD → 合并到 knowledge/framework/{target_name}")
        else:
            shutil.copy2(f, dest)
            print(f"  🧠 MD → 新建 knowledge/framework/{target_name}")
        shutil.move(str(f), str(ARCHIVE / f.name))
    
    print("\n✅ 归类完成！")
    if txts:
        print("⚠️  有 TXT 文件入库，请运行 python run_pipeline.py 重建向量索引")
    print_structure()
    # 返回处理情况：0=无新文件，1=仅 MD，2=含 TXT
    if txts:
        return 2
    if mds:
        return 1
    return 0

if __name__ == "__main__":
    code = main()
    sys.exit(code)
