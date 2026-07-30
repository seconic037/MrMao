"""毛选思维引擎 FastAPI Web 服务"""
import os
from pathlib import Path
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
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── FastAPI 应用 ──────────────────────────────────────────
app = FastAPI(title="毛选思维引擎", version="1.0")

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── 全局组件（延迟初始化）────────────────────────────────
retriever: Optional[Retriever] = None
try:
    col = load_collection(
        persist_dir=CHROMA_DIR,
        collection_name="maozedong-works",
        model_name=EMBEDDING_MODEL,
    )
    retriever = Retriever(col)
    print(f"RAG loaded: {col.count()} docs")
except Exception as e:
    print(f"WARN: RAG unavailable — {e}")

engine = MaoReasoningEngine()

llm: Optional[OpenAI] = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL) if LLM_API_KEY else None


# ── 请求/响应模型 ────────────────────────────────────────
class ChatReq(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResp(BaseModel):
    answer: str
    sources: list[dict] = []


# ── 路由 ──────────────────────────────────────────────────
@app.get("/")
async def root():
    """返回前端聊天界面 (static/index.html)。"""
    idx = static_dir / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"msg": "毛选思维引擎", "docs": "/docs"}


@app.get("/api/status")
async def status():
    """系统状态。"""
    return {
        "rag": retriever is not None,
        "llm": llm is not None,
        "model": LLM_MODEL,
        "chroma": CHROMA_DIR,
    }


@app.get("/api/sources")
async def sources():
    """列出已入库文献清单。"""
    if not retriever:
        return {"sources": [], "count": 0}
    seen = set()
    srcs = []
    for m in retriever._metadatas:
        key = (m.get("source", ""), m.get("title", ""))
        if key not in seen:
            seen.add(key)
            srcs.append({
                "source": m.get("source", ""),
                "title": m.get("title", ""),
                "date": m.get("date", ""),
            })
    return {"sources": srcs, "count": len(srcs)}


@app.post("/api/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    """问答：接收用户消息，返回分析答案及引用来源。"""
    if not llm:
        raise HTTPException(503, "LLM 未配置，请设置 OPENAI_API_KEY")

    rags = retriever.search(req.message, top_k=5) if retriever else []
    prompt = engine.build_prompt(req.message, rags)

    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是毛泽东思想的学者和分析家。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    return ChatResp(
        answer=resp.choices[0].message.content,
        sources=[
            {
                "text": r.text[:200],
                "source": r.source,
                "title": r.title,
                "date": r.date,
                "score": r.score,
            }
            for r in rags
        ],
    )
