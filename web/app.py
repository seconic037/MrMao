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
from pipeline.scenes import (
    get_scene, pick_action, pick_idle_actions, pick_exit_message,
    detect_switch_intent, get_transition, get_scene_entities_flat,
    get_switch_options, DEFAULT_SCENE, SCENES,
    FATIGUE_ACTIONS as SCENE_FATIGUE_ACTIONS,
)
from pipeline.game_engine import (
    pick_question, check_answer, should_quiz, get_question, STREAK_PRAISE,
)
from pipeline.intent import analyze_intent
from pipeline.topic_thread import TopicThread

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
    # 生成 NPC 知识库情况文件（服务启动时自动刷新）
    try:
        from rag.knowledge_usage import generate_knowledge_usage
        generate_knowledge_usage(col, model_name=EMBEDDING_MODEL, persist_dir=CHROMA_DIR)
    except Exception as ke:
        print(f"WARN: knowledge_usage 生成失败 — {ke}")
except Exception as e:
    print(f"WARN: RAG unavailable — {e}")

engine = MaoReasoningEngine()
llm: Optional[OpenAI] = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL) if LLM_API_KEY else None

# ── 内存状态 ─────────────────────────────────────────────
session_log: list[dict] = []
session_memories: list[dict] = []
recent_qa: list[dict] = []
topic_thread = TopicThread()
raw_buffer = []  # 最近2轮完整 {question, answer}
current_intent = None  # 当前轮意图缓存：记忆维护段写入，think 注入读取（避免每轮两次 analyze_intent）
total_tokens: int = 0
round_count: int = 0
last_activity: float = 0
session_title: str = ""
session_log_file: Path = None
FATIGUE_YELLOW = 21
FATIGUE_RED = 35
TIMEOUT_SECONDS = 10 * 60  # 10 分钟无操作 → 主席离开
TIMEOUT_WARN = 8 * 60      # 8 分钟无操作 → 疲倦预警
session_scene: str = DEFAULT_SCENE
pending_quiz_id: int | None = None
quiz_asked_ids: set[int] = set()
quiz_streak: int = 0
quiz_count: int = 0

LOG_DIR = Path("聊天记录")
LOG_DIR.mkdir(parents=True, exist_ok=True)
TITLES_FILE = LOG_DIR / "titles.json"

# ── 恢复上次会话 ──────────────────────────────────────────
def _restore_session():
    """从最近的日志文件恢复会话状态。"""
    global round_count, total_tokens, session_memories, session_log, session_log_file, last_activity
    log_files = sorted(LOG_DIR.glob("session_*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not log_files:
        return
    latest = log_files[0]
    try:
        entries = []
        with open(latest, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        if not entries:
            return
        round_count = sum(1 for e in entries if e.get("role") == "user")
        total_tokens = sum(e.get("tokens_in", 0) for e in entries)
        # 构建 dict 格式记忆（与实时对话一致）：{question, summary}，取最近 5 轮
        memories = []
        for e in entries[-20:]:
            if e.get("role") == "user":
                memories.append({"question": e.get("content", "")[:60], "summary": ""})
            elif e.get("role") == "chairman" and memories:
                memories[-1]["summary"] = e.get("content", "")[:80]
        session_memories = [m for m in memories if m.get("summary")][-5:]
        session_log = entries
        session_log_file = latest
        last_activity = time.time()
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
    scene_switch: Optional[dict] = None
    quiz: Optional[dict] = None      # 出题：{q, opts[], id}
    quiz_result: Optional[dict] = None  # 答题结果：{correct, msg, streak}

# ── 内容 ──────────────────────────────────────────────────
GREETINGS = [
    "来了？坐。今天想聊什么？",
    "我正好在看报纸。你有什么事？",
    "[主席掐灭烟头] 说吧，遇到什么难题了？",
    "我刚写了首词，你要不要看看？",
]

# 场景切换后 NPC 开场白兜底（LLM 偶发返回空时使用，问题 6）
FALLBACK_TOPICS = {
    "shuwu": "这满屋子的书，够咱们聊个三天三夜。方才那个话头，你心里有主意了没有？",
    "keting": "屋里清静，正好说话。方才说到的事，你回去想过了没有？",
    "xiaolu": "这小路走着走着，人就清爽了。刚才的话头，咱们边走边聊。",
    "shuxia": "树荫底下坐坐，心也就静了。方才那事儿，你琢磨出什么道道没有？",
}

IDLE_ACTIONS = [
    "[主席抽了口烟，等你开口]",
    "[老人家端起搪瓷杯，喝了口浓茶]",
    "[主席靠在藤椅上，目光望向窗外]",
    "[老人家提起铅笔，在一份文件上批了几个字]",
    "[主席站起来，走到墙边的大地图前看了看]",
    "[老人家摘下眼镜，用衣角擦了擦]",
    "[主席掐灭烟头，若有所思地看着你]",
    "[老人家翻开《资治通鉴》，看了两行]",
    "[主席站起身在屋里缓缓踱了两步]",
    "[老人家微笑着，手指轻轻敲着桌面]",
    "[主席往搪瓷杯里续了热水，杯口冒着白气]",
    "[老人家拿起红铅笔，在《人民日报》上画了个圈]",
]

FATIGUE_ACTIONS = {
    "yellow": [
        "[主席揉了揉太阳穴]",
        "[老人家放下手里的文件，闭了会儿眼]",
        "[主席端起搪瓷杯，喝完最后一口浓茶]",
        "[老人家把烟头掐灭，烟灰缸里已经四五个烟蒂了]",
    ],
    "red": [
        "[主席打了个哈欠，眼皮有点沉]",
        "[老人家身子往藤椅里靠了靠，快睡着了]",
        "[主席的烟灰缸里已经堆满了烟头，他又续了一支]",
        "[老人家摆了摆手，像是说今天就到这儿吧]",
        "[主席摘下眼镜放到一旁，背靠在椅子上]",
    ],
}

# ── 工具函数 ─────────────────────────────────────────────
def _fatigue_level() -> str:
    if round_count >= FATIGUE_RED: return "red"
    if round_count >= FATIGUE_YELLOW: return "yellow"
    return "green"

def _write_log(role: str, content: str, tokens_in: int = 0, tokens_out: int = 0):
    global last_activity
    _ensure_log_file()
    entry = {"role": role, "content": content, "time": datetime.now().isoformat(), "tokens_in": tokens_in, "tokens_out": tokens_out}
    session_log.append(entry)
    last_activity = time.time()
    _flush_log()  # 实时刷盘，意外退出不丢数据

def _generate_summary(question: str, answer: str) -> dict:
    """用 LLM 生成对话摘要。"""
    if not llm: return {"question": question[:30], "summary": answer[:30]}
    try:
        r = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": f"用一句话（不超过50字）总结这段对话的要点：\n问：{question[:100]}\n答：{answer[:100]}"}],
            max_tokens=80, temperature=0.3
        )
        return {"question": question[:60], "summary": r.choices[0].message.content.strip()[:80]}
    except:
        return {"question": question[:30], "summary": answer[:30]}

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
    fatigue = _fatigue_level()
    actions = pick_idle_actions(session_scene, fatigue, 3)
    return {"actions": actions, "scene": session_scene}

@app.post("/api/scene/set")
async def scene_set(data: dict):
    """切换场景。"""
    global session_scene
    scene_id = data.get("scene", DEFAULT_SCENE)
    if scene_id not in SCENES:
        raise HTTPException(400, f"未知场景: {scene_id}")
    old_scene = session_scene
    session_scene = scene_id
    scene = get_scene(scene_id)
    transition = get_transition(old_scene, scene_id)
    return {
        "scene": scene_id,
        "name": scene["name"],
        "atmosphere": scene["atmosphere"],
        "transition": transition,
    }

@app.get("/api/scene/get")
async def scene_get():
    """获取当前场景。"""
    scene = get_scene(session_scene)
    return {
        "scene": session_scene,
        "name": scene["name"],
        "atmosphere": scene["atmosphere"],
    }

@app.post("/api/scene/transition")
async def scene_transition(data: dict):
    """获取两个场景之间的过渡信息。"""
    from_s = data.get("from", session_scene)
    to_s = data.get("to", DEFAULT_SCENE)
    transition = get_transition(from_s, to_s)
    if not transition:
        return {"transition": None}
    return {"transition": transition}

@app.get("/api/scene/exit")
async def scene_exit():
    """生成主席离开语。"""
    scene = get_scene(session_scene)
    # 尝试生成话题总结
    summary = ""
    if session_memories:
        last = session_memories[-1]
        summary = last.get("summary", last.get("question", ""))[:40]
    msg = pick_exit_message(session_scene, summary)
    return {"message": msg, "scene": session_scene, "name": scene["name"]}

@app.get("/api/scene/suggest")
async def scene_suggest():
    """主席提议切换场景（冷场时调用）。"""
    scene = get_scene(session_scene)
    is_indoor = scene["type"].startswith("indoor")
    if is_indoor:
        target = random.choice(["xiaolu", "shuxia"])
        msg = random.choice([
            "小鬼，坐了这么久，陪我到外面走走？",
            "同志，屋里闷得很，出去透透气吧。",
            "走，到外面去，边走边聊。",
        ])
    else:
        target = random.choice(["shuwu", "keting"])
        msg = random.choice([
            "起风了，进屋坐吧。",
            "外面有点凉了，我们进屋里聊。",
        ])
    return {"message": msg, "target": target, "scene": session_scene}

@app.get("/api/scene/switch-options")
async def scene_switch_options():
    """主动切换面板数据：文案 + 可去目标（问题 1）。"""
    return get_switch_options(session_scene)

@app.post("/api/scene/fatigue-hint")
async def scene_fatigue_hint():
    """返回当前（新）场景的疲劳提示文字（问题 7：切换后提示）。"""
    scene = get_scene(session_scene)
    io = "indoor" if scene["type"].startswith("indoor") else "outdoor"
    level = _fatigue_level()
    pool = SCENE_FATIGUE_ACTIONS.get(io, {}).get(level, [])
    return {
        "hint": random.choice(pool) if pool else "",
        "level": level,
        "scene": session_scene,
        "name": scene["name"],
    }

@app.post("/api/scene/topic")
async def scene_topic():
    """切换场景后，主席主动提开场话题（问题 6，LLM 生成，可附带随机出题）。"""
    if not llm:
        return {"topic": "", "quiz": None}
    scene = get_scene(session_scene)
    # 最近对话记忆（取最近 3 条；兼容 dict 与 str 两种存储格式）
    mem = ""
    if session_memories:
        mem_items = []
        for m in session_memories[-3:]:
            if isinstance(m, dict):
                q = str(m.get("question", ""))[:40]
                s = str(m.get("summary", ""))[:60]
            else:
                q, s = "", str(m)[:60]
            if q or s:
                mem_items.append(f"对方问过「{q}」，你当时说「{s}」")
        mem = "；".join(mem_items)
    entities = "、".join(get_scene_entities_flat(session_scene)[:6])
    prompt = (
        f"你是毛泽东，刚刚和对方一起到了新地方——{scene['name']}（{scene['type']}）。\n"
        f"场景氛围：{scene['atmosphere']}\n"
        f"身边的事物：{entities}\n"
        + (f"最近聊过：{mem}\n" if mem else "")
        + "请以毛泽东的口吻说 2~3 句开场白：先结合当前场景说一句眼前的景象或感受，"
        "再自然接一句和刚才话题相关的话（如果刚才聊过的话；没有就随意从场景引出一个话题），"
        "最后可以留一个钩子让对方接话。不要用「现在」「我们」等翻译腔。直接说话，不要带方括号动作。"
    )
    topic = ""
    try:
        resp = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85, max_tokens=220
        )
        topic = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"Scene topic failed: {e}")
    # LLM 偶发返回空/单字 → 本地兜底，保证 NPC 话题完整不缺席
    if not topic or len(topic) < 20:
        topic = FALLBACK_TOPICS.get(session_scene, FALLBACK_TOPICS[DEFAULT_SCENE])
    return {"topic": topic, "quiz": None}  # 考考你不再自动触发

@app.get("/api/logs")
async def get_logs():
    titles = _load_titles()
    sessions = []
    for f in sorted(LOG_DIR.glob("session_*.jsonl"), reverse=True):
        t = titles.get(f.name, {})
        # 取最后一条主席消息作为两行预览
        preview = ""
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("role") == "chairman" and entry.get("content"):
                            preview = entry["content"]
                    except Exception:
                        continue
        except Exception:
            pass
        sessions.append({"name": f.name, "size": f.stat().st_size, "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "title": t.get("title", ""), "rounds": t.get("rounds", 0), "preview": preview[:60]})
    return {"sessions": sessions, "current": str(session_log_file.name) if session_log_file else "",
            "entries": session_log[-100:], "active_rounds": round_count, "active_title": session_title}

@app.delete("/api/logs/{filename}")
async def delete_log(filename: str):
    """删除指定日志文件。"""
    path = LOG_DIR / filename
    if path.exists() and "session_" in filename and ".." not in filename:
        path.unlink()
        return {"deleted": filename}
    raise HTTPException(404, "文件不存在")

@app.post("/api/compact")
async def compact():
    global round_count, session_memories
    summary = _compact_context()
    round_count = 0
    session_memories = [{"question": "(续聊摘要)", "summary": summary}] if summary else []
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
    """百度热搜，缓存 5 分钟。"""
    global _hotspots_cache, _hotspots_time
    import time as _t
    now = _t.time()
    if _hotspots_cache and now - _hotspots_time < 300:
        return _hotspots_cache
    from pipeline.hotspot_fetcher import fetch_baidu_hotspots
    data = fetch_baidu_hotspots(limit=15)
    _hotspots_time = now
    _hotspots_cache = data
    return data

@app.post("/api/hotspots/refresh")
async def refresh_hotspots():
    """强制刷新热搜。"""
    global _hotspots_cache, _hotspots_time
    from pipeline.hotspot_fetcher import fetch_baidu_hotspots
    import time as _t
    _hotspots_time = _t.time()
    _hotspots_cache = fetch_baidu_hotspots(limit=15)
    return _hotspots_cache


@app.get("/api/kb-stats")
async def kb_stats():
    """统计知识库字数（含知识扩展）。"""
    import glob as _glob
    total = 0
    for f in _glob.glob("data/txt/**/*_全文.txt", recursive=True) + _glob.glob("data/txt/**/*_精选.txt", recursive=True) + _glob.glob("data/txt/知识扩展/*.txt", recursive=True):
        try: total += len(open(f, encoding="utf-8").read())
        except: pass
    return {"word_count": total, "word_count_wan": round(total / 10000)}

@app.get("/api/knowledge/structure")
async def knowledge_structure():
    """查看知识库架构。"""
    import subprocess
    result = subprocess.run(["python", "tools/ingest_knowledge.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=".")
    return {"output": result.stdout or (result.stderr or "无输出")}


# ── 会话管理 ──────────────────────────────────────────
def _ensure_log_file():
    global session_log_file
    if session_log_file is None:
        session_log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

def _save_titles(titles=None):
    if titles is None:
        titles = {}
        if TITLES_FILE.exists():
            try: titles = json.loads(open(TITLES_FILE, encoding="utf-8").read())
            except: pass
    open(TITLES_FILE, "w", encoding="utf-8").write(json.dumps(titles, ensure_ascii=False))

def _load_titles():
    if TITLES_FILE.exists():
        try: return json.loads(open(TITLES_FILE, encoding="utf-8").read())
        except: pass
    return {}

def _auto_save_session():
    """15分钟无操作自动保存日志。"""
    global session_log, round_count
    if not session_log_file or not session_log or round_count == 0:
        return
    _flush_log()
    print(f"Session auto-saved: {round_count} rounds")

def _flush_log():
    """将内存中的日志写入文件。"""
    global session_log, session_log_file
    if not session_log or session_log_file is None:
        return
    with open(session_log_file, "a", encoding="utf-8") as f:
        for entry in session_log:
            if isinstance(entry, dict) and "_written" not in entry:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                entry["_written"] = True

@app.get("/api/session/status")
async def session_status():
    """当前会话状态。"""
    import time as _t
    idle = _t.time() - last_activity if last_activity else 0
    return {"active": round_count > 0, "rounds": round_count, "tokens": total_tokens,
            "idle_seconds": int(idle), "title": session_title, "file": str(session_log_file.name) if session_log_file else ""}

@app.post("/api/session/save")
async def session_save(title: str = ""):
    """保存日志。title 为空则自动生成。"""
    global session_title, session_log, round_count, total_tokens, session_memories, last_activity, session_log_file
    _ensure_log_file()
    _flush_log()
    session_title = title or datetime.now().strftime("%m/%d %H:%M")
    titles = _load_titles()
    titles[session_log_file.name] = {"title": session_title, "rounds": round_count, "time": datetime.now().isoformat()}
    _save_titles(titles)
    # 重置会话
    session_log = []; session_memories = []; round_count = 0; total_tokens = 0; last_activity = 0
    session_log_file = None
    return {"saved": True, "title": session_title}

@app.post("/api/session/discard")
async def session_discard():
    """丢弃当前日志。"""
    global session_log, round_count, total_tokens, session_memories, last_activity, session_log_file
    if session_log_file and session_log_file.exists():
        session_log_file.unlink()
    session_log = []; session_memories = []; round_count = 0; total_tokens = 0; last_activity = 0
    session_log_file = None
    return {"discarded": True}

@app.get("/api/logs/entries")
async def get_log_entries(filename: str = ""):
    """读取指定日志文件的全部条目（用于恢复历史消息）。"""
    path = LOG_DIR / filename
    if not path.exists() or "session_" not in filename or ".." in filename:
        raise HTTPException(404, "文件不存在")
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return {"entries": entries}

@app.post("/api/logs/append")
async def append_log_entry(payload: dict):
    """前端注入的 NPC 消息（场景话题/恢复总结等）也写入日志，保证界面与日志一致。"""
    role = payload.get("role", "chairman")
    content = str(payload.get("content", "")).strip()
    if not content:
        return {"ok": True}
    _write_log(role, content, 0, 0)
    return {"ok": True}

@app.post("/api/logs/entries/update")
async def update_log_entries(payload: dict):
    """保存编辑后的日志条目（删除/新增后写回文件）。"""
    filename = str(payload.get("filename", ""))
    entries = payload.get("entries")
    if not isinstance(entries, list) or "session_" not in filename or ".." in filename:
        raise HTTPException(400, "参数无效")
    path = LOG_DIR / filename
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return {"ok": True}

@app.post("/api/session/title")
async def set_title(filename: str = "", title: str = ""):
    """编辑日志标题。"""
    titles = _load_titles()
    titles[filename] = {**titles.get(filename, {}), "title": title}
    _save_titles(titles)
    return {"ok": True}

@app.post("/api/session/restore")
async def restore_session(filename: str = ""):
    """恢复指定日志文件为当前会话：NPC 获得最近 5 条对话记忆。"""
    path = LOG_DIR / filename
    if not path.exists() or "session_" not in filename or ".." in filename:
        raise HTTPException(404, "文件不存在")
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        raise HTTPException(400, "日志解析失败")
    global round_count, total_tokens, session_memories, session_log, session_log_file, last_activity
    round_count = sum(1 for e in entries if e.get("role") == "user")
    total_tokens = sum(e.get("tokens_in", 0) for e in entries)
    # 构建 dict 格式记忆（与实时对话一致）：{question, summary}，取最近 5 轮
    memories = []
    for e in entries[-20:]:
        if e.get("role") == "user":
            memories.append({"question": e.get("content", "")[:60], "summary": ""})
        elif e.get("role") == "chairman" and memories:
            memories[-1]["summary"] = e.get("content", "")[:80]
    session_memories = [m for m in memories if m.get("summary")][-5:]
    session_log = entries
    session_log_file = path
    last_activity = time.time()
    print(f"Session restored by request: {round_count} rounds, {len(session_memories)} memories from {filename}")
    return {"ok": True, "rounds": round_count, "memories": len(session_memories), "file": filename}

@app.post("/api/session/summarize")
async def summarize_log(filename: str = ""):
    """一键总结指定日志文件的对话内容。"""
    if not llm: raise HTTPException(503, "LLM 未配置")
    path = LOG_DIR / filename
    if not path.exists() or "session_" not in filename or ".." in filename:
        raise HTTPException(404, "文件不存在")
    content = path.read_text(encoding="utf-8")
    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": f"用一段话（不超过200字）总结以下对话内容：\n{content[:4000]}"}],
        max_tokens=300, temperature=0.5
    )
    return {"summary": resp.choices[0].message.content.strip(), "filename": filename}

@app.post("/api/hotspot/preview")
async def hotspot_preview(title: str = ""):
    """生成热点事件的概述（口语化、简短、纯事件描述）。"""
    if not llm or not title: return {"brief": title}
    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": f"用2-3句话口语化地讲清楚这个热点事件：{title}\n\n要求：像朋友聊天那样描述事件本身（发生了什么、大家什么反应），不要用「你刷到没」「你知道吗」「听说」这类引语开头，直接说事；别用书面语，别列条目，不超过100字。"}],
        max_tokens=180, temperature=0.8
    )
    return {"title": title, "brief": resp.choices[0].message.content.strip()}

@app.post("/api/hotspot/fetch")
async def hotspot_fetch(payload: dict):
    """抓取热点原文 URL 并提取正文纯文字（供弹窗内展示，不跳转）。"""
    url = str(payload.get("url", "")).strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return {"text": "", "error": "无效链接"}
    import urllib.request, re

    def _fetch(u):
        req = urllib.request.Request(u, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", "replace")

    # 从热点 url 中提取搜索词（百度 url 形如 ...?word=关键词&sa=...）
    m = re.search(r"[?&]word=([^&]+)", url)
    query = urllib.parse.unquote(m.group(1)) if m else url
    if query.startswith("http"):
        query = ""
    results = []

    # 源1：必应中国版（稳定，不触发安全验证）
    try:
        html = _fetch("https://cn.bing.com/search?q=" + urllib.parse.quote(query[:40]))
        text = _extract_bing(html)
        if text:
            results.append(text)
    except Exception as e:
        print(f"[hotspot/fetch] bing failed: {e}")

    # 源2：百度（降级备选）
    if not results:
        try:
            html = _fetch(url)
            text = _extract_baidu(html)
            if text:
                results.append(text)
        except Exception as e:
            print(f"[hotspot/fetch] baidu failed: {e}")

    if not results:
        return {"text": "", "error": "未能获取到正文（可能是反爬或页面无文字）"}
    text = results[0]
    if len(text) > 3000:
        text = text[:3000] + "…"
    return {"text": text, "error": ""}


def _extract_bing(html: str) -> str:
    """提取必应搜索结果页的正文：取前 2 条结果摘要拼接。"""
    import re
    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    # 先分行（每个标签后换行），再逐行压空白——顺序不能反
    text = re.sub(r"<[^>]+>", "\n", text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if len(l) > 40]
    out = []
    for l in lines:
        # 跳过导航/标题行
        if re.match(r"^(搜索|自适应|跳至|辅助|国内版|国际版|网页|图片|视频|学术|词典|地图|航班|约 \d|在新选项卡|时间不限|相关搜索|大家还在搜)", l):
            continue
        # 跳过域名来源行（sohu.com / cctv.com 等，后面紧跟正文）
        if re.match(r"^[a-z0-9\-\.]+\.[a-z]{2,5}\b", l) and len(out) == 0:
            continue
        # 跳过"标题 + 日期"来源行（含 › 面包屑）
        if " › " in l and len(out) == 0:
            continue
        if "页版权|Microsoft|隐私|必应" in l and len(out) > 2:
            break
        out.append(l)
        if len(out) >= 4:
            break
    joined = " ".join(out).strip()
    # 解码 HTML 实体 &ensp;/&#0183; 等
    try:
        import html as _html
        joined = _html.unescape(joined)
    except Exception:
        pass
    # 清理行首时间戳（如"2026年1月1日&ensp;"、"10 小时之前&ensp;"）
    joined = re.sub(r"(^|\s)(\d{4}年\d+月\d+日|\d+ 天前|\d+ 小时之前|\d+ 分钟前)\s*", r"\1", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


def _extract_baidu(html: str) -> str:
    """提取百度搜索页正文（原逻辑保留）。"""
    import re
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>|</p>|</div>|</h\d>|</li>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    for noise in ["百度一下 点击即刻体验AI搜索", "百度一下 点击查看更全面", "立即体验AI搜索"]:
        if noise in text:
            text = text[text.index(noise) + len(noise):].strip()
            break
    for kw in ["综合 笔记 视频 图片 资源筛选 资讯 问答 文档", "上升热点 昨天 人民日报",
               "商品 采购 小说 音乐 排序方式", "发布时间 24小时 1周内 1月内 1年内 重置"]:
        text = text.replace(kw, "")
    for cut_kw in ["相关搜索", "大家还在搜"]:
        cut = text.find(cut_kw)
        if cut > 200:
            text = text[:cut]
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[！!—\-·、，,。\s]+", "", text)
    nav = re.match(r"^(综合 笔记 视频 图片[^\u4e00-\u9fa5]*|热搜榜[^\u4e00-\u9fa5]*第\d+名\s*)", text)
    if nav:
        text = text[nav.end():]
    return text.strip()

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

def _maybe_quiz() -> dict | None:
    """判断是否应该出题。"""
    global pending_quiz_id, quiz_asked_ids, quiz_count
    if not should_quiz(round_count, quiz_count):
        return None
    q = pick_question(session_scene, quiz_asked_ids)
    if not q:
        quiz_asked_ids.clear()
        q = pick_question(session_scene, quiz_asked_ids)
        if not q:
            return None
    pending_quiz_id = q["id"]
    quiz_asked_ids.add(q["id"])
    quiz_count += 1
    return {"q": q["q"], "opts": q["opts"], "id": q["id"]}

@app.post("/api/quiz/question")
async def quiz_question():
    """主动出一道题（仅用户触发，绝不自动）。"""
    global pending_quiz_id, quiz_asked_ids, quiz_count
    q = pick_question(session_scene, quiz_asked_ids)
    if not q:
        quiz_asked_ids.clear()
        q = pick_question(session_scene, quiz_asked_ids)
        if not q:
            return {"question": None}
    pending_quiz_id = q["id"]
    quiz_asked_ids.add(q["id"])
    quiz_count += 1
    return {"question": {"id": q["id"], "q": q["q"], "opts": q["opts"], "category": q.get("category", "")}}

@app.post("/api/quiz/answer")
async def quiz_answer(payload: dict):
    """判题 + 返回题目介绍（弹窗内展示，用户确认后关闭）。"""
    global pending_quiz_id
    if payload.get("skip"):
        pending_quiz_id = None
        return {"skipped": True}
    try:
        qid = int(payload.get("id", -1))
        ans = int(payload.get("ans", -1))
    except (TypeError, ValueError):
        qid, ans = -1, -1
    result = check_answer(qid, ans)
    q = get_question(qid)
    pending_quiz_id = None  # 弹窗内答题完成，清除待答状态
    return {
        "correct": result["correct"],
        "msg": result["msg"],
        "correct_answer": result.get("correct_answer"),
        "correct_text": q["opts"][result["correct_answer"]] if q else "",
        "intro": (q.get("hint", "") if q else ""),
        "category": (q.get("category", "") if q else ""),
    }

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
    """列出某来源下的所有文章。排除知识扩展。"""
    import glob as _glob, json as _json
    articles = []
    files = sorted(_glob.glob("data/extracted/**/*.json", recursive=True))
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                art = _json.load(fh)
            if "知识扩展" in art.get("source", ""): continue
            if source and source not in art.get("source", ""): continue
            articles.append({"title": art.get("title",""), "date": art.get("date",""),
                           "source": art.get("source",""), "chars": len(art.get("content",""))})
        except: continue
    return {"articles": articles, "count": len(articles)}

@app.post("/api/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    global total_tokens, round_count, session_memories, recent_qa
    global pending_quiz_id, quiz_asked_ids, quiz_streak, quiz_count
    global current_intent, raw_buffer
    if not llm:
        raise HTTPException(503, "LLM 未配置")
    if req.message == "__greeting__":
        return ChatResp(answer=random.choice(GREETINGS), fatigue=_fatigue_level())

    round_count += 1
    fatigue = _fatigue_level()
    _write_log("user", req.message)

    # ── 检测 quiz 答题 ──
    quiz_result = None
    if pending_quiz_id is not None:
        try:
            user_ans = int(req.message.strip())
        except ValueError:
            user_ans = -1
        if 0 <= user_ans <= 2:
            result = check_answer(pending_quiz_id, user_ans)
            if result["correct"]:
                quiz_streak += 1
                # 连对特殊表扬
                streak_msg = STREAK_PRAISE.get(quiz_streak, "")
                if streak_msg:
                    result["msg"] = streak_msg + " " + result["msg"]
            else:
                quiz_streak = 0
            quiz_result = {"correct": result["correct"], "msg": result["msg"], "streak": quiz_streak}
            pending_quiz_id = None
            return ChatResp(answer=result["msg"], fatigue=fatigue, quiz_result=quiz_result)

    # 非答题 → 清除 pending
    pending_quiz_id = None

    # 检测超时
    if last_activity and (time.time() - last_activity) > TIMEOUT_SECONDS:
        _flush_log()
        _auto_save_session()

    # 检索
    rags = retriever.search(req.message, top_k=5) if retriever else []

    # 阶段 1：思维（注入对话记忆 + 话题线 + 原文缓冲 + 意图）
    think_prompt = engine.build_think_prompt(
        req.message, rags, session_memories[-5:],
        topic_line=topic_thread.summary(),
        raw_recent=raw_buffer,
        intent=current_intent,
    )
    think_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": think_prompt}],
        temperature=0.3, max_tokens=300
    )
    thinking = (think_resp.choices[0].message.content or "").strip()
    t1 = think_resp.usage.total_tokens if think_resp.usage else 0
    # thinking 为空 → 重试一次
    if not thinking:
        think_resp = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": think_prompt}],
            temperature=0.5, max_tokens=300
        )
        thinking = (think_resp.choices[0].message.content or "").strip()
        t1 += think_resp.usage.total_tokens if think_resp.usage else 0
    if not thinking:
        thinking = "对方在问：{0}。结合毛选方法论简要分析主要矛盾与可引用的原文，给出引导方向。".format(req.message[:50])

    # 阶段 2：表达（注入场景上下文）
    scene = get_scene(session_scene)
    scene_context = {
        "name": scene["name"],
        "atmosphere": scene["atmosphere"],
        "type": scene["type"],
        "entities": get_scene_entities_flat(session_scene),
    }
    speak_prompt = engine.build_speak_prompt(req.message, thinking, scene_context=scene_context)
    speak_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": "你是毛泽东本人，在和别人聊天。说话要有你的风格。"},
                  {"role": "user", "content": speak_prompt}],
        temperature=0.9, max_tokens=600
    )
    answer = (speak_resp.choices[0].message.content or "").strip()
    t2 = speak_resp.usage.total_tokens if speak_resp.usage else 0
    # answer 为空 → 重试一次
    if not answer:
        speak_resp = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "你是毛泽东本人，在和别人聊天。说话要有你的风格。"},
                      {"role": "user", "content": speak_prompt}],
            temperature=1.0, max_tokens=600
        )
        answer = (speak_resp.choices[0].message.content or "").strip()
        t2 += speak_resp.usage.total_tokens if speak_resp.usage else 0
    if not answer:
        answer = "[主席笑了笑] 这个问题，我得好好琢磨琢磨。你先把你的想法说来听听，咱们一起分析分析。"
    tokens_used = t1 + t2
    total_tokens += tokens_used

    _write_log("chairman", answer, tokens_used, 0)

    # 场景切换检测
    scene_switch = None
    switch_target = detect_switch_intent(req.message, session_scene)
    if switch_target and switch_target != session_scene:
        scene_switch = get_transition(session_scene, switch_target)
        if scene_switch:
            scene_switch["target"] = switch_target

    # 意图判断 + 三层记忆维护
    current_intent = analyze_intent(req.message)
    summary = _generate_summary(req.message, answer)
    summary["emotion"] = current_intent["emotion"]
    session_memories.append(summary)
    if len(session_memories) > 10:
        session_memories = session_memories[-5:]
    # 内容缓冲：最近2轮原文
    raw_buffer.append({"question": req.message, "answer": answer})
    if len(raw_buffer) > 2:
        raw_buffer = raw_buffer[-2:]
    # 话题主线
    topic_thread.update(req.message)

    return ChatResp(
        answer=answer,
        sources=[{"text": r.text[:200], "source": r.source, "title": r.title, "date": r.date, "score": r.score} for r in rags],
        tokens=tokens_used,
        cumulative_tokens=total_tokens,
        fatigue=fatigue,
        scene_switch=scene_switch,
        quiz=None,  # 考考你不再自动触发，仅由 /api/quiz/question 主动出题
    )
