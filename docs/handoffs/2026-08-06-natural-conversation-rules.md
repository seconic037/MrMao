# Handoff: 自然语言规则模块（手册 v3 已实现 + 第 7~11 层深化待推进）

> 从 MrMao 主席模拟器分叉 | 2026-08-06 22:03
> 状态：✅ 已完成（手册 v4 已产出并提交 `63397a1`；新层实现另起一轮，见 result.md）

## 任务目标

继续推进"自然语言规则"模块：当前手册 v3（第 0~6 层）已实现落地，待办是**深化手册第 7~11 层**（冲突/幽默/拒绝/沉默/情绪爆发），并可选择把新层实现进 prompt。

## 验收标准

- 手册 v4 包含第 0~11 层（新增 7~11 层草案已产出，待审阅并并入手册）
- 若实现新层：prompt 与意图模块相应更新，10 轮对话实测自然度不回退
- 具体实现范围与验收细节：**待子会话与用户确认**（用户上次选择"按序全补 + 理论标注"）

## 项目环境

- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- 技术栈: Python 3.11 · FastAPI · Uvicorn · ChromaDB（collection `maozedong-works` 6339 块）· DeepSeek API（deepseek-v4-flash）
- 启动方式: `python run_server.py` → `http://localhost:8000`
- 前端: 原生 HTML/CSS/JS（移动端响应式）
- 测试: unittest（`python tests/test_intent.py`、`python tests/test_topic_thread.py`、`python tests/test_kb_ops.py`）

## 涉及文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/superpowers/specs/2026-08-06-natural-conversation-redesign.md` | 修改 | 手册 v3 设计文档；待并入第 7~11 层变 v4 |
| `pipeline/intent.py` | 修改 | 意图判断器（双轴：情绪+需求，含 kind 细分）——新层可能需扩充信号 |
| `pipeline/topic_thread.py` | 修改 | 话题主线（Jaccard 切换检测） |
| `reasoning/prompts/think.jinja2` | 修改 | 意图驱动内心思考 + kind→策略映射 |
| `reasoning/prompts/speak.jinja2` | 修改 | 自然对话规则（第 0~5 层已落地）——新层如"拒绝/幽默"可能加约束 |
| `web/app.py` | 修改 | 三层记忆 + 意图注入主链路 |
| `tests/test_intent.py` `tests/test_topic_thread.py` | 修改 | 意图/话题单测（当前 15+3 用例） |

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
- 文档: `docs/superpowers/specs/2026-08-06-natural-conversation-redesign.md`（手册 v3 全量）· `.superpowers/sdd/progress.md`（进度+backlog）
- 记忆: `除非用户主动说-否则不上传-github`

## 完成时收尾

分支任务完成后，新会话须执行：
1. 将「改动摘要 + 测试结果 + 遗留问题」写入同目录 `2026-08-06-natural-conversation-rules-result.md`
2. 将本文档「状态」行改为 `✅ 已完成`
主会话回归时读取本目录（交接文档 + result.md）即可接手。
