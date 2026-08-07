# 从首页进入聊天：完整分支逻辑梳理（v2，含用户筛查修正）

> 依据 `web/static/app.js`（803 行）与 `web/static/index.html` 逐行核对 | 2026-08-01
> 目的：供检查"首页 → 点聊天框"之间所有可能的分支与系统反馈。
> v2 变更：按用户筛查结果修正——**默认普通模式不弹场景选择；仅主动打开场景模式才弹**。
> 图例：✅ 已确认 · ⚠️ 与当前代码不一致（期望行为，代码待改）· ❓ 待验证/待确认

---

## 0. 关键状态变量（决定分支走向）

| 变量 | 初值 | 含义 |
|------|------|------|
| `sceneMode` | `applySceneMode()` 从 `localStorage.mrmao_scene` 恢复 | 场景模式开关（**默认 off**；on=背景+过渡动画+可切场景+进入需选场景） |
| `scenePickDone` | `false` | 本次会话是否已选过场景（`startNewSession` 会重置为 false） |
| `scenePickPending` | `false` | 场景选择弹窗是否已挂起 |
| `_pendingSend` | `null` | 被挂起的待发消息（等场景选完再发） |
| `sceneTopicShown` | `false` | NPC 主动话题是否已展示（防重） |
| `hasNewMessages` | `false` | 是否有未保存的新消息（决定离开时是否弹退出确认） |
| `currentPage` | `'home'` | 当前页面（home/chat/read） |

---

## 1. 首页的 4 个"进入聊天"入口

### 入口 1：大按钮「和老人家聊聊」→ `showEntryPanel()`（app.js:146）

```
点击「和老人家聊聊」
│
├─ 【分支 1a】sceneMode = 开（用户主动打开的场景模式）
│   └─ 系统反馈：直接弹「📖 选择场景」弹窗（sceneModal）
│      → 弹窗内容 = 4 个场景（📚/🛋️/🌳/🌿）+ 随机 + 「普通模式」（单独一行）
│      → 点 4 场景 / 随机 → 走 [§3 场景选择流程]
│      → 点「普通模式」→ 自动关闭场景模式（sceneMode=false，写回 localStorage）
│        → 转入 [分支 1b]（普通模式流程）
│        ⚠️ 当前代码：sceneModal 无「普通模式」选项 → 需在 index.html + app.js 增加
│
└─ 【分支 1b】sceneMode = 关（普通模式 = 系统默认）✅
    ├─ 并行查 /api/session/status + /api/logs
    │
    ├─ 查询成功 → 弹「入口面板」entryModal，按会话状态给选项：
    │   ├─ 有活跃会话（s.active=true）
    │   │   └─ 显示「💬 继续上次聊天」（N 轮对话，X K tokens）
    │   │      → 点击 → 回填最近 20 条 → 弹两个后续选项（见下）⚠️ 选项为新增
    │   │        ├─ 【💡 总结并发起话题】→ NPC 总结之前话题内容，发起新话题
    │   │        └─ 【💬 直接开始对话】→ 等待聊天页输入，NPC 才会有反应
    │   │        ⚠️ 实测问题：回填后 NPC 并无之前对话记忆，而是从头讲起 → 待修复/确认
    │   ├─ 无活跃会话 + 有历史日志
    │   │   └─ 显示下拉（标题/文件名 · 条数）+「📜 继续这个话题」→ [§4.2 resumeFromLog]
    │   ├─ 无论上述哪种，都显示「🆕 从头开始」→ [§4.1 startNewSession]
    │   └─ 完全无记录 → 「暂无聊天记录。开始全新对话吧。」+「🆕 开始全新对话」
    │
    └─ 查询失败（catch）→ 系统反馈：无弹窗，静默直接 [§2 enterChat]
```

### 入口 2：首页「💬 试试这些」话题词条 → `ask(t)`（app.js:586）

```
点击话题词条
├─ 先把话题文本填入输入框（document.getElementById('msg').value = t）
├─ enterChat().then(popped => {
│   ├─ popped === true  → 已弹场景选择（仅场景模式可能）→ _pendingSend = t（挂起，选完才发）
│   └─ popped === false → setTimeout(200ms) 后自动 send()  ← 此时才真正发出
│   })
└─ 用户在这 200ms 内可自由改输入框内容（不覆盖，只发送当前值）
```

### 入口 3：热搜条目 → `showHotModal(title)` → `chatAboutHot()`（app.js:775, 783）

```
点击热搜条目
├─ 弹「热点详情弹窗」（hotModal）：标题 + 简述（fetch /api/hotspot/preview）
│   ├─ 简述加载中 →「加载中...」→ 成功后显示 200-300 字概述
│   └─ 失败 → 兜底显示标题本身
├─ 三个按钮：
│   ├─ 「💬 和主席聊聊这个」→ chatAboutHot()
│   ├─ 「👀 看看别的」→ 只关弹窗
│   └─ 「🏠 回到首页」→ 只关弹窗
└─ chatAboutHot():
    ├─ 关热点弹窗
    ├─ 输入框预填「<标题>，您怎么看？」
    ├─ 注入 window._hotContext = 热点简述
    │   └─ 发送时拼进 API 消息作为【背景信息】，但界面不显示
    ├─ enterChat().then(popped => {
    │   ├─ popped === true  → _pendingSend = 「<标题>，您怎么看？」（挂起）
    │   └─ popped === false → setTimeout(200ms) 后 send()
    │   })
```

### 入口 4：底部 Tab（不进入聊天，但影响状态）

| Tab | 处理函数 | 行为 |
|-----|---------|------|
| 🏠 首页 | `switchTab('home')` | 从聊天页离开时若 `hasNewMessages` 先弹退出确认（[§4.4]） |
| 📋 日志 | `toggleLogSheet()` | 半屏日志面板，不进聊天 |
| 🎭 场景 | `toggleSceneMode()` | 只翻转场景模式开关 + 更新 UI，不进聊天（**用户主动打开场景模式的唯一途径**） |
| 📖 阅读 | `switchTab('read')` | 进阅读页；从聊天离开同样先弹退出确认 |

---

## 2. 汇聚点：`enterChat()`（app.js:196）

所有"进入聊天"的路径最终都汇聚到这里。返回值语义：
- **返回 `true`** = 弹了场景选择，调用方必须挂起消息
- **返回 `false`** = 正常进入，可以发送

```
enterChat()
├─ ① switchTab('chat') → 聊天页激活
├─ ② resetIdleTimer() → 重置并启动后台定时器：
│     ├─ 30s 冷场 → showIdleAction（随机 NPC 小动作）
│     ├─ 8min 预警 → showExitWarning（退出预警条）
│     └─ 10min 离开 → 倒计时
│
├─ ③【分支 A：场景模式才弹场景选择】条件 = sceneMode && !scenePickDone
│   │  ⚠️ 当前代码：条件是 !sceneMode（普通模式才弹）→ 与期望相反，需反转
│   ├─ fetch /api/session/status
│   ├─ 返回无活跃会话（!sd.active）→ 弹「📖 选择场景」+ scenePickPending=true
│   │   └─ **return true**（挂起调用方）
│   └─ 有活跃会话 / 查询失败 → 不弹，继续
│   ❓ 待验证：场景模式 + 有活跃会话时是否仍弹场景选择（期望"总是先弹"，见 §5 链路5）
│
├─ ④ scenePickDone = true
├─ ⑤ fetch /api/scene/get → currentScene → updateSceneTags() + applySceneBg()
│   └─ applySceneBg 仅在 sceneMode=on 时设背景图，否则清空
│
└─ ⑥【分支 B：会话恢复 vs 开场白】fetch /api/session/status
    ├─ d.active === true（有活跃会话）
    │   └─ 聊天区为空 → fetch /api/logs → 回填最近 20 条（role 映射 chairman→assistant）
    │      → 普通模式：回填后弹两选项【总结并发起话题 / 直接开始对话】⚠️ 新增
    │      → 场景模式：先走完场景选择再恢复 ⚠️ 待验证
    └─ d.active === false → fetch /api/greeting → addMsg 开场白
    └─ return false
```

---

## 3. 场景选择流程（场景模式触发后）

用户从 sceneModal 选场景：`pickScene(id, label)`（app.js:665）或 `pickSceneRandom()`（app.js:681），或点「普通模式」返回普通模式流程

```
选择场景（4 固定场景 + 随机 + 普通模式）
├─ 点 4 场景 / 随机：
│   ├─ 关弹窗，sceneBar 场景名更新为 📚/🛋️/🌳/🌿 对应名
│   ├─ scenePickDone = true；scenePickPending = false
│   ├─ setScene(id, {defer:true})
│   │   └─ 系统反馈：过渡动画 playTransition（app.js:96）
│   │       ├─ 全屏遮罩 + 过场背景图（TRANS_BG：走廊/门廊/庭院等）
│   │       ├─ 过场文字逐字打出（60ms/字）
│   │       └─ 播完 → 应用目标场景背景图
│   │   └─ 切换成功（scene 确实变化）→ sceneTopicShown 重置为 false
│   ├─ 再次 enterChat()（回填历史或开场白）
│   ├─ showSceneTopic()（app.js:713）→ NPC 主动话题，只触发一次
│   │   └─ 返回 d.topic → typewrite 显示；返回 d.quiz → 弹「主席考考你」
│   ├─ showFatigueHint()（app.js:725）→ 疲劳非绿时追加提示条
│   └─ 若 _pendingSend 有值：
│       ├─ 输入框填入该值
│       └─ send()  ← 挂起的消息在此发出
│
└─ 点「普通模式」：
    ├─ sceneMode = false，写回 localStorage（mrmao_scene=off）⚠️ 新增
    ├─ 关弹窗
    └─ 转入 [§1 分支 1b]（普通模式入口面板流程）
```

场景模式关闭（sceneMode=off）时点聊天页 📍（showSceneSwitchPanel, app.js:695）：
- 系统反馈：toast「当前为普通模式，不可切换场景，请先打开场景模式」，不弹面板 ✅
- 场景模式开启时 → 查 /api/scene/switch-options → 弹「主动切换面板」→ 同样走 pickScene

---

## 4. 其余分支

### 4.1 从头开始 `startNewSession()`（app.js:168）
```
关入口弹窗 → fetch /api/session/discard（丢弃当前会话）
→ scenePickDone = false  ← 场景模式下：强制下次进聊天重新选场景 ✅
→ enterChat()
```

### 4.2 继续历史 `resumeFromLog(fname)`（app.js:530）
```
→ switchTab('chat') → 立即 addMsg「[老人家正在翻之前的聊天记录...]」（loading 气泡）
→ 关闭日志底部弹层（logSheet）
→ fetch /api/logs/entries?filename=... → 回填最后 5 条
→ 移除 loading 气泡 → 可直接继续对话
```

### 4.3 页面启动时（app.js:799-800）
```
fetch /api/status → RAG 未就绪 → stats 栏「⚠ RAG未就绪」；LLM 未配置 →「⚠ LLM未配置」
loadTopics() / loadHotspots() / loadKbStats() / applySceneMode() / initIcons()
```

### 4.4 从聊天页离开（切首页/阅读/点退出）→ `askSaveLog()`（app.js:175）
```
hasNewMessages === false → 直接走，不打扰
hasNewMessages === true  → 弹「退出确认浮层」：当前对话有 N 轮，是否保存？
    ├─ 保存并退出 → /api/session/save → hasNewMessages=false → switchTab('home')
    ├─ 丢弃退出   → /api/session/discard → hasNewMessages=false → switchTab('home')
    └─ 取消       → 留在聊天页
```

### 4.5 进入后的后台自动反馈（无需操作）
| 触发 | 反馈 |
|------|------|
| 30s 冷场 | NPC 随机小动作气泡（"指了指窗外院子里的树"等，来自 /api/idle-actions） |
| 空闲 ≥8min（或疲劳黄/红 + 4min）且未建议过 | 弹换场景建议（/api/scene/suggest，只问一次） |
| 8min 无操作 | 退出预警条（showExitWarning） |
| 10min 无操作 | 退出倒计时 |

---

## 5. 一句话总结关键链路（用户筛查后）

```
首页点击
 ├─ 普通模式（系统默认）+ 首进 + 无活跃会话 → 直接进聊天 → 开场白 → [可发消息]（不弹场景选择）✅
 ├─ 普通模式 + 有活跃会话 → 入口面板「继续上次聊天」→ 回填最近20条 → 弹选项：
 │     【💡 总结并发起话题】（NPC 总结之前话题，发起新话题）
 │     【💬 直接开始对话】（等待聊天页输入，NPC 才会有反应）
 │     ⚠️ 两选项为新增；且实测回填后 NPC 无记忆（从头讲起）→ 待修复
 ├─ 场景模式（用户主动打开）+ 首进 → 弹场景选择 → 选完(过渡动画) → 开场白 → [可发消息] ✅
 ├─ 话题/热点入口 → 若弹场景选择则挂起，选完自动补发；否则 200ms 后自动发 ✅
 └─ 场景模式 + 聊天区已非空 → 弹场景选择 → 选完恢复当前聊天 ⚠️ 与代码现状相反
```

**要点**：
- 整个系统**默认是普通模式**，只有用户主动打开场景模式后才会有「场景模式选择」；
- 普通模式从不弹场景选择，直接进入聊天；
- 场景模式进入时总是先弹场景选择（无论首进还是恢复），选完恢复/开始对话；
- 选完场景后挂起的消息（话题/热点）会自动补发；从头开始会强制重新选场景。

> ⚠ 实测问题（链路2）：普通模式「继续上次聊天」回填最近 20 条后，**NPC 并没有之前对话的记忆，而是从头讲起**——待修复/确认。

---

## 6. 差异清单执行状态（2026-08-01 已实施）

| # | 期望行为（用户确认） | 状态 | 说明 |
|---|---------------------|------|------|
| 1 | 场景选择只在场景模式（sceneMode=on）弹出 | ✅ 已改 | `enterChat()` 分支 A 条件反转为 `sceneMode&&!scenePickDone` |
| 2 | 场景模式 + 聊天区非空再进入 → 仍弹场景选择再恢复 | ✅ 已改 | 去掉"聊天区空"限制，场景模式总是先弹 |
| 3 | 场景选择弹窗增加「普通模式」选项（单独一行），点击自动关场景模式进普通流程 | ✅ 已改 | `pickPlainMode()` + index.html 新增选项 + 样式 `scene-pick-plain` |
| 4 | 恢复对话后弹三选项【总结由NPC发起 / 总结由我发起 / 直接聊】 | ✅ 已改 | `resumeModal` 弹窗 + `resumeSummarizeNpc/Me` + `resumeDirectChat`；两个恢复入口（继续上次聊天 `resumeActiveChat` + 日志恢复 `resumeFromLog`）都弹 |
| 5 | 恢复后 NPC 有前5条对话记忆 | ✅ 已改 | 新增 `POST /api/session/restore`，恢复入口调用后 `session_memories` 加载最近5条主席消息 |
| 6 | 普通模式 + 首进 + 无活跃会话 → 直接进聊天（开场白），不弹场景选择 | ✅ 已改 | 分支 A 反转后普通模式不弹场景 |
| 7 | 恢复会话回填后 NPC 应总结之前内容（三选项中的总结基于回填/恢复内容） | ✅ 已改 | `_summarizeResumed()` 用 `/api/session/summarize?filename=` 总结当前恢复内容 |
