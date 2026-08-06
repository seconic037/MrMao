# Handoff: AWS 云端部署（ChairManMao 上云）
> 从 MrMao 主席模拟器 分叉 | 2026-08-07 05:10
> 状态：⏸️ 已搁置（2026-08-07 用户决定本地使用，详见同目录 result 文档；未完成，非 ✅）

## 任务目标
参照「AI店长」项目已落地的 AWS 部署方案（EC2 + `deploy.sh` + systemd），把主席模拟器（ChairManMao）部署到**新开独立 EC2 实例**，实现完整功能公网访问。

## 验收标准
（用户已确认 2026-08-07）
- 新开**独立 EC2 实例**（与 AI店长 的 `43.196.75.2` 完全隔离，不影响其生产服务）
- 云端公网可访问网页，**完整功能可用**：对话（RAG 混合检索 + 两阶段推理）、向量库、热搜、场景切换、日志面板
- **手机外网**可打开并正常聊天
- 部署流程参照 AI店长：打包 → 上传 → 恢复 .env → 更新依赖 → systemd 服务 → health 验证

## 项目环境
- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- 技术栈: Python 3.11 · FastAPI · Uvicorn · ChromaDB（cosine，collection `maozedong-works` 6339 块）
- 向量库路径: `data/chroma_v3/`（**实际以 `.env` 的 `CHROMA_PERSIST_DIR` 为准**；AGENTS.md 旧文写 chroma_v2 已修正）
- 嵌入模型: `BAAI/bge-small-zh-v1.5`（sentence-transformers，本地离线，模型缓存 ~130MB）
- LLM: DeepSeek API（`deepseek-v4-flash`，经 openai SDK）
- 关键词检索: jieba 分词 + rank-bm25（RRF 融合）
- 前端: 原生 HTML/CSS/JS · 移动端响应式 · 四 Tab（首页/日志/场景/阅读）· 版本号 v20260806
- 启动: `python run_server.py` → `http://localhost:8000`（默认 host 需按云端外网访问适配）
- 数据规模: 445 篇著作 + 76 知识扩展（35 个 `_plus.txt` 已入库），452 万字

## 涉及文件
| 文件 | 类型 | 说明 |
|------|------|------|
| `deploy.sh` | 新增 | 参照 AI店长 版编写 ChairManMao 专属部署脚本（打包/上传/重启/验证） |
| `run_server.py` | 可能修改 | 入口；确认云端绑定 `0.0.0.0` 与端口参数化 |
| `web/app.py` | 可能修改 | FastAPI 服务；host/port、CORS、外网访问适配 |
| `requirements.txt` | 可能修改 | 云端依赖清单核对 |
| `.env.example` | 修改 | 云端所需环境变量模板（DeepSeek key、CHROMA_PERSIST_DIR、host/port） |
| `data/chroma_v3/` | 数据 | 向量库（sqlite 111MB+），上传 vs 云端重建二选一，见下方待决 |
| `data/txt/` | 数据 | 语料源（445 篇 + 76 扩展），若云端重建管道则需上传 |
| `.gitignore` | 参考 | 已忽略 `data/chroma_v*/`、`data/extracted/`、`data/logs/`、`data/chunks.jsonl` |

## 当前变更
- git HEAD `7461eb9`（快照导出提交），工作区有未跟踪文件：35 个 `data/txt/知识扩展/*_plus.txt`（已入库 v3）、`backgrounds/`、`data/baidu_hot.json`
- 部署前需确认这些未跟踪内容是否随包上传（语料已入库，若上传库则 txt 可不传）

## 约束
- **除非用户明确说，否则不推 GitHub / 不发布到外部公开渠道**；本任务上传目标是自己的 AWS 服务器，属部署行为
- **新开独立 EC2**，绝不动 AI店长 的服务器（`43.196.75.2`）及其 systemd 服务（ai-manager / ai-manager-c1）
- **隐私**：`.env` 含 DeepSeek API key，禁止打包进上传内容；key 在服务器端单独配置（参照 AI店长 deploy.sh 的 .env 备份/恢复机制）
- SSH key 路径见 AI店长 项目 `deploy.sh` 顶部的 `KEY` 变量（本文档不复制该路径）
- 不扫敏感/大数据目录：`data/txt/` `data/chroma_v*/` 仅作打包决策用，不做全量内容分析
- 在独立分支/独立区域工作，勿动 master 主线逻辑

## 决策记录
（2026-08-07 用户确认）
1. **部署目标 = 新开独立 EC2 实例**：与 AI店长 隔离，按 ChairManMao 规格（内存/磁盘）单独配置，不影响 AI店长 生产服务
2. **验收标准 = 完整功能可公网访问**：对话/向量库/热搜/场景/日志全可用，手机外网可聊

## 新会话待办（按优先级）
1. **摸清 AI店长 部署方案细节**：读 `C:\Users\68090\Desktop\AI店长\deploy.sh`（EC2 host/key 变量、打包范围、systemd 服务名、health 验证方式）+ 服务器端 `ai-manager.service` 单元文件写法
2. **确认/创建独立 EC2**：规格建议内存 ≥2GB（嵌入模型 + ChromaDB 常驻）、磁盘 ≥10GB；安全组开放 8000 端口
3. **决策向量库策略**：上传 `data/chroma_v3/`（111MB，快）vs 云端重跑 `run_pipeline.py`（需 bge 模型下载 + 3-10 分钟）；上传库需保证路径与 .env 一致
4. **编写 ChairManMao 版 deploy.sh + systemd 单元**：参照 AI店长 模板，服务名如 `chairmanmao`，端口 8000
5. **云端 .env 配置**：DeepSeek key、`CHROMA_PERSIST_DIR`、host/port
6. **端到端验证**：公网 URL 打开 → 发消息验证 RAG/推理 → 热搜/场景/日志 → 手机外网实测
7. 形成项目计划文档（本次交接即计划输入），执行前如遇资源/费用/账号权限等需用户拍板项，用 `ask` 确认

## 建议加载的 Skill/文档
- Skill: `deploy`（一键部署流程，指向 AI店长 deploy.sh）· `inherit-seconic`（项目继承）· `maozedong-wenxian` / `maoxuan-workbench`（本项目知识域）
- 文档: AI店长 `deploy.sh` · 本继承快照 `docs/inherit/current-snapshot.md` · 手册 v5 `docs/superpowers/specs/2026-08-06-natural-conversation-rules-v5.md`
- 记忆: `除非用户主动说-否则不上传-github`（约束同上）

## 完成时收尾
分支任务完成后，新会话须执行：
1. 将「改动摘要 + 部署结果 + 遗留问题」写入同目录 `2026-08-07-aws-cloud-deploy-result.md`
2. 将本文档「状态」行改为 `✅ 已完成`
主会话回归时读取本目录（交接文档 + result.md）即可接手。
