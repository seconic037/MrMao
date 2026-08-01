# AGENTS.md — MrMao 主席模拟器

基于毛泽东著作（毛选四卷+文集+诗词+建国文稿+39个知识扩展，163万字语料）的 AI 对话系统。RAG 混合检索 + 两阶段推理（先想后说），移动端 Web 界面。

## Project

- 后端：Python 3.11 · FastAPI · Uvicorn
- 向量库：ChromaDB（cosine）+ BM25（jieba 分词 + rank-bm25），RRF 融合
- 嵌入：BAAI/bge-small-zh-v1.5（sentence-transformers，本地离线）
- LLM：DeepSeek API（deepseek-chat），经 openai SDK 调用
- 前端：原生 HTML/CSS/JS，移动端响应式，无框架
- 入口：`run_server.py` → `web/app.py`；离线管道：`run_pipeline.py`

## Commands

```bash
pip install -r requirements.txt          # 安装依赖
cp .env.example .env                     # 配置 OPENAI_API_KEY（DeepSeek）
python run_pipeline.py                   # 构建向量索引（首次 ~5 分钟）
python run_server.py                     # 启动服务 → http://localhost:8000
python run_server.py --port=8080 --reload  # 自定义端口 + 热重载
```

- 新增语料：TXT 放入 `data/txt/知识扩展/` 后重跑 `run_pipeline.py`
- 向量库重建失败：删除 `data/chroma_v2/` 后重跑管道
- 无测试套件（无 pytest 配置）

## Architecture

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| `pipeline/` | 离线数据处理：TXT解析→分块→向量化入库 | `txt_parser.py` `chunker.py` `embed_and_store.py` |
| `rag/` | 混合检索：向量 top-10 + BM25 top-5 → RRF 融合 → top_k | `retriever.py`（类 `Retriever`，`SearchResult` dataclass） |
| `reasoning/` | 两阶段推理：`think`（矛盾分析）→ `speak`（毛式表达） | `framework.py` `prompts/*.jinja2` |
| `web/` | FastAPI 服务 + 前端 | `app.py` `static/` |
| `data/` | 语料 `txt/`、解析结果 `extracted/`、向量库 `chroma_db|chroma_v2/`、日志 `logs/` | |

数据流：用户输入 → `Retriever.search`（RAG）→ think 提示（注入记忆）→ speak 提示 → 逐字输出。

## Conventions

- 环境变量全部经 `load_dotenv()` 读取，默认值写在代码中（`.env` 不提交）
- LLM 统一用 `openai` SDK + `LLM_MODEL`（默认 deepseek-chat），`base_url` 指向 DeepSeek
- 中文注释；中文标识符尽量避免，类/函数用英文
- 日志写入 `data/logs/session_*.jsonl`（JSON Lines，UTF-8）
- 疲劳度阈值：黄 21 轮 / 红 35 轮（`web/app.py` 常量）
- 会话状态存内存 + 磁盘 JSONL，重启时 `_restore_session()` 恢复
- 热点接口 `/api/hotspots` 用硬编码缓存兜底（10 分钟缓存）

## Notes

（留空，后续补充）
