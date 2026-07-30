---
name: ai-diary
description: 自动记录AI交互过程，生成多平台适配的自媒体日记内容
runAs: subagent
allowed-tools: [read_file, write_file, grep, web_fetch, glob]
---

# ai-diary — AI自媒体日记助手

## 概述
自动记录用户与 AI Agent（Reasonix + DeepSeek）的交互过程，生成多平台适配的自媒体内容。
定位：日记型自媒体 — 「我和AI的日常」

## 日记存储
所有日记文件存放在项目 `diary/` 目录下：
- 单日日记：`diary/YYYY-MM-DD.md`
- 周报：`diary/weekly/YYYY-Www.md`
- 草稿：`diary/drafts/{platform}/`

## 命令接口

用户通过以下命令与技能交互：

| 命令 | 功能 |
|------|------|
| `/diary` | 查看最近日记摘要 |
| `/diary today` | 生成今日日记草稿 |
| `/diary weekly` | 生成本周周报 |
| `/diary list` | 浏览历史日记列表 |
| `/diary publish` | 输出多平台适配版本 |
| `/diary endday` | 生成当日摘要+结束记录 |

### 命令解析规则
1. 检查用户消息是否以 `/diary` 开头
2. 提取后续参数确定具体命令
3. 匹配到对应命令则执行相应逻辑
4. 未匹配则显示帮助信息
