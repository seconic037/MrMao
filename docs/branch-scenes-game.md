# 分支：场景系统 + 游戏化互动
>
> **分支目标：** 为主席模拟器增加四个互动场景 + 游戏化问答功能。
> **基准项目：** MrMao 主席模拟器（seat: `C:\Users\68090\Desktop\ChairManMao`）

---

## 一、项目环境（进入分支必读）

| 项 | 值 |
|----|-----|
| 项目路径 | `C:\Users\68090\Desktop\ChairManMao` |
| 后端 | Python 3.11 · FastAPI · Uvicorn |
| 前端 | 原生 HTML/CSS/JS，无框架 |
| 向量库 | ChromaDB (cosine) + BM25 (jieba) |
| LLM | DeepSeek API (deepseek-v4-flash, openai SDK) |
| 嵌入 | BAAI/bge-small-zh-v1.5 (sentence-transformers) |
| 启动 | `python run_server.py` → `http://localhost:8000` |
| 管道 | `python run_pipeline.py`（新增语料后重跑） |
| 日志 | `聊天记录/session_*.jsonl`（实时刷盘） |
| 知识库 | `data/txt/知识扩展/` 74 个 TXT，480 篇文章，5233 块 |

---

## 二、分支功能概述

### 2.1 场景系统

四个固定场景，每个带有独特氛围和专属动作库：

| ID | 场景 | 氛围描述 | 背景暗示 |
|----|------|---------|---------|
| `office` | 🏢 办公室 | 文件堆积、地图挂墙、红机电话 | 中南海办公室 |
| `living` | 🛋️ 客厅 | 藤椅、搪瓷杯、旧报纸、烟灰缸 | 丰泽园菊香书屋 |
| `garden` | 🌳 办公地外 | 庭院小径、林荫、鸟鸣 | 中南海散步道 |
| `home_out` | 🏡 家周围 | 菜地、田野、池塘、乡邻 | 韶山老家 / 北戴河 |

**每个场景有专属动作（5 个），替换通用的 IDLE_ACTIONS。** 主席说的动作描写和场景要一致，比如在"客厅"里不能说"站起来看地图"。

### 2.2 游戏化：考考你

主席出题考用户，题型：历史 / 哲学 / 诗词 / 党史。

- 题库 ~20 题，每题 3 个选项
- 答对：主席夸两句（7 种赞美随机）
- 答错：主席纠正，顺便带一句背景知识
- 连对 3 题：主席满意点头 + 特殊表扬

### 2.3 交互入口

- 场景选择：聊天页 `stats-bar` 下方增加场景标签行，点一下切换
- 游戏启动：聊天页底部操作栏增加 `🔔` 按钮（现有 💾保存 / 🔥找话题 / 🚪退出 四个按钮）

---

## 三、涉及文件

### 3.1 新增文件

| 文件 | 职责 |
|------|------|
| `pipeline/scenes.py` | 场景定义、氛围文本、专属动作映射 |
| `pipeline/game_engine.py` | 题库、评分、赞美/纠错语库 |

### 3.2 修改文件

| 文件 | 改动点 |
|------|--------|
| `web/app.py` | `+ /api/scene/set` `+ /api/scene/get` `+ /api/game/question` `+ /api/game/answer`；speak 接口传入当前场景 |
| `web/static/index.html` | 聊天页 + 场景标签行；+ 游戏问答面板 HTML |
| `web/static/app.js` | 场景切换函数；游戏交互（出题/选答案/得分）；底部栏 + 🔔 按钮 |
| `web/static/style.css` | 场景标签样式；游戏面板样式 |
| `reasoning/prompts/speak.jinja2` | 场景感知提示（注入氛围描述 + 动作约束） |

---

## 四、文件详细规格

### 4.1 `pipeline/scenes.py`

```python
SCENES = {
    "office": {
        "name": "办公室",
        "atmosphere": "你在中南海的办公室里。桌上堆着文件和《人民日报》，墙上挂着大地图，红机电话偶尔响起。",
        "actions": ["批了两份文件","拿起红铅笔在报告上画了个圈","抬头看了一眼墙上的大地图","把文件推到一边，腾出桌面","摘下眼镜放桌上，揉了揉鼻梁"],
    },
    "living": { ... },
    "garden": { ... },
    "home_out": { ... },
}
```

### 4.2 `pipeline/game_engine.py`

```python
QUESTIONS = [
    {"q":"《矛盾论》写于哪一年？","opts":["1936","1937","1938"],"a":1,"hint":"1937年8月，和《实践论》同年"},
    ...共20题
]
PRAISE = ["对头！","没错，就是这个理。","看来你下了点功夫。","孺子可教。"]
CORRECT_MSG = ["不对。","没说到点子上。","再想想看。"]
```

### 4.3 `web/app.py` 新增接口

| 接口 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/scene/set` | POST | `scene: str` | `{scene, atmosphere}` |
| `/api/scene/get` | GET | — | `{scene, atmosphere}` |
| `/api/game/question` | POST | — | `{q, opts[]}` |
| `/api/game/answer` | POST | `idx: int, answer: int` | `{correct, msg, streak}` |

场景状态存内存（`session_scene = "office"`），重启后恢复默认。

### 4.4 speak 流程改动

```
think 阶段（不变）
    ↓
speak 阶段：注入 SCENES[scene].atmosphere + actions
    → 动作描写必须符合当前场景
    ↓
输出
```

### 4.5 前端改动

```
聊天页新增：
  <div class="scene-bar" id="sceneBar">    ← 场景标签行
    <span onclick="setScene('office')">🏢 办公室</span>
    <span onclick="setScene('living')">🛋️ 客厅</span>
    ...
  </div>

聊天操作栏新增：
  <button onclick="startGame()">🔔 考考你</button>   ← 新增第 4 个按钮

游戏面板（弹出浮层）：
  ┌──────────────────┐
  │ 🔔 主席考考你     │
  │ 什么是...？       │
  │ ○ 选项A          │
  │ ○ 选项B          │
  │ ○ 选项C          │
  │ [提交答案]        │
  │ ✅ 答对了！...    │
  │ 连对: 2          │
  └──────────────────┘
```

---

## 五、数据流

```
[前端] 选场景 → POST /api/scene/set → 存内存
[前端] 发消息 → POST /api/chat → think(不变)
                                  → speak(注入场景氛围+动作)
[前端] 点🔔 → POST /api/game/question → 返回题目
[前端] 选答案 → POST /api/game/answer → 判断 + 点评
```

---

## 六、与主项目的正交性

- 场景系统不改变 RAG 检索、think 逻辑、日志系统
- 游戏化完全独立，不干扰正常对话
- 所有新增代码在独立文件中，修改文件仅增加接口
- 分支可随时合并，不会引入 breaking change

---

*分支规划文档，新对话引用此文件即可接续讨论。*
