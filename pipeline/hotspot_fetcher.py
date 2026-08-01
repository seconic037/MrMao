"""百度热搜实时抓取 + 娱乐新闻过滤"""
import subprocess, json, time, os, tempfile

ENTERTAINMENT_KEYWORDS = [
    "综艺", "明星", "八卦", "恋情", "绯闻", "出道",
    "瘦到骨头", "造型", "最让人上", "有何不同",
    "导演：没想", "爆笑出圈", "多了个爹",
    "何广智回应", "孙珍妮", "窦靖童", "两版尹新月",
]

def fetch_baidu_hotspots(limit: int = 15) -> dict:
    """抓取百度热搜，过滤娱乐类。"""
    try:
        tmp = os.path.join(tempfile.gettempdir(), "baidu_hot.json")
        subprocess.run(["curl", "-s",
            "https://top.baidu.com/api/board?platform=wise&tab=realtime",
            "-o", tmp], timeout=10, check=True)
        with open(tmp, "r", encoding="utf-8") as f:
            data = json.load(f)
        cards = data.get("data", {}).get("cards", [])
        if not cards:
            raise ValueError("no cards")
        raw_list = cards[0].get("content", [{}])[0].get("content", [])
        items = []
        for item in raw_list:
            if len(items) >= limit:
                break
            title = item.get("word", "")
            if any(kw in title for kw in ENTERTAINMENT_KEYWORDS):
                continue
            tag = "置顶" if item.get("isTop") else (item.get("newHotName") or "")
            items.append({
                "title": title,
                "tag": tag,
                "rank": item.get("index", 0),
                "url": item.get("url", ""),
            })
        return {"time": time.strftime("%m/%d %H:%M"), "source": "百度热搜", "items": items}
    except Exception as e:
        return {"time": time.strftime("%m/%d %H:%M"), "source": "百度热搜", "items": [], "error": str(e)}
