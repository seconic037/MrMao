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
    "[掐灭烟头] 说吧，遇到什么难题了？",
    "我刚写了首词，你要不要看看？",
]

IDLE_ACTIONS = [
    "[抽了口烟，等你开口]",
    "[端起搪瓷杯，喝了口浓茶]",
    "[靠在藤椅上，目光望向窗外]",
    "[拿笔在纸上写了几个字，又划掉了]",
    "[翻了翻手边的毛选]",
    "[站起来在屋里踱了两步]",
    "[掐灭烟头，若有所思地看着你]",
    "[微笑了一下，等着你继续]",
]

FATIGUE_ACTIONS = {
    "yellow": ["[揉了揉太阳穴]", "[喝了口浓茶提神]"],
    "red": ["[打了个哈欠]", "[眼皮有点沉]", "[烟灰缸里已经堆满了烟头]"],
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
        sessions.append({"name": f.name, "size": f.stat().st_size})
    return {"sessions": sessions, "current": str(session_log_file.name), "entries": session_log[-50:]}

@app.post("/api/compact")
async def compact():
    global round_count, session_memories
    summary = _compact_context()
    round_count = 0
    session_memories = [summary] if summary else []
    return {"message": "主席精神了", "summary": summary, "fatigue": "green"}

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
