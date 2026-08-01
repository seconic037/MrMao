# 📚 主席知识库补充指南

## 两条路

```
你给主席的新知识
    ↓
是整本书/长篇资料？ → .txt → 丢进 新知识放这里/ → python tools/ingest_knowledge.py → python run_pipeline.py
    ↓
是方法框架/蒸馏提炼？ → .md  → 丢进 新知识放这里/ → python tools/ingest_knowledge.py → 重启服务即可
```

## 快速上手

```bash
# 1. 把文件放到这里
#    TXT、MD 都行，放在 新知识放这里/

# 2. 自动归类
python tools/ingest_knowledge.py

# 3. 如果有 TXT，重建索引
python run_pipeline.py

# 4. 重启
python run_server.py
```

## 查看当前架构

```bash
python tools/ingest_knowledge.py    # 随时运行，无新文件时会打印当前架构
```

或浏览器访问 `http://localhost:8000/api/knowledge/structure`

## 规则

| 文件 | → | 目标 | 说明 |
|------|--|------|------|
| `.txt` | → | `data/txt/知识扩展/` | 切块→向量化→RAG 检索 |
| `.md` | → | `knowledge/framework/` | 按主题合并，注入 think prompt |
| 同名主题 MD | → | 追加合并到已有文件 | 经济学多本书蒸馏合并为 `经济学.md` |
| 处理完 | → | `新知识放这里/_已处理/` | 可手动清理 |

## 删除知识

删掉 `data/txt/知识扩展/` 或 `knowledge/framework/` 里的对应文件，重跑管道即可。
