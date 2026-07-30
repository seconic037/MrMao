# 主席模拟器

> 基于毛泽东著作的 AI 对话系统。毛选四卷 + 文集 + 诗词 + 建国后文稿，406 篇著作，约 100 万字。

## 功能

- 💬 **和老人家聊天**：两阶段对话引擎，先用毛选原文思考、再用毛式语言表达
- 🔥 **百度热搜**：首页展示实时热点
- 📚 **阅读著作**：分级目录，点击阅读原文
- 📋 **聊天日志**：保存/删除/一键 AI 总结

## 技术栈

Python 3.11 · FastAPI · ChromaDB · sentence-transformers · DeepSeek API

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API key
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API key

# 3. 构建向量索引（首次运行，约 5-10 分钟）
python run_pipeline.py

# 4. 启动
python run_server.py
# 浏览器打开 http://localhost:8001
# 手机同 WiFi 打开 http://你的电脑IP:8001
```

双击 `启动主席.bat` 即可一键启动。

## 项目结构

```
├── data/txt/          # 毛选 TXT 原文
├── pipeline/          # 离线数据处理
│   ├── txt_parser.py    # TXT 解析
│   ├── chunker.py       # 文本分块
│   └── embed_and_store.py  # 向量化入库
├── rag/               # RAG 检索
│   └── retriever.py     # 向量+BM25 混合检索
├── reasoning/         # 推理引擎
│   ├── framework.py
│   └── prompts/
├── web/               # Web 服务
│   ├── app.py           # FastAPI
│   └── static/          # 前端
├── knowledge/         # 知识库模板
└── run_pipeline.py / run_server.py
```
