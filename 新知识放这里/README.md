# 📥 新知识放这里

把 TXT 或 MD 文件丢进来，运行以下命令自动归类：

```bash
python tools/ingest_knowledge.py
```

| 文件类型 | 归到哪里 | 作用 |
|---------|---------|------|
| `.txt` | `data/txt/知识扩展/` | 语料库，需重跑 `python run_pipeline.py` |
| `.md` | `knowledge/framework/` | 思维框架，按主题合并，重启即生效 |

处理后文件移到 `_已处理/`，可随时清理。
