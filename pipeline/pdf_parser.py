"""PDF 解析：从毛选/文集PDF中提取结构化文本。

输出格式：
{
    "source": "毛泽东选集 第一卷",
    "title": "实践论",
    "date": "1937年7月",
    "content": "马克思以前的唯物论..."
}
"""
import fitz  # pymupdf
import os
import json
import re


def extract_articles(pdf_path: str) -> list[dict]:
    """从单个PDF中提取所有文章。

    解析策略：
    1. 先用pdf目录/书签识别篇目边界（如果PDF有书签）
    2. 无书签时，通过大标题模式（如 "实践论" 前后空行）识别篇目
    3. 每篇的 title 和 date 从标题行及上下文推断
    """
    doc = fitz.open(pdf_path)
    articles = []

    # 尝试从文件名推断 source
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    source = basename  # 如 "毛泽东选集_第一卷"

    toc = doc.get_toc()

    if toc and len(toc) > 1:
        # 有书签：按书签切分
        for i, entry in enumerate(toc):
            level, title, page = entry
            if level == 1:
                continue  # 跳过卷级书签

            start_page = page - 1  # fitz 页码从1开始
            end_page = toc[i + 1][2] - 1 if i + 1 < len(toc) else doc.page_count

            text_parts = []
            for p in range(start_page, end_page + 1):
                text_parts.append(doc[p].get_text())

            content = "\n".join(text_parts)
            title_clean, date = _parse_title_and_date(title)

            articles.append({
                "source": source,
                "title": title_clean,
                "date": date,
                "content": content.strip()
            })
    else:
        # 无书签：全量提取后按标记分篇
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        articles = _split_by_heading_patterns(full_text, source)

    doc.close()
    return articles


def _parse_title_and_date(raw_title: str) -> tuple[str, str]:
    """从标题行解析篇名和日期。

    如 "实践论（一九三七年七月）" → ("实践论", "1937年7月")
    如 "反对本本主义" → ("反对本本主义", "")
    """
    date = ""
    title = raw_title.strip()
    date_match = re.search(r'[（(](.{4,20})[）)]\s*$', title)
    if date_match:
        date = date_match.group(1)
        title = title[:date_match.start()].strip()
    return title, date


def _split_by_heading_patterns(full_text: str, source: str) -> list[dict]:
    """当PDF无书签时，通过标题特征切分文章。

    识别特征：
    - 行首有 "（一）（二）..." 或 "一、二、三..." 这种结构标记 → 篇目分隔符
    - 短行（<80字符）且含括号日期 → 篇目标题（如 "实践论（一九三七年七月）"）
    - 短行（<80字符）前后有空行 → 可能是篇目标题
    """
    lines = full_text.split("\n")
    articles = []
    current_title = ""
    current_date = ""
    current_lines = []

    # 匹配篇目分隔符： （一）（二）... 或 一、二、三...
    heading_pattern = re.compile(
        r'^(?:[（(][一二三四五六七八九十]+[）)]|[一二三四五六七八九十]+[、.])'
    )

    def _flush_article():
        """将当前积累的内容保存为一篇文章并重置。"""
        nonlocal current_title, current_date, current_lines
        if not current_lines and not current_title:
            return
        title = current_title or source
        content = "\n".join(current_lines).strip()
        if content:
            articles.append({
                "source": source,
                "title": title,
                "date": current_date,
                "content": content
            })
        current_title = ""
        current_date = ""
        current_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            current_lines.append(line)
            continue

        # 检测当前行是否为篇目标题行
        is_title = False

        # 条件1：匹配 （一）（二）... 或 一、二、三... 格式 → 篇目分隔符
        if heading_pattern.match(stripped):
            is_title = True
        # 条件2：短行（<80字符）且含括号日期
        elif len(stripped) < 80 and re.search(r'[（(].{4,20}[）)]', stripped):
            is_title = True
        # 条件3：短行（<80字符）且前后都是空行 → 独立标题
        elif len(stripped) < 80 and (i == 0 or not lines[i - 1].strip()) and (i == len(lines) - 1 or not lines[i + 1].strip()):
            is_title = True

        if is_title:
            _flush_article()
            current_title, current_date = _parse_title_and_date(stripped)
        else:
            current_lines.append(line)

    # 保存最后一篇文章
    _flush_article()

    return articles


def save_extracted(articles: list[dict], output_dir: str):
    """将解析结果保存为 JSON 文件，按 source 分目录。"""
    from collections import defaultdict

    by_source = defaultdict(list)
    for art in articles:
        by_source[art["source"]].append(art)

    for source, arts in by_source.items():
        safe_name = source.replace(" ", "_").replace("/", "_")
        dir_path = os.path.join(output_dir, safe_name)
        os.makedirs(dir_path, exist_ok=True)

        for i, art in enumerate(arts):
            fname = f"{i:03d}_{art['title']}.json"
            fname = re.sub(r'[\\/*?:"<>|]', '_', fname)
            filepath = os.path.join(dir_path, fname)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(art, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(articles)} articles to {output_dir}")
