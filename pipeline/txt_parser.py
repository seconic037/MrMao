"""TXT 解析：从毛选/文集 TXT 全文文件中提取结构化文本。

输入：data/txt/ 下的 *_全文.txt 文件（毛选四卷）
附加：毛泽东诗词全集132首.txt

输出格式（与 pdf_parser 相同）：
{
    "source": "毛选第一卷",
    "title": "中国社会各阶级的分析",
    "date": "一九二五年十二月一日",
    "content": "..."
}
"""
import os
import json
import re
import glob


def extract_from_fulltext(txt_path: str) -> list[dict]:
    """从 _全文.txt 文件中提取所有文章。

    解析策略：
    1. 识别文章标题 + 日期行的模式：title → blank → (date)
    2. 以「篇」为边界，日期行是确切的边界信号
    3. 章节标题（如"第一次国内革命战争时期"）作为上下文但不单独成篇
    """
    source = _infer_source(txt_path)

    with open(txt_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    lines = full_text.split('\n')
    articles = []
    current_section = ""
    current_title = ""
    current_date = ""
    current_content_lines = []
    in_footnotes = False

    # 日期行模式：全角括号+年月日
    date_pattern = re.compile(r'^[（(].*?年.*?月.*?日[）)]\s*$')

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测脚注开始（大量的 〔1〕〔2〕 标记）
        if re.match(r'^〔\d+〕', stripped):
            in_footnotes = True
            continue
        if in_footnotes:
            if re.match(r'^〔\d+〕', stripped) or stripped == '':
                continue
            else:
                in_footnotes = False

        # 检测日期行 → 新文章边界
        if date_pattern.match(stripped):
            # 保存上一篇
            if current_title and current_content_lines:
                articles.append(_make_article(
                    source, current_title, current_date,
                    current_content_lines, current_section
                ))

            # 提取日期，找上一非空行作为标题
            current_date = stripped.strip('（）()')
            current_content_lines = []

            # 向前找标题（跳过空行）
            title_line = ""
            for j in range(i - 1, max(i - 4, 0), -1):
                prev = lines[j].strip()
                if prev and not date_pattern.match(prev):
                    title_line = prev
                    break
            current_title = title_line

            in_footnotes = False
            continue

        # 检测章节标题（如 "第一次国内革命战争时期"、"抗日战争时期（上）"）
        if _is_section_header(stripped, lines, i):
            current_section = stripped
            continue

        # 累积正文
        if current_title:
            current_content_lines.append(line)

    # 最后一篇
    if current_title and current_content_lines:
        articles.append(_make_article(
            source, current_title, current_date,
            current_content_lines, current_section
        ))

    return articles


def extract_poems(poem_path: str) -> list[dict]:
    """从毛泽东诗词全集中提取每首诗词。

    诗词格式：
    诗词名·写作时间
    正文
    空行分隔
    """
    with open(poem_path, 'r', encoding='utf-8') as f:
        content = f.read()

    poems = []
    # 匹配 "词牌名·标题 时间" 模式
    poem_pattern = re.compile(
        r'^(.+?[·‧](.+?))\s*(（?[\d零一二三四五六七八九十百千万]+年[\d零一二三四五六七八九十百千万]+月）?)?\s*$',
        re.MULTILINE
    )

    # 按空行分首
    blocks = re.split(r'\n\s*\n', content)
    current_title = ""
    current_date = ""

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        first_line = lines[0].strip()

        # 检查是否是标题行
        m = poem_pattern.match(first_line)
        if m:
            current_title = m.group(1)
            current_date = m.group(3) or ""
            # 正文是剩余行
            body = '\n'.join(lines[1:]).strip()
            if body:
                poems.append({
                    "source": "毛泽东诗词",
                    "title": current_title,
                    "date": current_date,
                    "content": body
                })

    return poems


def _infer_source(txt_path: str) -> str:
    """从文件路径推断来源。"""
    basename = os.path.basename(txt_path)
    # "毛选第一卷_全文.txt" → "毛选第一卷"
    source = basename.replace('_全文.txt', '').replace('.txt', '')
    return source


def _is_section_header(line: str, lines: list[str], idx: int) -> bool:
    """判断是否是章节标题。"""
    if not line or len(line) > 30:
        return False
    # 章节标题常见模式：时期、战争阶段等
    section_keywords = [
        '时期', '战争', '阶段', '革命', '运动',
        '抗日', '国内', '第二次', '第三次', '第一次'
    ]
    if any(kw in line for kw in section_keywords):
        # 不是日期行、不是文章标题
        if re.match(r'^[（(]', line):
            return False
        # 前后有空行
        prev_empty = idx == 0 or not lines[idx-1].strip()
        next_empty = idx == len(lines)-1 or not lines[idx+1].strip()
        return prev_empty or next_empty
    return False


def _make_article(source, title, date, content_lines, section) -> dict:
    """构建文章字典。"""
    content = '\n'.join(content_lines).strip()
    # 清理内容：移除脚注标记残留
    content = re.sub(r'〔\d+〕', '', content)
    # 合并多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 在标题中加入章节上下文（如果章节信息有用）
    full_title = title
    if section and section not in title:
        pass  # 保留原始标题，不强行拼接

    return {
        "source": source,
        "title": full_title,
        "date": date,
        "content": content
    }


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
            fname = f"{i:03d}_{art['title'][:30]}.json"
            fname = re.sub(r'[\\/*?:"<>|]', '_', fname)
            filepath = os.path.join(dir_path, fname)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(art, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(articles)} articles to {output_dir}")


def extract_all(input_dir: str = "data/txt") -> list[dict]:
    """从 data/txt/ 目录提取所有文章。

    处理：
    1. 各卷 _全文.txt 文件（主要源）
    2. 毛泽东诗词全集
    """
    all_articles = []

    # 1. 处理毛选四卷全文
    fulltext_files = glob.glob(
        os.path.join(input_dir, "**/*_全文.txt"),
        recursive=True
    )
    fulltext_files += glob.glob(
        os.path.join(input_dir, "**/*_精选.txt"),
        recursive=True
    )
    for ft_path in sorted(fulltext_files):
        print(f"  解析: {ft_path}")
        articles = extract_from_fulltext(ft_path)
        all_articles.extend(articles)
        print(f"    提取 {len(articles)} 篇")

    # 2. 处理诗词
    poem_files = glob.glob(
        os.path.join(input_dir, "**/毛泽东诗词全集*.txt"),
        recursive=True
    )
    for p_path in poem_files:
        print(f"  解析诗词: {p_path}")
        poems = extract_poems(p_path)
        all_articles.extend(poems)
        print(f"    提取 {len(poems)} 首")

    print(f"  共提取 {len(all_articles)} 篇")
    return all_articles
