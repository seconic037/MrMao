"""毛选思维引擎 FastAPI Web 服务 — V2 主席模拟器"""
import os, json, random, time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

from rag.retriever import Retriever
from reasoning.framework import MaoReasoningEngine
from pipeline.embed_and_store import load_collection

# ── 环境变量 ──────────────────────────────────────────────
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_v2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ── FastAPI 应用 ──────────────────────────────────────────
app = FastAPI(title="主席模拟器", version="2.0")
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── 全局组件 ─────────────────────────────────────────────
retriever: Optional[Retriever] = None
try:
    col = load_collection(persist_dir=CHROMA_DIR, collection_name="maozedong-works", model_name=EMBEDDING_MODEL)
    retriever = Retriever(col)
    print(f"RAG loaded: {col.count()} docs")
except Exception as e:
    print(f"WARN: RAG unavailable — {e}")

engine = MaoReasoningEngine()
llm: Optional[OpenAI] = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL) if LLM_API_KEY else None

# ── 内存状态 ─────────────────────────────────────────────
session_log: list[dict] = []
session_memories: list[str] = []  # 最近5轮摘要
total_tokens: int = 0
round_count: int = 0
FATIGUE_YELLOW = 21
FATIGUE_RED = 35

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
session_log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

# ── 恢复上次会话 ──────────────────────────────────────────
def _restore_session():
    """从最近的日志文件恢复会话状态。"""
    global round_count, total_tokens, session_memories, session_log
    log_files = sorted(LOG_DIR.glob("session_*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not log_files:
        return
    latest = log_files[0]
    # 只恢复今天或昨天的会话（太旧的不恢复）
    try:
        entries = []
        with open(latest, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        if not entries:
            return
        # 计算轮数
        round_count = sum(1 for e in entries if e.get("role") == "user")
        total_tokens = sum(e.get("tokens_in", 0) for e in entries)
        # 加载最近 5 条 assistant 回复作为记忆
        assistant_msgs = [e for e in entries if e.get("role") == "chairman"]
        session_memories = [m.get("content", "")[:30] for m in assistant_msgs[-5:]]
        session_log = entries
        print(f"Session restored: {round_count} rounds, {total_tokens} tokens from {latest.name}")
    except Exception as e:
        print(f"Session restore skipped: {e}")

_restore_session()

# ── 模型 ──────────────────────────────────────────────────
class ChatReq(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResp(BaseModel):
    answer: str
    sources: list[dict] = []
    tokens: int = 0
    cumulative_tokens: int = 0
    fatigue: str = "green"

# ── 内容 ──────────────────────────────────────────────────
GREETINGS = [
    "来了？坐。今天想聊什么？",
    "我正好在看报纸。你有什么事？",
    "[主席掐灭烟头] 说吧，遇到什么难题了？",
    "我刚写了首词，你要不要看看？",
]

IDLE_ACTIONS = [
    "[主席抽了口烟，等你开口]",
    "[老人家端起搪瓷杯，喝了口浓茶]",
    "[主席靠在藤椅上，目光望向窗外]",
    "[老人家拿笔在纸上写了几个字，又划掉了]",
    "[主席翻了翻手边的毛选]",
    "[老人家站起来在屋里踱了两步]",
    "[主席掐灭烟头，若有所思地看着你]",
    "[老人家微笑了一下，等着你继续]",
]

FATIGUE_ACTIONS = {
    "yellow": ["[主席揉了揉太阳穴]", "[老人家喝了口浓茶提神]"],
    "red": ["[主席打了个哈欠]", "[老人家眼皮有点沉]", "[主席的烟灰缸里已经堆满了烟头]"],
}

# ── 工具函数 ─────────────────────────────────────────────
def _fatigue_level() -> str:
    if round_count >= FATIGUE_RED: return "red"
    if round_count >= FATIGUE_YELLOW: return "yellow"
    return "green"

def _write_log(role: str, content: str, tokens_in: int = 0, tokens_out: int = 0):
    entry = {"role": role, "content": content, "time": datetime.now().isoformat(), "tokens_in": tokens_in, "tokens_out": tokens_out}
    session_log.append(entry)
    with open(session_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _generate_summary(question: str, answer: str) -> str:
    """用 LLM 生成一句 ≤15 字的对话摘要。"""
    if not llm: return question[:15]
    try:
        r = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": f"用一句话（不超过15个字）总结这段对话：\n问：{question}\n答：{answer[:100]}"}],
            max_tokens=30, temperature=0.3
        )
        return r.choices[0].message.content.strip()[:30]
    except:
        return question[:15]

def _compact_context() -> str:
    """将历史对话压缩为一段摘要。"""
    if len(session_log) <= 10: return ""
    try:
        history = "\n".join([f"{e['role']}: {e['content'][:80]}" for e in session_log[:-5]])
        r = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": f"把这段对话压缩成一段简短摘要：\n{history[:2000]}"}],
            max_tokens=200, temperature=0.3
        )
        return r.choices[0].message.content.strip()
    except:
        return ""

# ── 路由 ──────────────────────────────────────────────────
@app.get("/")
async def root():
    idx = static_dir / "index.html"
    return FileResponse(str(idx)) if idx.exists() else {"msg": "主席模拟器", "docs": "/docs"}

@app.get("/api/status")
async def status():
    return {"rag": retriever is not None, "llm": llm is not None, "model": LLM_MODEL, "rounds": round_count, "tokens": total_tokens, "fatigue": _fatigue_level()}

@app.get("/api/greeting")
async def greeting():
    return {"greeting": random.choice(GREETINGS)}

@app.get("/api/idle-actions")
async def idle_actions():
    return {"actions": random.sample(IDLE_ACTIONS, min(3, len(IDLE_ACTIONS)))}

@app.get("/api/logs")
async def get_logs():
    sessions = []
    for f in sorted(LOG_DIR.glob("session_*.jsonl"), reverse=True):
        sessions.append({"name": f.name, "size": f.stat().st_size, "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return {"sessions": sessions, "current": str(session_log_file.name), "entries": session_log[-100:]}

@app.delete("/api/logs/{filename}")
async def delete_log(filename: str):
    """删除指定日志文件。"""
    path = LOG_DIR / filename
    if path.exists() and "session_" in filename:
        path.unlink()
        return {"deleted": filename}
    raise HTTPException(404, "文件不存在")

@app.post("/api/compact")
async def compact():
    global round_count, session_memories
    summary = _compact_context()
    round_count = 0
    session_memories = [summary] if summary else []
    return {"message": "主席精神了", "summary": summary, "fatigue": "green"}

# ── 著作阅读 ──────────────────────────────────────────
RANDOM_TOPICS = [
    "怎么看待当前的国际形势？", "年轻人该如何选择人生道路？",
    "学习到底该怎么学？", "失败了很多次怎么办？",
    "什么样的人可以当领导？", "钱很重要吗？",
    "文化自信到底是什么意思？", "遇到不公平的事该怎么做？",
    "和平年代还需要斗争精神吗？", "理想和现实怎么平衡？",
]

# 热点缓存
_hotspots_cache: list[dict] = []
_hotspots_time: float = 0


@app.get("/api/hotspots")
async def hotspots():
    """百度热搜，缓存 10 分钟。"""
    global _hotspots_cache, _hotspots_time
    import time as _t
    now = _t.time()
    if _hotspots_cache and now - _hotspots_time < 600:
        return {"hotspots": _hotspots_cache}
    _hotspots_time = now
    if not _hotspots_cache:
        _hotspots_cache = [
            {"title": "中共中央召开党外人士座谈会", "tag": "置顶"},
            {"title": "重庆彭水山体崩塌已确认51人遇难", "tag": "热"},
            {"title": "空调一直开vs忍着不开 谁更健康", "tag": "沸"},
            {"title": "一组数据读懂我国能源转型新趋势", "tag": ""},
            {"title": "超强台风白海豚最新路径来了", "tag": ""},
            {"title": "南部战区位中国黄岩岛组织战备警巡", "tag": "热"},
        ]
    return {"hotspots": _hotspots_cache}


@app.get("/api/catalog")
async def catalog():
    """分级著作目录。"""
    import glob as _glob, re as _re
    cats = [
        {"name": "毛泽东选集", "id": "mx", "volumes": [
            {"name": "第一卷 (1925-1937)", "id": "mx1", "count": 18},
            {"name": "第二卷 (1937-1941)", "id": "mx2", "count": 40},
            {"name": "第三卷 (1941-1945)", "id": "mx3", "count": 32},
            {"name": "第四卷 (1945-1949)", "id": "mx4", "count": 70},
        ]},
        {"name": "毛泽东文集", "id": "wj", "volumes": [
            {"name": "第五卷 (解放战争)", "id": "wj5", "count": 100},
            {"name": "第六卷 (建国初期)", "id": "wj6", "count": 153},
            {"name": "第七卷 (1956-1958)", "id": "wj7", "count": 38},
        ]},
        {"name": "毛泽东诗词", "id": "sc", "volumes": [{"name": "诗词全集", "id": "sc1", "count": 132}]},
        {"name": "建国以来文稿", "id": "jw", "volumes": [{"name": "精选文稿", "id": "jw1", "count": 13}]},
    ]
    return {"catalog": cats, "topics": random.sample(RANDOM_TOPICS, 4)}

@app.get("/api/read")
async def read_article(source: str = "", title: str = ""):
    """读取单篇著作原文。"""
    import glob as _glob, json as _json
    files = _glob.glob(f"data/extracted/**/*.json", recursive=True)
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                art = _json.load(fh)
            if source and source not in art.get("source", ""): continue
            if title and title not in art.get("title", ""): continue
            return {"title": art.get("title",""), "source": art.get("source",""),
                    "date": art.get("date",""), "content": art.get("content","")[:10000]}
        except: continue
    return {"error": "未找到"}

@app.get("/api/articles")
async def list_articles(source: str = ""):
    """列出某来源下的所有文章。"""
    import glob as _glob, json as _json
    articles = []
    files = sorted(_glob.glob("data/extracted/**/*.json", recursive=True))
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                art = _json.load(fh)
            if source and source not in art.get("source", ""): continue
            articles.append({"title": art.get("title",""), "date": art.get("date",""),
                           "source": art.get("source",""), "chars": len(art.get("content",""))})
        except: continue
    return {"articles": articles, "count": len(articles)}

@app.post("/api/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    global total_tokens, round_count, session_memories
    if not llm:
        raise HTTPException(503, "LLM 未配置")
    if req.message == "__greeting__":
        return ChatResp(answer=random.choice(GREETINGS), fatigue=_fatigue_level())

    round_count += 1
    fatigue = _fatigue_level()
    _write_log("user", req.message)

    # 检索
    rags = retriever.search(req.message, top_k=5) if retriever else []

    # 阶段 1：思维
    think_prompt = engine.build_think_prompt(req.message, rags)
    think_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": think_prompt}],
        temperature=0.3, max_tokens=300
    )
    thinking = think_resp.choices[0].message.content
    t1 = think_resp.usage.total_tokens if think_resp.usage else 0

    # 注入记忆
    memory_block = ""
    if session_memories:
        memory_block = "## 你记得之前聊过\n" + "\n".join(f"- {m}" for m in session_memories[-5:]) + "\n\n"

    # 阶段 2：表达
    speak_prompt = engine.build_speak_prompt(req.message, thinking)
    speak_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": "你是毛泽东本人，在和别人聊天。说话要有你的风格。"},
                  {"role": "user", "content": memory_block + speak_prompt}],
        temperature=0.9, max_tokens=400
    )
    answer = speak_resp.choices[0].message.content
    t2 = speak_resp.usage.total_tokens if speak_resp.usage else 0
    tokens_used = t1 + t2
    total_tokens += tokens_used

    _write_log("chairman", answer, tokens_used, 0)

    # 生成摘要加入记忆
    summary = _generate_summary(req.message, answer)
    session_memories.append(summary)
    if len(session_memories) > 10:
        session_memories = session_memories[-5:]

    return ChatResp(
        answer=answer,
        sources=[{"text": r.text[:200], "source": r.source, "title": r.title, "date": r.date, "score": r.score} for r in rags],
        tokens=tokens_used,
        cumulative_tokens=total_tokens,
        fatigue=fatigue
    )
