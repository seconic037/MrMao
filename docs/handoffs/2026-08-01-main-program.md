# Handoff: MrMao 主程序回归（web 应用主线）

> 从 MrMao 项目分叉 | 2026-08-01 21:11

## 任务目标

回归 **MrMao 主席模拟器主程序**（web 应用）开发主线。kb-editor 分支任务已完结（v2 工作流编辑器 `7006087` + 闪退修复 `90576ee` + 介绍文档 `9a3c8ea`），主程序当前有一大笔**未提交成果**（场景系统 7 项改造 + 全产品实测修复，约 1172 行新增）待接续：提交、继续开发或按需调整。

## 项目环境

- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · ChromaDB（collection `maozedong-works` 6339 块）· DeepSeek API（deepseek-v4-flash）
- 前端: 原生 HTML/CSS/JS · 16 个极简 SVG 图标 · 前端版本号 `v=20260802c`
- 启动: `python run_server.py` → `http://localhost:8000`
- 管道: `python run_pipeline.py`（重建向量库，3-10 分钟）
- **服务器当前未运行**（2026-08-01 21:11 检测：8000 无监听），接手先启动

## 功能模块（主程序现状，全部已实现）

| 模块 | 关键文件 | 状态 |
|------|---------|------|
| 基础对话 | `reasoning/framework.py` + `speak/think.jinja2` | ✅ 两阶段推理+疲劳度 |
| 场景系统 | `pipeline/scenes.py` `game_engine.py` | ✅ 4 场景（shuwu/keting/xiaolu/shuxia）+ 游戏化 |
| 场景 UI | `web/static/`（4 WebP 背景 `backgrounds/` `web/static/img/`）+ 遮罩 + 单标签居中 | ✅ |
| 场景开关 | 底部 4TAB（首页/日志/场景/阅读） | ✅ |
| 考考你 | 弹窗出题 | ✅ |
| 日志面板 | 半屏弹出 + 两行预览 + 查看 + 继续聊 | ✅ |
| 热点 | `pipeline/hotspot_fetcher.py` + 百度实时 + 娱乐过滤 + 🔄刷新 | ✅ |
| 知识库体系 | `新知识放这里/` + `tools/ingest_knowledge.py` + `rag/knowledge_usage.py` + `knowledge/framework/` | ✅ |
| 阅读分级目录 | `/api/articles` `/api/catalog` `/api/read` | ✅ |
| Windows 服务 | `tools/nssm/` + `install_service.bat` | ⚠️ 待测 |

主程序 API（26 个）：`/api/chat` `/api/scene/*`（get/set/suggest/exit/transition/topic）`/api/hotspots*` `/api/logs*` `/api/session*`（save/discard/status/summarize/title）`/api/compact` `/api/read` `/api/articles` `/api/catalog` `/api/knowledge/structure` `/api/greeting` `/api/status`。

## 当前未提交改动（回归主任务的起点）

**已跟踪文件的修改**（约 1172 insertions / 132 deletions）：

| 文件 | 改动规模 | 内容 |
|------|---------|------|
| `web/static/app.js` | +673 | 场景 UI、日志面板、考考你、退出倒计时、承接截断去残字、`resumeFromLog` 修复 |
| `web/app.py` | +374 | 场景/热点/日志/会话接口 |
| `web/static/style.css` | +93 | 场景背景、退出浮层、删 chat-links 残留与重复定义 |
| `web/static/index.html` | +80 | 4TAB 布局、版本号统一 `v=20260802c` |
| `reasoning/prompts/speak.jinja2` | +35 | 场景感知表达 |
| `reasoning/framework.py` | +28 | 场景/疲劳接入 |
| `README.md` | +16 | **全产品实测修复记录（他人未提交内容，改 README 需精确 stage 自己的 hunk）** |
| `reasoning/prompts/think.jinja2` | +4 | 场景提示 |
| `.gitignore` | +1 | 忽略规则 |

**未跟踪新增**：

| 路径 | 说明 |
|------|------|
| `pipeline/scenes.py` `game_engine.py` `hotspot_fetcher.py` | 场景系统/游戏引擎/热点抓取 |
| `rag/knowledge_usage.py` | 知识库使用统计 |
| `knowledge/framework/` | 框架层新知识（.md） |
| `backgrounds/` `web/static/img/` | 4 场景 WebP 背景图 |
| `data/txt/知识扩展/` 35 个新 TXT | 新语料（**未跑 run_pipeline.py，向量库未含**） |
| `docs/branch-scenes-game.md` `docs/scene-system-design.md` `docs/scene-bg-prompts.txt` | 场景系统设计文档 |
| `AGENTS.md` `KNOWLEDGE.md` | 项目/知识库指南 |

## 活跃问题（2026-08-01 session-handoff 基线，已全部 ✅）

- 日志「继续聊」返回空 — 已修复（版本号统一）+ Chrome 实测通过
- 承接截断残字 — 已修复（去尾标点+省略号）
- NPC 场景建议 5 分钟+只问一次 — 已修复
- 退出倒计时 CSS 重复定义 — 已清理
- `chat-links` CSS 残留 — 已删

## 约束

- **不推 GitHub**（除非用户明确说）；本地 commit 可选
- 不扫 `data/chroma_*` `data/extracted` `聊天记录/` `.env` `tools/nssm`
- 所有文件 UTF-8；中文注释
- README.md 有他人未提交改动，改 README 需精确 stage（用 `git apply --cached` 补丁）
- `tools/` 被 .gitignore 忽略，`tools/` 下新增文件需 `git add -f`
- 知识库编辑器（kb-editor）分支已完结，勿把主程序改动与其混提

## 建议加载的 Skill/文档

- Skill: `handoff-seconic`（交接）· `maoxuan-workbench`（毛选方法论）· `maozedong-wenxian`（文献知识）
- 文档: `docs/handoffs/2026-08-01-session-handoff.md`（主程序状态基线）· `docs/scene-system-design.md`（场景设计）· `docs/branch-scenes-game.md`（分支规划）· `README.md`
- 记忆: `kb-editor-桌面编辑器已上线`（分支已完结）· `除非用户主动说-否则不上传-github`
