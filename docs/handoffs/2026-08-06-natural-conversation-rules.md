# Handoff: 自然语言规则模块（✅ 已完成：手册 v5 + 主席配置 + S1~S8 全实现）

> 从 MrMao 主席模拟器分叉 | 2026-08-06 22:03
> 状态：✅ 已完成（分支由后续会话完整推进——手册 v5 已发布、S1~S8 全部实现；最终记录见 `2026-08-06-natural-conversation-rules-result.md`）

## 任务目标

✅ **已完成**（2026-08-06 后续会话完整推进）：手册 v3 → **v5**（通用自然对话规则手册，0~12 层去绑定抽象）+ 主席配置（第一个实例），并实现 S1~S8 全部代码（意图/场景信号/性格层/术语随场合/长期记忆/冷场挂起/特殊场景应对）。

## 验收标准

✅ **已达成**：
- 手册 v5 含 0~12 层 + 三大原则总纲 + 机制配置接口（取代 v3/v4 规则部分）
- S1~S8 全部实现，62 unittest 全过
- 10 轮跨意图实测（求答案/求安慰/冲突/闲聊）自然度通过、0 术语外露
- 唯一遗留：用户自做的更长时间真实对话体验（见 result.md）

## 项目环境

- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- 技术栈: Python 3.11 · FastAPI · Uvicorn · ChromaDB（collection `maozedong-works` 6339 块）· DeepSeek API（deepseek-v4-flash）
- 启动方式: `python run_server.py` → `http://localhost:8000`
- 前端: 原生 HTML/CSS/JS（移动端响应式）
- 测试: unittest（`python tests/test_intent.py`、`python tests/test_topic_thread.py`、`python tests/test_kb_ops.py`）

## 涉及文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/superpowers/specs/2026-08-06-natural-conversation-rules-v5.md` | 修改 | **通用自然对话规则手册 v5**（最终版，取代 v3/v4 规则部分） |
| `docs/superpowers/specs/2026-08-06-mao-config.md` | 修改 | 主席配置（第一个实例：10 特质×情境 + C1~C8 裁定） |
| `docs/superpowers/specs/2026-08-06-scene-signal-detector-design.md` | 修改 | 场景信号检测器（S3+S4+S6）+ 性格层实现 |
| `docs/superpowers/specs/2026-08-06-long-term-memory-design.md` | 修改 | 长期记忆持久化（S5，_meta 快照） |
| `pipeline/intent.py` | 修改 | 意图判断器（情绪+需求+situation/arousal/scene 信号） |
| `pipeline/topic_thread.py` | 修改 | 话题主线（Jaccard 切换检测） |
| `reasoning/prompts/think.jinja2` | 修改 | 意图驱动内心思考 + 场景/情境/唤醒度注入 + 特质选择 |
| `reasoning/prompts/speak.jinja2` | 修改 | 自然对话规则（0~12 层）+ 特殊场景应对 + 术语随场合 |
| `web/app.py` | 修改 | 三层记忆 + 意图注入 + 长期记忆快照 |
| `tests/test_intent.py` `tests/test_topic_thread.py` | 修改 | 意图/话题单测（62 用例全过） |

## 当前变更

自然语言重构已全部提交（master，13 commits，`218e589..3dc03ed`），**工作区干净**：
- 新增 `pipeline/intent.py`、`pipeline/topic_thread.py` + 测试
- 重写 `think.jinja2`、`speak.jinja2`（意图驱动 + 自然规则 + 禁术语）
- `web/app.py` 接入三层记忆（raw_buffer 2轮 / memories 5条含emotion / topic_thread 全程）+ 意图判断在 think 前
- 场景话题 prompt 自然化
- 未跟踪文件：`backgrounds/`、`data/` 新语料等（非本模块，勿动）

## 约束

- 除非用户明确说，否则不推 GitHub / 不发布到外部（本地 commit 可选）
- 不扫 `data/` `聊天记录/` `tools/` `.env`
- 所有文件 UTF-8；中文注释；类/函数用英文
- 测试用 unittest（项目无 pytest）
- 在 master 直接开发（项目惯例，用户已确认）

## 决策记录

- **手册深化方向（用户已选）**：按序全补第 7~11 层（冲突应答/幽默玩笑/拒绝边界/沉默冷场/情绪爆发），每层带理论标注
- 第 7~11 层**草案已产出**（在上一条会话讨论中）：每层 4~5 条规则，理论出处已标注（Goffman 面子 / Brown&Levinson / Rogers / Martin 幽默 / House 社会支持 等）
- **待用户审阅**：草案中有一个规则冲突待定——8.4"情绪低时不幽默" vs 7.5"冲突时玩笑化解"，两处可能打架，需在并入手册时裁定
- 台账 `docs/../.superpowers/sdd/progress.md` 含全部 minor backlog（如 topic_thread 节点无上限/summary 文案重复、意图词库误报等）

## 建议加载的 Skill/文档

- Skill: `maozedong-wenxian`（文献知识）· `maoxuan-workbench`（毛选方法论）
- 文档: `docs/superpowers/specs/2026-08-06-natural-conversation-rules-v5.md`（手册 v5 最终版）· `docs/superpowers/specs/2026-08-06-mao-config.md`（主席配置）· `docs/handoffs/2026-08-06-natural-conversation-rules-result.md`（分支最终记录）
- 记忆: `除非用户主动说-否则不上传-github`

## 完成时收尾

分支任务完成后，新会话须执行：
1. 将「改动摘要 + 测试结果 + 遗留问题」写入同目录 `2026-08-06-natural-conversation-rules-result.md`
2. 将本文档「状态」行改为 `✅ 已完成`
主会话回归时读取本目录（交接文档 + result.md）即可接手。
