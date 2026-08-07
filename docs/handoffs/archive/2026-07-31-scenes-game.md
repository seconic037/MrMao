# Handoff: MrMao 场景系统 + 游戏化互动
> 从 MrMao 项目分叉 | 2026-07-31 23:10

## 任务目标
为主席模拟器增加四个互动场景（🏢办公室 🛋️客厅 🌳办公地外 🏡家周围）和游戏化问答（主席出题考用户），新会话独立推进开发。

## 项目环境
- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · ChromaDB · DeepSeek API (`deepseek-v4-flash`)
- 前端: 原生 HTML/CSS/JS
- 启动: `python run_server.py` → `http://localhost:8000`
- 知识库: `data/txt/知识扩展/` 74 TXT, 480 篇, 5233 块
- 日志: `聊天记录/session_*.jsonl` (实时刷盘)

## 涉及文件
| 文件 | 类型 | 职责 |
|------|------|------|
| `pipeline/scenes.py` | 新增 | 场景定义、氛围文本、专属动作库 |
| `pipeline/game_engine.py` | 新增 | 题库(~20题)、评分、赞美/纠错语库 |
| `web/app.py` | 修改 | +4 接口: 场景读写/出题/答题, speak 注入场景 |
| `web/static/index.html` | 修改 | 场景标签行 + 游戏问答弹窗 |
| `web/static/app.js` | 修改 | 场景切换 + 游戏交互逻辑 |
| `web/static/style.css` | 修改 | 场景标签 + 游戏面板样式 |
| `reasoning/prompts/speak.jinja2` | 修改 | 场景感知的氛围文本 + 动作约束 |

## API 接口
| 接口 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/scene/set` | POST | `scene: str` | `{scene, atmosphere}` |
| `/api/scene/get` | GET | — | `{scene, atmosphere}` |
| `/api/game/question` | POST | — | `{q, opts[]}` |
| `/api/game/answer` | POST | `idx, answer` | `{correct, msg, streak}` |

## 前端交互
- 场景标签: `stats-bar` 下方, 4 个标签切换
- 游戏面板: 弹窗出题→三选一→显示结果, 连对3题特殊表扬
- 底部操作栏: 新增 🔔 按钮

## 约束
- 不推 GitHub (除非用户明确要求)
- 不改变 RAG/think/日志系统
- 新增文件隔离, 修改文件仅追加
- 场景状态存内存, 重启默认办公室
- 不扫 `data/` `聊天记录/` `tools/` `.env`

## 建议加载的 Skill/文档
- `docs/branch-scenes-game.md` — 完整分支规划
- `docs/scene-system-design.md` — 场景系统设计 (如有)
- AGENTS.md — 项目架构描述
