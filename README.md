# 📖 主席模拟器

> 基于毛泽东著作的 AI 对话系统。毛选四卷 + 文集 + 诗词 + 建国后文稿 + 马克思主义经典 + 世界历史，**153 万字**语料库。

## ✨ 功能

- 💬 **和老人家聊天** —— 两阶段对话引擎，先想后说，逐字打字效果
- 📚 **阅读著作** —— 分级目录，406 篇原文随时查阅
- 🔥 **百度热搜** —— 首页实时热点，点击看概述再决定要不要聊
- 📋 **聊天日志** —— 保存/删除/一键 AI 总结/可编辑标题
- 🫁 **疲劳度系统** —— 35 轮后主席犯困，🍵续茶 🚬递烟恢复
- 📱 **手机适配** —— 底部标签栏，微信式输入框，100dvh 安全区
- 🔌 **离线嵌入** —— sentence-transformers 本地运行，无需联网

## 🚀 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env          # 编辑填入 DeepSeek API key
python run_pipeline.py         # 构建向量索引（首次 ~5 分钟）
python run_server.py           # 启动 http://localhost:8001
```

手机同 WiFi 打开 `http://你的电脑IP:8001`。

## 📁 项目结构

```
├── data/txt/          # 语料库（毛选+文集+知识扩展）
├── pipeline/          # 离线数据处理
│   ├── txt_parser.py    # TXT 解析
│   ├── chunker.py       # 文本分块
│   └── embed_and_store.py  # 向量化入库
├── rag/               # RAG 检索
│   └── retriever.py     # 向量+BM25 混合检索
├── reasoning/         # 推理引擎
│   ├── framework.py
│   └── prompts/         # think + speak 两阶段模板
├── web/               # Web 服务
│   ├── app.py           # FastAPI
│   └── static/          # 前端
├── knowledge/         # 知识库模板
└── requirements.txt
```

## ⚙️ 技术栈

Python 3.11 · FastAPI · ChromaDB · sentence-transformers · DeepSeek API

## 📄 数据来源

- 毛选四卷：求是网 (qstheory.cn) 公开资料
- 毛泽东文集、建国后文稿：公开整理
- 知识扩展：马克思/恩格斯/列宁/斯大林著作摘要、四书五经、世界史等

## 📝 许可证

本项目代码采用 MIT 许可证。语料数据版权归属原作者及发布平台，仅供学习研究使用。
