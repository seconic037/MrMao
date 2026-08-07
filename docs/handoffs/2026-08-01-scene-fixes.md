# Handoff: MrMao 场景系统 7 项改造
> 从 MrMao 项目分叉 | 2026-08-01

## 任务目标
按用户确认的方案改造场景系统 7 项问题（切换入口/背景/模式联动/事物互动/动画/NPC 话题/疲劳联动），完成后在新会话实测。

**用户已确认的决策**：
- ✅ 全部 7 项一起改，一次实测
- ✅ NPC 话题用 LLM 生成（结合历史摘要 + 新场景氛围，附带随机出题）
- ✅ 顶栏地点图标 → 底部弹层切换面板

## 项目环境
- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · ChromaDB · DeepSeek API (deepseek-v4-flash)
- 前端: 原生 HTML/CSS/JS，移动端响应式
- 启动: `python run_server.py` → `http://localhost:8000`
- 场景图: `web/static/img/scenes/`（4 主场景 + 5 过渡图 png/webp 双版本）
- 疲劳阈值: 黄 21 轮 / 红 35 轮（`web/app.py` 常量）
- 日志: `聊天记录/session_*.jsonl`；会话内存 + 磁盘恢复

## 涉及文件
| 文件 | 类型 | 说明 |
|------|------|------|
| `pipeline/scenes.py` | 修改 | 过渡映射补全、室内外切换文案、实体互动白名单、疲劳提示 |
| `pipeline/game_engine.py` | 修改(可选) | 已有 SCENE_BIAS 按场景出题，可能补场景事件题 |
| `reasoning/prompts/speak.jinja2` | 修改 | 强化"事物必须来自当前场景清单"约束 |
| `reasoning/prompts/think.jinja2` | 修改(可选) | 场景切换意图检测 |
| `web/app.py` | 修改 | scene/set 返回 topic+疲劳提示、scene/suggest 联动疲劳、新场景疲劳提示接口 |
| `web/static/app.js` | 修改 | 地点图标面板、applySceneBg 模式检查、enterChat 弹场景选择、切换后 NPC 话题、idle 疲劳联动、compact 按钮场景变体 |
| `web/static/index.html` | 修改 | scene-bar 加地点图标、切换面板结构 |
| `web/static/style.css` | 修改 | 普通模式纯色背景、面板/图标样式、compact 变体 |
| `docs/handoffs/2026-08-01-scene-fixes.md` | 新增 | 本文档 |

## 7 项问题根因与方案

### 1️⃣ 场景主动切换入口（顶栏地点图标 → 弹层面板）
**现状**：`scene-bar` 只有 `sceneLabel` + `sceneToggle`（⚙️ 调 `toggleSceneMode()`）。无地点图标、无主动切换入口。唯一切换：底部场景 TAB 开模式 → 首页"和老人家聊聊"→ sceneModal；或对话关键词（`detect_switch_intent`）。

**方案**：
- `index.html` scene-bar 加地点图标（如 📍/🏠，`id="sceneSwitchBtn"`）
- `app.js` 新增 `showSceneSwitchPanel()`：
  - `sceneMode===false` → toast "当前为普通模式，不可切换场景，请打开场景模式"（问题 1c）
  - 当前 indoor → 面板列 2 个 outdoor 目标，文案"主席，我们出去走走好吗？"
  - 当前 outdoor → 面板列 2 个 indoor 目标，文案"主席，外面风大，我们回屋吧？"（问题 1a）
  - 点击目标 → `pickScene(target, label)` → 走过渡动画（问题 1b）
- `scenes.py` 新增 `SCENE_SWITCH_TEMPLATES`（室内→室外 / 室外→室内 两种语言文案）
- 复用现有 `sceneModal` 结构或新建 `sceneSwitchModal`

### 2️⃣ 普通模式不应显示背景图 → 纯色
**根因**：`applySceneBg()`（app.js:71）无条件设置 inline `background-image`；`updateSceneUI` 只移除 `scene-bg` 类，**inline 背景仍在**，`#page-chat.active{background-size:cover}` 继续渲染。

**方案**：
- `applySceneBg(sceneId)` 开头检查 `if(!sceneMode){clearSceneBg();return}`；新增 `clearSceneBg()` 清 `page.style.backgroundImage=''`
- `enterChat` 178 行、`playTransition` 91 行、`setScene` 63 行调用统一走此检查
- `style.css`：`#page-chat.active` 加默认纯色 `background-color:var(--bg)` 或暖色；仅 `.scene-bg.*` 时显示图
- 注意：`page.style.backgroundImage` 清空后，切回场景模式需重新 `applySceneBg(currentScene)`

### 3️⃣ 普通模式进入聊天也应弹场景选择（4 场景+随机）
**现状**：`enterChat()` 不弹场景选择；场景选择只在首页"和老人家聊聊"且 `sceneMode=true` 时经 `showEntryPanel` 弹 sceneModal。

**方案**：
- `enterChat()` 开头：`if(!sceneMode)` 先弹 sceneModal（4 场景+随缘，现有 `pickScene`/`pickSceneRandom` 复用），选完再进聊天
- 注意协调调用链：`resumeFromLog`、`startNewSession`、`ask()`、热点"和主席聊聊"都会调 `enterChat`——需区分"首次进入需选场景"与"恢复会话不重选"，避免打断（建议：仅当 `chat.children.length===0` 且无活跃会话时弹）

### 4️⃣ 室内 2 场景不触发事物互动 + LLM 互动提示契合场合
**根因**：
- `SCENE_ENTITIES` 室内（shuwu/keting）只有 `objects` 类；室外才有 sky/ground/objects
- `speak.jinja2` 把全部实体注入为"允许列表"而非"约束"，LLM 室内回复可自由提到室外事物（实测"窗外那棵树的树冠"）
- 无互动触发校验层

**方案**：
- `scenes.py`：`SCENE_ENTITIES` 给每个实体标 `type`（indoor_work/indoor_home/outdoor_work/outdoor_home）；室内场景增加"窗外院子/树影"边界实体（可看不可去，标注 `reachable:false`）
- `speak.jinja2`：动作约束强化——
  - indoor_work（书房）：禁"看树/摘叶/走路/抬头望天"等室外动作，禁谈论非办公场所事物
  - indoor_home（客厅）：可看窗外院子树影，但禁"走出去/在树下"等室外行为
  - outdoor_*：禁"批文件/看地图/翻书"等办公动作
  - 增加硬约束："你描述或互动的环境事物必须来自当前场景清单，不得发明不在场的事物"
- `app.py`：`get_scene_entities_flat` 传实体时带上 `type` 过滤标记，或拆成 `allowed_entities` / `forbidden_actions`

### 5️⃣ 场景切换动画丢失
**根因（多层）**：
- **A**（已修复需回归验证）：上次 `setScene` 合并为 async 版，`pickScene` `await setScene(id)`，过渡只在 `d.transition.scene` 非空时播
- **B**：同类型切换 `get_transition` 返回 `"scene":""`（scenes.py:460）→ `TRANS_BG['']` undefined → 无图，仅文字（可接受但需确认不卡死）
- **C**：跨类型缺口——`shuwu↔shuxia`、`keting↔xiaolu`、`shuxia→shuwu` 等组合 `get_transition` 返回 `None` → `setScene` 走 `else applySceneBg()` **完全不播过渡**
- **D**：`(shuxia, keting)` 映射到 `丰泽园庭院入口`(trans-courtyard)，但设计文档 §3.5 规定应为 **`傍晚庭院入口`(trans-dusk) 专用**
- **E**：`send()` 218 行 `setTimeout(()=>setScene(...),1500)` 与 `typewrite` 并发，切换可能在打字动画中途触发

**方案**：
- `scenes.py` `TRANSITIONS` 补全：
  - `(shuxia, keting)` → 傍晚庭院入口 (trans-dusk)
  - 补 `(keting, xiaolu)`、`(xiaolu, keting)`、`(shuwu, shuxia)`、`(shuxia, shuwu)`（可复用门廊/小径/庭院入口，或归并到 `get_transition` 的兜底逻辑）
  - 兜底：任意未定义组合 → 返回通用过渡（有文字+可空图）
- `app.js` `playTransition`：处理 `transition.scene===''`（纯文字遮罩，无图不报错）；`transition` 为 null 时也应至少播文字
- `setScene`：`d.transition` 为 None → 播放通用过渡（调用 `/api/scene/transition?from=旧&to=新` 或前端兜底文字）
- `send()`：场景切换等 `typewrite` 完成后触发（在 `typewrite` 的 done 回调里检查 `d.scene_switch`）

### 6️⃣ 切换场景后 NPC 主动提话题（LLM 生成）
**现状**：`setScene` 切换后只 `resetIdleTimer()`，无主动发言。

**方案**：
- `app.py` `/api/scene/set` 响应增加 `topic` 字段（可选），或新增 `POST /api/scene/topic`：
  - 用 LLM 生成：输入 = `session_memories`（最近对话摘要）+ 新场景 `atmosphere` + 场景实体 + 随机事件
  - 输出 = 主席 2-3 句开场话题（联动之前对话），可附带一道题（复用 `_maybe_quiz`/`pick_question`）
- 前端 `setScene` 成功后：若切换成功（有 transition 或 scene 变化）→ 调 topic 接口 → `typewrite` 主席开场白
- 防重：`sceneTopicShown` 标志，每次切换仅一次；不打断用户刚发送的消息（切换由用户主动触发时，话题作为追加气泡）

### 7️⃣ NPC 切换建议与疲劳阈值一致 + 切换后疲劳提示
**现状**：
- 前端冷场建议 `idleCount>=10`（30s×10=5min）触发 `/api/scene/suggest`，注释写"2次"（错误）
- 疲劳阈值：后端 21 黄 / 35 红
- `TIMEOUT_WARN=8min` 常量定义了但未用
- 用户需求例子："22/35，8分钟触发" —— 即到黄疲劳(21)后，空闲 8 分钟（16 次 30s 冷场）触发切换建议

**方案**：
- 前端 `resetIdleTimer`/`showIdleAction`：
  - `idleCount>=10` 改为与疲劳联动：建议触发条件 = `idleCount >= 16`（8min）**或** 疲劳黄/红且 idleCount≥8（4min）
  - 修正 287 行注释
- 切换场景后**在新场景触发疲劳提示**（以切换后的场景为准）：
  - `scenes.py` 已有 `FATIGUE_ACTIONS`（indoor/outdoor 区分）——切换后前端调新接口 `POST /api/scene/fatigue-hint`（或复用 idle-actions）返回**新场景**的疲劳提示文字
  - 前端切换完成 → 若 `currentFatigue` 非 green → 显示新场景疲劳提示气泡
- compact 恢复按钮按场景变文字：室内"🍵 续茶 / 🚬 递烟"，室外"💧 喝口水 / 🪨 歇歇脚"（`doCompact` 根据 `currentScene` 换文案）
- 室内外疲劳提示文字不同（FATIGUE_ACTIONS 已按 indoor/outdoor 区分，确认切换后取新场景）

## 联动修改清单（跨文件依赖）
1. **scenes.py 是核心**：过渡映射 + 实体 type 标记 + 切换文案 + 疲劳提示 → 先改
2. **app.py 依赖 scenes.py**：scene/set 返回 topic、scene/suggest 疲劳联动、fatigue-hint 接口
3. **speak.jinja2**：实体约束强化（不依赖代码，但需与实体 type 标记呼应）
4. **app.js 依赖所有**：地点面板、模式检查、NPC 话题、疲劳联动、动画修复
5. **index.html/style.css**：面板结构 + 样式（最后）

## 已知遗留（勿动）
- `web/app.py` `LOG_DIR` 用中文目录"聊天记录"（旧 data/logs 数据不迁移，属既有状态）
- `web/static/app.js` `toggleAddForm/doAddEntry` 死代码（无调用者）
- `ask()` 已在上一轮去重（app.js:532 唯一）

## 约束
- 不推 GitHub
- 不改变 RAG/think 核心 / 日志系统 / 考考你题库
- 不扫 `data/` `聊天记录/` `tools/` `.env`
- 改动前先 `git status` 确认基线（当前有上轮测试修复未提交）

## 实测结果（2026-08-01 二测 ✅ 全部通过）

| # | 实测项 | 结果 |
|---|--------|------|
| 1 | 顶栏地点图标 + 切换面板 | ✅ 📍 图标渲染；普通模式点 📍 toast 提示"请打开场景模式"；场景模式弹面板（室内→"主席，我们出去走走好吗？"+室外目标；室外→"主席，外面风大，我们回屋吧？"+室内目标）；"先不换"取消 |
| 2 | 普通模式纯色背景 | ✅ applySceneBg 检查 sceneMode + updateSceneUI 清 inline + `#page-chat.active{background-color:var(--bg)}` 三层防护 |
| 3 | 普通模式进聊天弹场景选择 | ✅ "从头开始"→ 弹 4 场景+随缘；ask/热点入口挂起待发消息，选完场景再发（修复了同步检查 modal 的竞态） |
| 4 | 室内外事物约束 | ✅ 客厅回复动作全室内（烟灰缸/蒲扇/弹烟灰），无室外事物；speak.jinja2 四类约束 + 硬约束生效 |
| 5 | 过渡动画 | ✅ trans-doorway（书屋↔小路）/trans-courtyard（客厅↔树下/客厅↔小路）/trans-dusk（树下→客厅 5D）/trans-path（书屋↔树下）全部请求 200；对话关键词切换在 typewrite 完成后触发（5E） |
| 6 | 切换后 NPC 话题 | ✅ LLM 生成（"这院子里的草木生得精神…"、"这树荫底下凉快得很…读书如光斑"均联动前文+场景）；LLM 偶发空/单字时有本地兜底；气泡显示在历史之后（defer 修复） |
| 7 | 疲劳联动 | ✅ 灌 24 轮到黄疲劳：compact 按钮户外变体"喝口水/歇歇脚"；切换后新场景疲劳提示"[老人家把烟头掐灭，烟灰缸里已经四五个烟蒂了]"（室内黄）；fatigue-hint 接口按 indoor/outdoor 返回 |

### 二测新发现并修复的问题
1. **topic 接口 500**：`session_memories` 恢复/compact 后是字符串，`scene_topic` 里 `m.get()` 报 AttributeError → 兼容 dict/str 两种格式
2. **topic 偶发空/单字**：deepseek 偶发返回空或 1 字；加 `FALLBACK_TOPICS` 兜底 + `len(topic)<20` 判断；兜底曾用 `random.choice(字符串)` 返回单字，改为直接取文案
3. **topic 气泡被顶出视口**：pickScene 里 setScene 先触发 typewrite，随后 enterChat 加载历史（scrollIntoView 滚到底）把话题顶出 → `setScene(...,{defer:true})` 延后到 `await enterChat()` 后触发
4. **ask/热点场景选择竞态**：`ask()` 同步检查 modal 状态，但 enterChat 是异步（await 后才弹）→ 改为 `enterChat()` 返回"是否弹了场景选择"，`.then` 里再决定挂起/发送
5. **切换场景后 compact 按钮不变体**：setScene 更新 currentScene 后未刷新按钮文字 → 加 `updateCompactSceneBtns()` 调用

### 备注
- 灌水测试产生的会话已 `POST /api/session/discard` 清理
- 服务用 `python run_server.py`（无 --reload），改 app.py 需重启

## 建议加载的 Skill/文档
- `docs/scene-system-design.md`（v2.0 设计总纲，§3 切换机制 / §3.5 过渡图 / §7 场景互动）
- `docs/handoffs/2026-08-01-full-test.md`（上轮全测记录，含已修复 Bug 基线）
