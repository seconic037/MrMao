# 长期记忆持久化设计（S5，方案 A：单会话跨重启恢复）

> 日期：2026-08-06
> 状态：📝 方案讨论产出——待审阅，未实现
> 承接：v3 §7 范围外（原"不做长期记忆持久化"）→ 用户 2026-08-06 决定推进，范围选 A

## 1. 设计目标

解决核心痛点：**重启后主席"忘了"之前聊的话题线**——`_restore_session()` 目前只重建 memories（且不含 emotion、截断 60/80 字），raw_buffer 和 topic_thread 完全未恢复。

## 2. 现状问题（`web/app.py:_restore_session`）

| 记忆层 | 会话内 | 重启恢复现状 |
|--------|--------|-------------|
| 1 内容缓冲 raw_buffer | ✅ | ❌ 未恢复 |
| 2 摘要+情绪 memories | ✅ | ⚠️ 重建但不含 emotion、截断 60/80 字 |
| 3 话题主线 topic_thread | ✅ | ❌ 未恢复（topic_line 从零开始） |

违反：5.1 接续感 / 5.2 推进（重启后话题断片）。

## 3. 方案 A 设计

### 3.1 存储

在现有 `session_*.jsonl`（`data/logs/`）中，每轮对话追加一个**元数据条目**：

```json
{"role": "_meta", "type": "memory_snapshot", "ts": "...", "data": {
  "raw_buffer": [{"question": "...", "answer": "..."}],
  "memories": [{"question": "...", "summary": "...", "emotion": "negative"}],
  "topic_thread": [{"topic": "...", "brief": "...", "round": 3}],
  "session_id": "..."   // 预留扩展位：B 方案多会话归档用
}}
```

- **时机**：每轮对话后（与 `_flush_log()` 同步）追加一条 `_meta` 条目
- **不引入新文件**：直接复用现有 JSONL 日志（session_log 已实时刷盘）
- **兼容**：旧日志无 `_meta` 条目 → `_restore_session()` 跳过，行为等同现状

### 3.2 恢复

`_restore_session()` 读取最新日志时：
1. 扫到 `role == "_meta"` 的条目 → 取 `data` 恢复 raw_buffer / memories / topic_thread
2. 无 `_meta` → 退回现有重建逻辑（memories 截断重建）
3. 恢复后 topic_thread 重建 → topic_line 接续

### 3.3 改动清单

| 文件 | 改动 |
|------|------|
| `web/app.py` | ①每轮后写 `_meta` 条目（复用 `_write_log`）②`_restore_session()` 优先恢复三层 ③topic_thread/raw_buffer 全局变量恢复 |
| `web/app.py` | 会话切换/恢复入口（`/api/resume` 等）若复用日志文件，同步恢复三层 |

### 3.4 测试

- `tests/test_session_restore.py`（新）：写日志 → 重启恢复 → 断言三层结构正确
- 现有 `test_kb_ops.py` 回归（不动日志格式主链路）

## 4. 范围外（后续可加）

- **B**：旧会话一句话摘要 + 多会话列表（存 `session_id` 已预留）
- **C**：跨会话按主题召回（需 RAG 改造，风险高，明确后置）
- 不重做会话日志格式（保持 JSONL 兼容）

## 5. 待确认

- [ ] `_meta` 条目追加时机：每轮后追加 vs 会话结束归档？（建议每轮后——意外退出不丢，符合现有 `_flush_log` 哲学）
- [ ] `_meta` 是否参与 `session_log` 的消息渲染（前端日志展示需过滤 `_meta`）