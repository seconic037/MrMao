# ai-diary: AI自媒体日记助手 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 ai-diary Reasonix Skill，自动记录AI交互过程并生成多平台适配的自媒体内容

**Architecture:** 一个 runAs=subagent 的 Reasonix Skill，通过指令模式匹配（/diary 前缀）响应不同命令，将日记数据以 Markdown 文件存储在 `diary/` 目录下，输出多平台适配版本

**Tech Stack:** Reasonix Skill 系统（Markdown 指令）、web_fetch（domestic-reach 联动）、文件 IO（日记存储）

## Global Constraints

- 所有日记文件为纯 Markdown 格式，存放在 `diary/` 目录下
- 不依赖外部数据库或 API（除 domestic-reach 联动外）
- 产出文件路径固定，方便被外部脚本（如「下班」指令）引用
- 遵循既有项目的技能风格（参考 `.reasonix/skills/domestic-reach/SKILL.md`）
- subagent 模型统一使用 deepseek-v4-flash

---

## 文件结构

```
.reasonix/skills/ai-diary/
  └── SKILL.md                    # 主技能文件（全部逻辑在此）

diary/
  ├── YYYY-MM-DD.md               # 单日日记
  ├── weekly/
  │   └── YYYY-Www.md             # 周报
  └── drafts/
      ├── xiaohongshu/            # 小红书适配
      ├── bilibili/               # B站脚本
      └── wechat/                 # 公众号长文
```

---

### Task 1: 创建 ai-diary Skill 骨架

**Files:**
- Create: `.reasonix/skills/ai-diary/SKILL.md`

**Interfaces:**
- Consumes: 设计规格文档 `docs/superpowers/specs/2026-07-31-ai-diary-media-design.md`
- Produces: 可调用的 `ai-diary` Skill，支持 `/diary` 指令模式匹配

- [ ] **Step 1: 编写 SKILL.md 基础结构和数据源配置**

写入 Skill 的 frontmatter、概述、数据源配置和采集逻辑部分。

```markdown
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
```

- [ ] **Step 2: 编写命令匹配逻辑**

写入技能如何识别和处理不同的 `/diary` 命令。

```markdown
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
```

- [ ] **Step 3: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: create ai-diary skill skeleton"
```

---

### Task 2: 实现日记条目结构和自动记录机制

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`（追加日记条目逻辑）

**Interfaces:**
- Consumes: 会话中产生的任务描述、工具调用、关键产出
- Produces: 标准化的日记条目格式

- [ ] **Step 1: 编写日记条目结构定义**

```markdown
## 日记条目结构

每条日记包含以下字段，存入 `diary/YYYY-MM-DD.md`：

```markdown
# 2026-07-31 日记

## 📋 任务摘要
[一句话描述今天让AI做了什么]

## 🛠 工具调用
- [MCP/技能名]：[用途说明]

## 📦 关键产出
- [产出描述]

## 💬 AI评价
[从AI视角看这件事的价值/有趣之处]

## 📱 适合平台
- 小红书 ✅/❌
- B站 ✅/❌
- 公众号 ✅/❌
```

- [ ] **Step 2: 编写自动记录逻辑说明**

```markdown
## 自动记录机制

当对话结束时，技能自动执行以下步骤：
1. 回顾本次会话中的任务、工具调用和产出
2. 提取关键信息填入日记条目模板
3. 追加写入 `diary/YYYY-MM-DD.md`
4. 如果当日文件已存在，追加新条目而非覆盖

### 触发时机
- 用户主动调用 `/diary` 系列命令时
- 整合进「下班」指令时（通过 `/diary endday`）
- 用户明确要求"记录一下"时
```

- [ ] **Step 3: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: add diary entry structure and auto-recording"
```

---

### Task 3: 实现 `/diary` 和 `/diary today`

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`

**Interfaces:**
- Produces: `diary/YYYY-MM-DD.md` 文件创建和读取

- [ ] **Step 1: 编写 `/diary`（查看摘要）逻辑**

```markdown
### /diary — 查看最近日记摘要

行为：
1. 使用 `glob` 查找 `diary/*.md` 文件
2. 按文件名排序，取最近 5 条
3. 用 `read_file` 读取每个文件的前 10 行（标题区）
4. 输出摘要列表

输出格式：
```
📖 最近日记
━━━━━━━━━━━━━━━━━━
1. 2026-07-31 — [标题]
   工具: xxx | 产出: xxx
2. 2026-07-30 — [标题]
   ...
```
```

- [ ] **Step 2: 编写 `/diary today`（生成今日日记）逻辑**

```markdown
### /diary today — 生成今日日记草稿

行为：
1. 检查 `diary/2026-07-31.md` 是否存在
2. 如果存在，读取并显示已有内容，询问是否追加
3. 如果不存在，回顾本次会话信息，生成新日记
4. 使用 `write_file` 写入文件

生成逻辑：
1. 回顾会话历史：用户提出了什么任务？用了哪些工具？产出了什么？
2. 按日记条目模板结构化输出
3. 从AI视角添加评价（这件事为什么有意思？）
4. 标记适合发布的平台
5. 写入文件后提示用户

输出示例：
```
✅ 今日日记已生成 → diary/2026-07-31.md

📋 今日摘要：
1. 采集国内科技热点并生成选题报告
2. 用 domestic-reach 分析了小米澎程系列热度

💡 可发布内容：这条「用AI做热点选题」的体验适合发小红书
```
```

- [ ] **Step 3: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: implement /diary and /diary today commands"
```

---

### Task 4: 实现 `/diary list` 和 `/diary weekly`

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`

- [ ] **Step 1: 编写 `/diary list` 逻辑**

```markdown
### /diary list — 浏览历史日记列表

行为：
1. 使用 `glob` 查找 `diary/*.md`（排除 weekly/ 和 drafts/）
2. 按日期倒序排列
3. 显示分页列表（每页 10 条）
4. 支持参数：`/diary list --page=2` 翻页

输出格式：
```
📚 日记历史（共 23 条）
━━━━━━━━━━━━━━━━━━
2026-07-31  [标题]
2026-07-30  [标题]
...
第 1/3 页  → 使用 /diary list --page=2 翻页
```
```

- [ ] **Step 2: 编写 `/diary weekly` 逻辑**

```markdown
### /diary weekly — 生成本周周报

行为：
1. 计算当前周数（ISO 周数）
2. 读取本周所有日记文件（周一至周日）
3. 汇总本周所有任务、工具、产出
4. 统计：任务数量、工具使用频率、产出类型分布
5. 生成周报写入 `diary/weekly/YYYY-Www.md`

输出格式：
```
📊 2026年第31周周报
━━━━━━━━━━━━━━━━━━
📋 本周共完成 12 个任务
🛠 常用工具：domestic-reach(5次)、hotnews-mcp(4次)、web_fetch(3次)

🏆 本周亮点：[最有意思的任务]
📱 适合发布：[推荐本周值得发的内容]
```
```

- [ ] **Step 3: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: implement /diary list and /diary weekly"
```

---

### Task 5: 实现 `/diary publish`（多平台输出）

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`

- [ ] **Step 1: 编写小红书适配逻辑**

```markdown
### /diary publish — 输出多平台适配版本

#### 📱 小红书（图文笔记）

适配规则：
- 标题：提问式/观点式 + emoji，不超过 20 字
- 正文：800-1500 字，口语化，用「❶❷❸」分点
- 配图建议：在文中标注 `[截图：XXX]`
- 结尾加话题标签 #AI日记 #AI工具

输出路径：`diary/drafts/xiaohongshu/YYYY-MM-DD-标题.md`
```

- [ ] **Step 2: 编写 B站/抖音脚本适配逻辑**

```markdown
#### 🎬 B站/抖音（视频脚本）

适配规则：
- 时长：3-5 分钟
- 结构：
  - Hook（0:00-0:15）：抛出一个问题或惊人结果
  - 引入（0:15-0:45）：今天让AI做了什么
  - 过程（0:45-3:00）：展示操作过程/关键步骤
  - 结果（3:00-4:00）：展示AI的产出
  - 总结（4:00-5:00）：这件事的价值 + 下期预告
- 格式：分镜/口播稿

输出路径：`diary/drafts/bilibili/YYYY-MM-DD-标题.md`
```

- [ ] **Step 3: 编写公众号长文适配逻辑**

```markdown
#### 📖 公众号（长文）

适配规则：
- 标题：信息量大，含关键词
- 结构：导语 → 正文(2-3个小标题分段) → 总结
- 字数：2000-4000 字
- 风格：可加入深度思考、方法论、背景介绍
- 适合分享AI使用心得

输出路径：`diary/drafts/wechat/YYYY-MM-DD-标题.md`
```

- [ ] **Step 4: 编写 `/diary publish` 路由逻辑**

```markdown
### /diary publish 执行流程

1. 用户执行 `/diary publish`
2. 列出最近 5 条日记让用户选择要发布哪条
3. 用户选择后，询问要生成哪个平台的版本
4. 按对应平台的适配规则生成内容
5. 写入 `diary/drafts/{platform}/` 目录
6. 提示用户草稿已生成，可手动复制发布

支持参数：
- `/diary publish --today`  直接发布今日日记
- `/diary publish --all`    生成所有平台的版本
- `/diary publish --platform=xiaohongshu`  指定平台
```

- [ ] **Step 5: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: implement /diary publish with multi-platform output"
```

---

### Task 6: 实现 `/diary endday` 与「下班」指令整合

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`

- [ ] **Step 1: 编写 `/diary endday` 逻辑**

```markdown
### /diary endday — 下班总结

行为：
1. 自动执行 `/diary today` 生成今日日记（如果还未生成）
2. 在日记末尾追加「🔚 下班总结」区块
3. 统计：今日任务数、耗时、亮点
4. 标记：今日最值得发布的内容
5. 输出简短总结

输出格式：
```
🔚 下班总结
━━━━━━━━━━━━━━━━━━
📋 今日完成 3 个任务
🏆 亮点：用 domestic-reach 做了热点选题分析

📱 推荐发布：
  这条适合发小红书 → 体验分享
```

整合说明：
- 此命令设计为「下班」指令的最后一个步骤
- 执行后输出短摘要，不打断下班流程
- 日记文件已自动保存，明日可继续编辑
```

- [ ] **Step 2: 编写「下班」指令整合说明**

```markdown
## 「下班」指令整合

### 整合方式
在现有的「下班」指令流程末尾添加以下内容：

```
最后调用 ai-diary 的 /diary endday 功能：
1. 回顾本日所有会话
2. 生成今日日记
3. 输出下班总结
```

### 手动整合
如果「下班」是手动流程，最后一步执行 `/diary endday`。

### 脚本整合
如果「下班」是自动化脚本，在脚本末尾调用 Reasonix 执行：
```
reasonix run "请执行 /diary endday"
```
```

- [ ] **Step 3: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: implement /diary endday and 下班 integration"
```

---

### Task 7: 实现与 domestic-reach 联动

**Files:**
- Modify: `.reasonix/skills/ai-diary/SKILL.md`

- [ ] **Step 1: 编写选题热度判断逻辑**

```markdown
## 与 domestic-reach 联动

### 触发场景
1. 用户执行 `/diary publish` 时，自动判断当前话题热度
2. 用户执行 `/diary today` 时，标记热门选题

### 联动方式
通过 subagent 调用 domestic-reach 技能：

```
调用 domestic-reach，参数：采集当前国内热点，聚焦与当前日记话题相关的领域
```

### 输出增强
在日记中增加热度标记：

```
🔥 热度判断
━━━━━━━━━━━━━━━━━━
相关热点：小米澎程系列发布（百度沸🔥）
话题热度：⭐⭐⭐⭐（高）
建议：趁热发布，搭配「AI如何帮你追热点」角度
```
```

- [ ] **Step 2: 提交**

```bash
git add .reasonix/skills/ai-diary/SKILL.md
git commit -m "feat: integrate domestic-reach for topic heat analysis"
```

---

## 验收标准

| 功能 | 验收条件 |
|------|---------|
| `/diary` | 显示最近 5 条日记摘要 |
| `/diary today` | 生成或更新当日日记文件 |
| `/diary list` | 分页显示历史日记列表 |
| `/diary weekly` | 生成周报并写入 weekly/ 目录 |
| `/diary publish` | 输出指定平台适配版本到 drafts/ |
| `/diary endday` | 生成下班总结，可整合进下班流程 |
| domestic-reach联动 | publish 和 today 时附加热度判断 |
