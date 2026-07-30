# 毛选思维引擎 — Implementation Plan v2 (TXT-based)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于 TXT 格式的毛泽东著作（毛选四卷全文 100万字 + 诗词 132 首 + 文集目录），构建一个 RAG 问答 Web 系统。先用 book-to-skill 萃取毛选知识库（框架/原则/方法/反面模式），再结合 ChromaDB 向量检索原文，以毛选思维方式生成结构化回答。

**Architecture:** 离线管道（TXT解析→分块→向量化） + 在线服务（FastAPI→ChromaDB检索→毛式推理→回答输出）。前端纯 HTML+CSS+JS 聊天界面。

**Data source:** `ChairManMao.zip` → `data/txt/` (毛选 4 卷全文 TXT + 毛泽东诗词 + 文集/文稿目录)

**Tech Stack:** Python 3.11, FastAPI, ChromaDB, sentence-transformers (BAAI/bge-small-zh-v1.5), deepseek-chat / OpenAI API, jinja2

## Global Constraints

- 嵌入模型：BAAI/bge-small-zh-v1.5（本地运行，中文优化，首次自动下载 ~400MB）
- LLM：deepseek-chat / OpenAI API（通过 .env 切换）
- 向量数据库：ChromaDB，collection 名 `maozedong-works`
- 前端：纯 HTML+CSS+JS，无框架依赖
- 启动方式：`python run_server.py`
- Python >=3.11
- 数据量：207 篇/首（毛选四卷约 100 万字 + 诗词 132 首）

## Current Progress

| Task | Status | Commit |
|------|--------|--------|
| Task 1: 项目脚手架 | ✅ Done | d08c975 |
| Task 2: TXT 解析器 (替代 PDF) | ✅ Done | 6349ed4 |
| Task 3: 文本分块器 | ✅ Done + fixed | 1dc40b1 |
| Task 5: 向量化入库 | ✅ Done | (included in 6349ed4) |
| Task 4: book-to-skill 知识萃取 | ⏳ Pending | interactive |
| Task 6: RAG 检索器 | ⏳ Pending | |
| Task 7: 毛式推理层 | ⏳ Pending | |
| Task 8: FastAPI Web 服务 | ⏳ Pending | |
| Task 9: Web 前端 | ⏳ Pending | |
| Task 10: 集成 | ⏳ Pending | |

---

### Task 4: book-to-skill 知识萃取（交互式）

> ⚠️ 手动步骤。book-to-skill 是内置 subagent 技能，非自动化脚本。

**Files:**
- Create: `knowledge/maozedong-knowledge-base.md`（产出物 — 结构化毛选知识库）

**Interfaces:**
- Consumes: `data/extracted/` 中的 TXT 解析结果（JSON，Task 2 产出）
- **或直接消费原始 TXT：** `data/txt/毛选第一卷/毛选第一卷_全文.txt` 等
- Produces: 结构化知识库包含框架/原则/方法/反面模式四类 + 出处索引

- [ ] **Step 1: 在 Reasonix 中运行 book-to-skill 萃取**

根据 book-to-skill 的使用方式，直接对 TXT 原文进行分析：
```
/book-to-skill data/txt/
```
或对解析后的 JSON 进行分析：
```
/book-to-skill data/extracted/
```

- [ ] **Step 2: 将萃取结果格式化为标准知识库文件**

```markdown
# 毛泽东选集 — 知识库
> 基于毛选 1-4 卷 (约100万字) + 毛泽东诗词 132首 萃取
> 数据来源: qstheory.cn 求是网公开资料

## 核心框架
<!-- 辩证唯物主义认识论、历史唯物主义社会分析、马克思主义中国化 -->

## 基本原则
<!-- 实事求是、独立自主、群众路线、为人民服务 -->

## 工作方法
<!-- 矛盾分析法、调查研究法、阶级分析法、整风方法 -->

## 反面模式
<!-- 本本主义、教条主义、经验主义、主观主义、尾巴主义 -->

## 出处索引
<!-- 每条知识标注原始出处（卷·篇·写作时间） -->
```

- [ ] **Step 3: 保存到 knowledge/maozedong-knowledge-base.md**

---

### Task 6: RAG 检索器

**Files:**
- Create: `rag/retriever.py`

**Interfaces:**
- Consumes: `load_collection(...)` from `pipeline/embed_and_store.py` (Task 5)
- Produces: `Retriever` class with `search(query: str, top_k: int) -> list[SearchResult]`
- Produces: `SearchResult` = `{text, source, title, date, score}`

- [ ] **Step 1: 编写 `rag/retriever.py`**

```python
"""RAG 检索器：向量相似度 + BM25 关键词混合检索，RRF 融合排序。"""
from dataclasses import dataclass
from typing import Optional
import chromadb
from rank_bm25 import BM25Okapi
import jieba


@dataclass
class SearchResult:
    text: str
    source: str
    title: str
    date: str = ""
    score: float = 0.0
    chunk_id: str = ""


class Retriever:
    def __init__(self, collection: chromadb.Collection, bm25_weight: float = 0.3):
        self.collection = collection
        self.bm25_weight = bm25_weight
        self._build_bm25()

    def _build_bm25(self):
        all_docs = self.collection.get()
        self._documents = all_docs.get("documents", [])
        self._metadatas = all_docs.get("metadatas", [])
        self._ids = all_docs.get("ids", [])
        if self._documents:
            tokenized = [list(jieba.cut(doc)) for doc in self._documents]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        # 1. Vector search
        vector_results = self.collection.query(query_texts=[query], n_results=min(10, len(self._documents)))
        vector_scores = {}
        for idx, chunk_id in enumerate(vector_results["ids"][0]):
            d = vector_results.get("distances", [[0]])[0][idx]
            vector_scores[chunk_id] = 1.0 / (1.0 + d) if d else 1.0

        # 2. BM25 search
        bm25_scores = {}
        if self._bm25:
            query_tokens = list(jieba.cut(query))
            scores = self._bm25.get_scores(query_tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
            max_s = max(scores) if scores else 1.0
            for idx in top_indices:
                bm25_scores[self._ids[idx]] = scores[idx] / max_s

        # 3. RRF fusion
        combined = {}
        all_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        for chunk_id in all_ids:
            vs = vector_scores.get(chunk_id, 0) * (1 - self.bm25_weight)
            bs = bm25_scores.get(chunk_id, 0) * self.bm25_weight
            combined[chunk_id] = vs + bs

        sorted_ids = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]
        id_to_idx = {cid: i for i, cid in enumerate(self._ids)}
        return [
            SearchResult(
                text=self._documents[id_to_idx[cid]],
                source=self._metadatas[id_to_idx[cid]].get("source", ""),
                title=self._metadatas[id_to_idx[cid]].get("title", ""),
                date=self._metadatas[id_to_idx[cid]].get("date", ""),
                score=round(score, 4),
                chunk_id=cid,
            )
            for cid, score in sorted_ids if cid in id_to_idx
        ]
```

- [ ] **Step 2: 自测**

```bash
python -c "
from pipeline.embed_and_store import embed_and_store
from rag.retriever import Retriever
import tempfile
test_chunks = [
    {'id':'r0','text':'实事求是就是从实际出发，理论联系实际。','source':'毛选一','title':'改造我们的学习','date':'1941'},
    {'id':'r1','text':'没有调查就没有发言权。','source':'毛选一','title':'反对本本主义','date':'1930'},
    {'id':'r2','text':'矛盾存在于一切事物的发展过程中。','source':'毛选一','title':'矛盾论','date':'1937'},
]
col = embed_and_store(test_chunks, persist_dir=tempfile.mkdtemp())
retriever = Retriever(col)
results = retriever.search('什么是实事求是', top_k=2)
for r in results:
    print(f'  [{r.score}] {r.title}: {r.text[:50]}')
assert results
print('Retriever test passed')
"
```

- [ ] **Step 3: 提交**

```bash
git add rag/retriever.py
git commit -m "feat: add hybrid RAG retriever (vector + BM25 with RRF)"
```

---

### Task 7: 毛式推理层

**Files:**
- Create: `reasoning/framework.py`
- Create: `reasoning/prompts/qa_with_reasoning.jinja2`
- Create: `reasoning/prompts/pure_reasoning.jinja2`

**Interfaces:**
- Consumes: `knowledge/maozedong-knowledge-base.md` (book-to-skill 萃取产物)
- Consumes: `list[SearchResult]` (from Task 6 retriever)
- Produces: `MaoReasoningEngine` class with `build_prompt(question, rag_results, chat_history) -> str`

- [ ] **Step 1: 编写 `reasoning/framework.py`**

```python
"""毛式推理引擎：加载 book-to-skill 知识库，结合 RAG 结果生成分析 Prompt。"""
import os
from dataclasses import dataclass
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from rag.retriever import SearchResult


@dataclass
class ReasoningContext:
    question: str
    knowledge_base: str
    rag_results: list[SearchResult]
    chat_history: list[dict]


class MaoReasoningEngine:
    def __init__(self, knowledge_path="knowledge/maozedong-knowledge-base.md", prompt_dir="reasoning/prompts"):
        self.knowledge_path = knowledge_path
        self._knowledge_base = self._load_knowledge()
        self._jinja_env = Environment(loader=FileSystemLoader(prompt_dir), trim_blocks=True, lstrip_blocks=True)

    def _load_knowledge(self) -> str:
        if os.path.exists(self.knowledge_path):
            with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > 200:
                return content
        return """## 毛选通用方法论
### 核心框架
辩证唯物主义：一切从实际出发。矛盾分析法：抓住主要矛盾。
### 基本原则
实事求是、群众路线、独立自主。
### 工作方法
调查研究、总结经验、集中兵力。
### 反面模式
本本主义、经验主义、主观主义。"""

    def build_prompt(self, question: str, rag_results=None, chat_history=None) -> str:
        context = ReasoningContext(
            question=question, knowledge_base=self._knowledge_base,
            rag_results=rag_results or [], chat_history=chat_history or []
        )
        template_name = "qa_with_reasoning.jinja2" if rag_results else "pure_reasoning.jinja2"
        return self._jinja_env.get_template(template_name).render(
            question=context.question, knowledge_base=context.knowledge_base,
            rag_results=context.rag_results, chat_history=context.chat_history
        )
```

- [ ] **Step 2: 编写 `qa_with_reasoning.jinja2`**

```jinja2
你是一位精通毛泽东思想的学者和分析家。

## 毛泽东著作知识库

{{ knowledge_base }}

## 检索到的相关原文

{% for r in rag_results %}
**出处：{{ r.source }} · {{ r.title }}{% if r.date %}（{{ r.date }}）{% endif %}**
> {{ r.text }}
{% endfor %}

## 用户问题

{{ question }}

## 回答要求

1. **引用原文**：直接引用原文段落，标注出处。
2. **矛盾分析**：抓主要矛盾、主要方面/次要方面。
3. **实事求是**：客观条件 + 主观能动性。
4. **实践建议**：具体可行的行动指南。

格式：**根据《篇名》(时间)**: 引用+分析 → **[矛盾分析]**: → **[建议]**:
```

- [ ] **Step 3: 编写 `pure_reasoning.jinja2`**

```jinja2
你是一位精通毛泽东思想的学者。

## 知识库

{{ knowledge_base }}

## 用户问题

{{ question }}

基于方法论框架分析，如有不确定请坦诚说明。
```

- [ ] **Step 4: 自测 + 提交**

```bash
python -c "
from reasoning.framework import MaoReasoningEngine
engine = MaoReasoningEngine()
p = engine.build_prompt('什么是实事求是？')
assert '实事求是' in p
print('Reasoning test passed')
"
git add reasoning/ reasoning/prompts/
git commit -m "feat: add Maoist reasoning engine with Jinja2 prompt templates"
```

---

### Task 8: FastAPI Web 服务

**Files:**
- Create: `web/app.py`

**Interfaces:**
- Consumes: `Retriever` (Task 6), `MaoReasoningEngine` (Task 7), `load_collection` (Task 5)
- Produces:
  - `POST /api/chat` — 问答（`{"message":"...", "session_id":"?"}` → `{"answer":"...", "sources":[...]}`）
  - `GET /api/sources` — 列出已入库文献
  - `GET /api/status` — 系统状态

- [ ] **Step 1: 编写 `web/app.py`**

```python
"""毛选思维引擎 Web 服务"""
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

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

app = FastAPI(title="毛选思维引擎", version="1.0")
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

retriever = None
try:
    collection = load_collection(persist_dir=CHROMA_DIR, collection_name="maozedong-works", model_name=EMBEDDING_MODEL)
    retriever = Retriever(collection)
except Exception as e:
    print(f"WARNING: RAG not available — {e}")

engine = MaoReasoningEngine(knowledge_path="knowledge/maozedong-knowledge-base.md")
llm = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL) if LLM_API_KEY else None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []

@app.get("/")
async def root():
    idx = static_dir / "index.html"
    return FileResponse(str(idx)) if idx.exists() else {"message": "毛选思维引擎 API", "docs": "/docs"}

@app.get("/api/status")
async def status():
    return {"rag": retriever is not None, "llm": llm is not None, "model": LLM_MODEL}

@app.get("/api/sources")
async def sources():
    if not retriever: return {"sources": []}
    seen = set()
    srcs = []
    for m in retriever._metadatas:
        k = (m.get("source",""), m.get("title",""))
        if k not in seen:
            seen.add(k)
            srcs.append({"source": m.get("source",""), "title": m.get("title",""), "date": m.get("date","")})
    return {"sources": srcs, "count": len(srcs)}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not llm:
        raise HTTPException(503, "LLM 未配置")
    rags = retriever.search(req.message, top_k=5) if retriever else []
    prompt = engine.build_prompt(req.message, rags)
    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":"你是毛泽东思想的学者。"},{"role":"user","content":prompt}],
        temperature=0.7, max_tokens=2000
    )
    return ChatResponse(
        answer=resp.choices[0].message.content,
        sources=[{"text":r.text[:200], "source":r.source, "title":r.title, "date":r.date, "score":r.score} for r in rags]
    )
```

- [ ] **Step 2: 提交**

```bash
git add web/app.py
git commit -m "feat: add FastAPI web service with /api/chat endpoint"
```

---

### Task 9: Web 前端聊天界面

**Files:**
- Create: `web/static/index.html`
- Create: `web/static/style.css`
- Create: `web/static/app.js`

- [ ] **Step 1: index.html** — 单页聊天布局，含建议问题按钮、输入框、消息区

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>毛选思维引擎</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="app">
    <header class="header"><h1>📖 毛选思维引擎</h1><span id="status">● 就绪</span></header>
    <main class="chat-container" id="chat">
        <div class="welcome">
            <h2>📚 毛选思维引擎</h2>
            <p>基于毛泽东选集四卷（约100万字）+ 诗词 + 毛式方法论框架</p>
            <button onclick="ask('什么是实事求是？')">什么是实事求是？</button>
            <button onclick="ask('矛盾分析法如何应用？')">矛盾分析法如何应用？</button>
            <button onclick="ask('调查研究的方法论')">调查研究的方法论</button>
        </div>
    </main>
    <footer class="input-area">
        <textarea id="msg" placeholder="输入你的问题..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"></textarea>
        <button onclick="send()">发送</button>
    </footer>
</div>
<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: style.css** — 毛选红色主题，响应式（略，约 150 行）

- [ ] **Step 3: app.js** — fetch `/api/chat`，渲染消息气泡+引用脚注

```javascript
async function send(){
    const m=document.getElementById('msg').value.trim();
    if(!m)return;
    document.querySelector('.welcome')?.remove();
    addMsg('user',m);
    document.getElementById('msg').value='';
    document.getElementById('status').textContent='● 思考中';
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
        const d=await r.json();
        let txt=d.answer||'';
        if(d.sources?.length){
            txt+='\n\n📚 引用来源：';
            d.sources.forEach((s,i)=>txt+=`\n[${i+1}] ${s.source}·${s.title} (${s.date}) 置信度:${(s.score*100).toFixed(0)}%`);
        }
        addMsg('assistant',txt);
    }catch(e){addMsg('assistant','❌ '+e.message)}
    document.getElementById('status').textContent='● 就绪';
}
function ask(t){document.getElementById('msg').value=t;send();}
function addMsg(role,txt){
    const d=document.createElement('div');
    d.className='message '+role;
    d.innerHTML=txt.replace(/\n/g,'<br>');
    document.getElementById('chat').appendChild(d);
    d.scrollIntoView();
}
```

- [ ] **Step 4: 提交**

```bash
git add web/static/
git commit -m "feat: add chat web frontend with source citations"
```

---

### Task 10: 集成 — Server Launcher 补全

**Files:**
- Modify: `run_server.py`（补全服务启动逻辑）

**Interfaces:**
- Produces: `python run_server.py` 一键启动

- [ ] **Step 1: 补全 run_server.py**

```python
"""启动毛选思维引擎 Web 服务。用法: python run_server.py [--port=8080] [--reload]"""
import sys, os
from dotenv import load_dotenv
load_dotenv()
import uvicorn

def main():
    port = int(os.getenv("WEB_PORT", "8000"))
    reload = "--reload" in sys.argv
    for a in sys.argv:
        if a.startswith("--port="): port = int(a.split("=")[1])
    print(f"毛选思维引擎 → http://localhost:{port}")
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=reload)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 集成测试**

```bash
python run_pipeline.py   # 完整管道：TXT解析 → 分块 → 向量化
python run_server.py --port=9999 &
sleep 3
curl http://localhost:9999/api/status
kill %1
```

- [ ] **Step 3: 提交**

```bash
git add run_server.py
git commit -m "feat: complete server launcher and end-to-end pipeline"
```

---

## 快速启动（用户指南）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API key
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 3. 运行数据管道（首次 ~5分钟，含模型下载）
python run_pipeline.py

# 4. 启动服务
python run_server.py

# 5. 打开浏览器 http://localhost:8000
```

## 完整文件结构

```
ChairManMao/
├── data/
│   ├── txt/              # 毛选 TXT 原文 (ChairManMao.zip 解压)
│   │   ├── 毛选第一卷/
│   │   ├── 毛选第二卷/
│   │   ├── 毛选第三卷/
│   │   ├── 毛选第四卷/
│   │   ├── 毛泽东诗词/
│   │   └── ...
│   ├── extracted/        # TXT解析后 JSON
│   └── chroma_db/        # ChromaDB 向量库
├── pipeline/
│   ├── txt_parser.py     # TXT解析 (替代pdf_parser)
│   ├── chunker.py        # 文本分块
│   └── embed_and_store.py # 向量化入库
├── rag/
│   └── retriever.py      # RAG混合检索 (Task 6)
├── reasoning/
│   ├── framework.py      # 推理引擎 (Task 7)
│   └── prompts/
│       ├── qa_with_reasoning.jinja2
│       └── pure_reasoning.jinja2
├── web/
│   ├── app.py            # FastAPI 服务 (Task 8)
│   └── static/           # 前端 (Task 9)
├── knowledge/
│   └── maozedong-knowledge-base.md  # book-to-skill 萃取 (Task 4)
├── requirements.txt
├── .env.example
├── run_pipeline.py       # 一键管道
└── run_server.py         # 一键启动
```
