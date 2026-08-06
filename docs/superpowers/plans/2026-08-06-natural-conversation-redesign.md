# 自然对话重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 think/speak prompt 与记忆机制，让 NPC 输出符合自然对话规则（接话/长度波动/结构自由/反问低频），并新增意图判断器与三层记忆。

**Architecture:** 保留现有二重结构（think→speak），在 think 前插入规则粗判的意图判断器（双轴标签：情绪+需求），think 改为"基于意图选策略+产出心里话"；speak 改为"按自然规则表达"。记忆从单一摘要列表升级为三层（内容缓冲2轮原文 + 摘要5条含情绪 + 话题主线全程）。RAG 检索与思维框架注入位置不变。

**Tech Stack:** Python 3.11 · FastAPI · jinja2 · jieba（已有依赖）· unittest（项目现有测试框架，无 pytest）

## Global Constraints

- 所有新代码用 unittest 测试（项目无 pytest，`tests/test_kb_ops.py` 是既有模式）
- 中文注释；类/函数用英文命名
- 不推 GitHub；本地 commit 可选
- 不扫 `data/` `聊天记录/` `.env` `tools/` 目录
- think/speak 模板是 jinja2，保持 `{{ }}` 语法
- `web/app.py` 是主服务文件，改动集中在 chat 链路（约 920 行附近）与记忆维护（约 982 行附近）

---

### Task 1: 意图判断器模块 `pipeline/intent.py`

**Files:**
- Create: `pipeline/intent.py`
- Test: `tests/test_intent.py`

**Interfaces:**
- Consumes: 无（纯本地规则）
- Produces:
  - `class IntentAnalyzer` 或函数 `analyze_intent(text: str, prev_needs: list = None) -> dict`
  - 返回 `{"emotion": "negative|positive|neutral", "needs": {"info": 0.0-1.0, "affection": 0.0-1.0, "action": 0.0-1.0}}`
  - `EMOTION_WORDS_NEG` / `EMOTION_WORDS_POS` / `NEED_SIGNALS` 词库常量

- [ ] **Step 1: Write the failing test**

`tests/test_intent.py`:
```python
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from intent import analyze_intent

class TestIntent(unittest.TestCase):
    def test_negative_emotion(self):
        r = analyze_intent("我压力大，好累")
        self.assertEqual(r["emotion"], "negative")
    def test_positive_emotion(self):
        r = analyze_intent("太好了，我做到了")
        self.assertEqual(r["emotion"], "positive")
    def test_neutral_default(self):
        r = analyze_intent("今天天气不错")
        self.assertEqual(r["emotion"], "neutral")
    def test_info_need(self):
        r = analyze_intent("我该怎么办？")
        self.assertGreater(r["needs"]["info"], 0.5)
    def test_affection_need(self):
        r = analyze_intent("我压力大，你说我该怎么办")
        self.assertGreater(r["needs"]["affection"], 0.3)
        self.assertGreater(r["needs"]["info"], 0.3)
    def test_action_need(self):
        r = analyze_intent("帮我个忙")
        self.assertGreater(r["needs"]["action"], 0.3)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_intent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'intent'`

- [ ] **Step 3: Write minimal implementation**

`pipeline/intent.py`:
```python
# -*- coding: utf-8 -*-
"""意图判断器：规则粗判，输出双轴标签（情绪轴 + 需求轴，带隶属度）。
理论依据：Russell(1980) 情绪效价；Searle(1969) 言语行为；House(1981) 社会支持；Rosch(1975) 原型隶属度。
"""

EMOTION_WORDS_NEG = [
    "累", "压力", "焦虑", "难过", "烦", "失败", "不行", "没用", "差", "痛苦",
    "迷茫", "绝望", "难受", "委屈", "孤独", "害怕", "担心", "生气", "郁闷", "崩溃",
    "煎熬", "受挫", "失落", "糟糕", "吃力", "撑不住", "坚持不住", "好难", "太难",
]
EMOTION_WORDS_POS = [
    "开心", "高兴", "太好了", "棒", "成功", "厉害", "满意", "幸福", "激动",
    "感谢", "感谢你", "喜欢", "进步", "突破", "顺利", "好运", "欣慰",
]
NEED_SIGNALS = {
    "info": ["怎么办", "如何", "为什么", "该不该", "能不能", "怎么", "什么意思", "有什么办法"],
    "affection": ["好累", "压力大", "好难", "做不到", "是不是我不行", "没用", "撑不住", "安慰", "好烦"],
    "action": ["帮我", "帮我个忙", "请你", "拜托", "替我"],
}


def _count_hits(text: str, words: list) -> int:
    return sum(1 for w in words if w in text)


def analyze_intent(text: str, prev_emotion: str = "neutral") -> dict:
    """粗判一句话的情绪与需求。prev_emotion 供前文衰减融合（预留）。"""
    neg = _count_hits(text, EMOTION_WORDS_NEG)
    pos = _count_hits(text, EMOTION_WORDS_POS)
    if neg > pos:
        emotion = "negative"
    elif pos > neg:
        emotion = "positive"
    else:
        emotion = "neutral"

    needs = {"info": 0.0, "affection": 0.0, "action": 0.0}
    for key, signals in NEED_SIGNALS.items():
        hits = _count_hits(text, signals)
        if hits:
            needs[key] = min(0.4 + 0.2 * hits, 1.0)
    # 负面情绪天然提升"要情感"隶属度
    if emotion == "negative":
        needs["affection"] = max(needs["affection"], 0.4)
    # 无任何信号 → 视为闲聊（无需求）
    if all(v == 0.0 for v in needs.values()):
        needs["affection"] = 0.1
    return {"emotion": emotion, "needs": needs}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_intent.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/intent.py tests/test_intent.py
git commit -m "feat: add intent analyzer (emotion + needs dual-axis)"
```

---

### Task 2: 话题主线模块 `pipeline/topic_thread.py`

**Files:**
- Create: `pipeline/topic_thread.py`
- Test: `tests/test_topic_thread.py`

**Interfaces:**
- Consumes: 无（独立）
- Produces:
  - `class TopicThread`
    - `def update(self, question: str) -> None`（每轮调用：检测切换/更新节点）
    - `def summary(self) -> str`（返回一行话题线，如"从工作压力聊到管理方法，现在在用人上"）
    - `def nodes(self) -> list`（话题节点列表 [{topic, brief, round}]）

- [ ] **Step 1: Write the failing test**

`tests/test_topic_thread.py`:
```python
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from topic_thread import TopicThread

class TestTopicThread(unittest.TestCase):
    def test_same_topic_updates_not_appends(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("工作压力还是很大，怎么办")
        self.assertEqual(len(t.nodes()), 1)
    def test_new_topic_appends(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("咱们聊聊历史吧")
        self.assertGreaterEqual(len(t.nodes()), 2)
    def test_summary_nonempty(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("咱们聊聊历史吧")
        self.assertTrue(len(t.summary()) > 5)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_topic_thread.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'topic_thread'`

- [ ] **Step 3: Write minimal implementation**

`pipeline/topic_thread.py`:
```python
# -*- coding: utf-8 -*-
"""话题主线：检测话题切换，维护话题节点序列，提供整体话题线。
理论依据：Zacks & Tversky(2001) 事件分割——人按"事件边界"记忆连续经验。
"""

import jieba

SIM_THRESHOLD = 0.15  # Jaccard 相似度低于此值视为切换话题


def _keywords(text: str) -> set:
    words = jieba.lcut(text)
    # 去掉单字与停用词
    stops = {"我", "你", "他", "的", "了", "吗", "呢", "啊", "是", "在", "有", "也", "就", "都"}
    return {w for w in words if len(w) > 1 and w not in stops}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


class TopicThread:
    def __init__(self):
        self._nodes = []  # [{topic, brief, round}]
        self._round = 0

    def update(self, question: str) -> None:
        self._round += 1
        kws = _keywords(question)
        if not self._nodes:
            self._nodes.append({"topic": question[:20], "brief": question[:30], "round": self._round})
            return
        last = self._nodes[-1]
        last_kws = _keywords(last["topic"]) | _keywords(last["brief"])
        sim = _jaccard(kws, last_kws)
        if sim >= SIM_THRESHOLD:
            last["brief"] = question[:30]  # 同话题，更新简述
        else:
            self._nodes.append({"topic": question[:20], "brief": question[:30], "round": self._round})

    def nodes(self) -> list:
        return list(self._nodes)

    def summary(self) -> str:
        if not self._nodes:
            return ""
        if len(self._nodes) == 1:
            return f"你们在聊「{self._nodes[0]['topic']}」"
        topics = "、".join(n["topic"] for n in self._nodes)
        return f"从「{self._nodes[0]['topic']}」聊到「{self._nodes[-1]['topic']}」，中间还提到：{topics}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_topic_thread.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/topic_thread.py tests/test_topic_thread.py
git commit -m "feat: add topic thread tracker (Jaccard topic-switch detection)"
```

---

### Task 3: think 模板重写 `reasoning/prompts/think.jinja2`

**Files:**
- Modify: `reasoning/prompts/think.jinja2`（整文件重写）

**Interfaces:**
- Consumes:
  - `question`（用户输入）
  - `memories`（摘要列表，每项 `{question, summary, emotion}`）
  - `rag_results`（RAG 原文）
  - `knowledge_base`（思维框架）
  - `topic_line`（话题主线字符串，Task 2 产出）
  - `raw_recent`（最近2轮原文列表，每项 `{question, answer}`）
  - `intent`（意图标签 dict，Task 1 产出 `{emotion, needs}`）
- Produces: 无（模板文件；由 `build_think_prompt` 渲染）

- [ ] **Step 1: 先改 framework.py 的 build_think_prompt 签名**

`reasoning/framework.py` 当前 `build_think_prompt(question, rags, memories)` 只传三个变量。改为接受扩展参数：

```python
def build_think_prompt(self, question, rags, memories, **extra):
    """extra: topic_line, raw_recent, intent 等可选上下文。"""
    return self.env.get_template("think.jinja2").render(
        question=question, rag_results=rags, memories=memories, **extra
    )
```

- [ ] **Step 2: 重写 think.jinja2**

`reasoning/prompts/think.jinja2` 全文：
```jinja
你是毛泽东的"内心思考"，不对外说话。你的任务：判断对方此刻真正要什么，想好这一轮该怎么回应。

## 对方此刻的状态（规则粗判，基本可信）
- 情绪：{{ intent.emotion if intent else '中性' }}
- 需求倾向：{% if intent and intent.needs %}{% for k,v in intent.needs.items() if v > 0.3 %}{{ {'info':'想要方法/答案','affection':'想要被理解/安慰','action':'想要你帮忙'}[k] }}({{'%.0f' % (v*100) }}%) {% endfor %}{% else %}正常交流{% endif %}

## 你们的话题线
{{ topic_line or '刚开始聊' }}

## 你们最近聊过
{% for mem in memories %}
- 对方问过：{{ mem.question }}（情绪 {{ mem.get('emotion','中性') }}）
- 你当时说：{{ mem.summary }}
{% endfor %}

## 最近的原话（近2轮，供你回想细节）
{% for r in raw_recent %}
- 对方说：{{ r.question }}
- 你答：{{ r.answer }}
{% endfor %}

## 相关原文
{% for r in rag_results %}
（{{ r.title }}，{{ r.date }}）{{ r.text }}
{% endfor %}

## 知识框架
{{ knowledge_base }}

## 对方刚说
{{ question }}

## 你的思考任务（心里想，不写出来）
1. 他到底要什么？——结合上面"对方此刻的状态"，判断他是要方法、要安慰、要认可，还是随便聊聊。不要只看字面。
2. 这一轮怎么接最合适？——根据他的需求决定：给方法？先共情？直接点破？讲故事？还是就陪他聊两句。
3. 心里想说的话：一条或两条关键判断（可引用刚聊过的话题或他的话，但要自然）。
4. 如果有贴切的历史典故、原文可以用，想一个；没有就不硬凑。

注意：你不是在写分析报告，是在"心里琢磨"。想得可以深，但想完给"说话"留出自然的余地。
```

- [ ] **Step 3: 语法检查**

Run: `python -c "from jinja2 import Environment, FileSystemLoader; e=Environment(loader=FileSystemLoader('reasoning/prompts')); t=e.get_template('think.jinja2'); t.render(question='测试', memories=[{'question':'q','summary':'s','emotion':'负面'}], rag_results=[], knowledge_base='kb', topic_line='', raw_recent=[], intent={'emotion':'负面','needs':{'info':0.7,'affection':0.0,'action':0.0}}); print('think.jinja2 renders OK')"`
Expected: `think.jinja2 renders OK`

- [ ] **Step 4: Commit**

```bash
git add reasoning/prompts/think.jinja2 reasoning/framework.py
git commit -m "refactor: rewrite think prompt as intent-driven inner thought"
```

---

### Task 4: speak 模板重写 `reasoning/prompts/speak.jinja2`

**Files:**
- Modify: `reasoning/prompts/speak.jinja2`（整文件重写）

**Interfaces:**
- Consumes: `question`、`thinking_result`、`scene_context`（现有）
- Produces: 无（模板；由 `build_speak_prompt` 渲染）

- [ ] **Step 1: 重写 speak.jinja2**

`reasoning/prompts/speak.jinja2` 全文（保留场景/称呼/动作约束，重写表达规则）：
```jinja
你是毛泽东。现在你在和人聊天。对方用「您」称呼你。

## 当前场景
你正在：{{ scene.name or '菊香书屋' }}

{% if scene.atmosphere %}
{{ scene.atmosphere }}
{% endif %}

{% if scene.entities %}
你周围的事物：{{ scene.entities | join('、') }}
{% endif %}

## 动作与环境约束（必须遵守）
{% if scene.type == 'indoor_work' %}
- 你在书房兼办公室。动作只能写：批文件、翻书、看地图、喝茶、抽烟、打电话、踱步、坐在书桌前、看向窗外。
- 禁止一切室外动作：「抬头看天」「看树」「摘叶」「走路」「散步」「站在路边」「树下」。
- 禁止谈论或指认书房里不存在的东西（田野、池塘、菜地、小路一律不许出现）。
{% elif scene.type == 'indoor_home' %}
- 你在客厅。动作只能写：坐藤椅、喝茶、翻旧报纸、抽烟、摇蒲扇、剥橘子、看窗外。
- 可以隔着窗户看院子里的树影，但禁止「走出去」「到院子」「在树下」。
{% elif scene.type == 'outdoor_work' %}
- 你在室外小路上。动作只能写：背着手走、看冬青、看树、看鸟、坐下歇脚、捡落叶、望天空。
- 禁止一切办公桌动作：「批文件」「看地图」「翻书」「打电话」「写文章」。
{% elif scene.type == 'outdoor_home' %}
- 你在树下。动作只能写：靠树干、望田野、看池塘、听鸟叫蝉鸣、拔草、拍蚊子、看树冠光斑。
- 禁止办公桌动作；不写「进屋」「回书房」这类移动动作。
{% endif %}
- **硬约束**：你描述或互动的环境事物必须来自上面「你周围的事物」清单。
- 动作描写必须带「主席」或「老人家」做主语，用方括号包裹，如 [主席喝了口茶，看着你]。一轮最多 2 个动作。

## 称呼（必须遵守）
- 对方是年轻后辈，你称他为「你」或「小鬼」；绝不用「对方」「您」「先生」指代他。
- 动作里写到对方一律用「你」：如「看着你」「指指你」，禁止「看着对方」。
- 你自称「我」即可；不自称「润之」，不称呼对方「老弟」「兄弟」。

## 自然对话规则（必须遵守，这是你说话的方式）
- **接话**：先抓住对方话里的某个词或情绪接过去，不要从零开始讲道理。可以用他刚说的词。
- **长度**：多数时候两三句话，说透了就停；特别想讲、或对方问到根上，才说长。平均短，偶尔长。
- **结构自由**：禁止固定套路。有时先讲故事，有时先反问，有时只给一句判断，怎么自然怎么来。不列一二三四，不用「一方面…另一方面」。
- **口头禅**：点到位为止，整段最多一次，别句句带。
- **反问**：可以反问，也可以不反问就自然收尾。反问多了就假，不要每轮都以问题结尾。
- **情感**：先有态度（认同/心疼/调侃/惊讶），再说道理。对方低落时少说教、先接住情绪。

## 你心里想的是
{{ thinking_result }}

## 对方刚说
{{ question }}

## 现在你开口
说人话，像聊天，不像布道。把心里想的意思说出来，怎么自然怎么来。
```

- [ ] **Step 2: 语法检查**

Run: `python -c "from jinja2 import Environment, FileSystemLoader; e=Environment(loader=FileSystemLoader('reasoning/prompts')); t=e.get_template('speak.jinja2'); t.render(question='测试', thinking_result='想一下', scene_context={'name':'菊香书屋','atmosphere':'','type':'indoor_work','entities':[]}); print('speak.jinja2 renders OK')"`
Expected: `speak.jinja2 renders OK`

- [ ] **Step 3: Commit**

```bash
git add reasoning/prompts/speak.jinja2
git commit -m "refactor: rewrite speak prompt with natural conversation rules"
```

---

### Task 5: 主链路接入 `web/app.py`

**Files:**
- Modify: `web/app.py`（chat 链路：意图判断注入、记忆三层化、话题线）
- Test: 无单测（集成验证，见验证步骤）

**Interfaces:**
- Consumes: `analyze_intent`（Task 1）、`TopicThread`（Task 2）、新 `build_think_prompt` 签名（Task 3）
- Produces: 无

- [ ] **Step 1: 导入新模块 + 初始化**

`web/app.py` 顶部 import 区追加：
```python
from pipeline.intent import analyze_intent
from pipeline.topic_thread import TopicThread
```
全局变量区（`session_memories` 附近）追加：
```python
topic_thread = TopicThread()
raw_buffer = []  # 最近2轮完整 {question, answer}
```

- [ ] **Step 2: 记忆维护改为三层**

找到 `_generate_summary` 附近/chat 末尾的记忆追加段（约 982 行），改为：
```python
    # 意图判断 + 三层记忆维护
    intent = analyze_intent(req.message)
    summary = _generate_summary(req.message, answer)
    summary["emotion"] = intent["emotion"]
    session_memories.append(summary)
    if len(session_memories) > 10:
        session_memories = session_memories[-5:]
    # 内容缓冲：最近2轮原文
    raw_buffer.append({"question": req.message, "answer": answer})
    if len(raw_buffer) > 2:
        raw_buffer = raw_buffer[-2:]
    # 话题主线
    topic_thread.update(req.message)
```

- [ ] **Step 3: think 调用点注入扩展参数**

找到 `build_think_prompt` 调用（约 920 行）：
```python
    think_prompt = engine.build_think_prompt(
        req.message, rags, session_memories[-5:],
        topic_line=topic_thread.summary(),
        raw_recent=raw_buffer,
        intent=analyze_intent(req.message),
    )
```
注：`analyze_intent` 在 Step 2 已调用一次；此处为避免重复计算可改为把 Step 2 的 intent 存为模块级变量（实现时用 `current_intent` 全局缓存）。

- [ ] **Step 4: 语法检查 + 服务启动验证**

Run: `python -c "import ast; ast.parse(open('web/app.py',encoding='utf-8').read()); print('app.py syntax OK')"`
Expected: `app.py syntax OK`

Run: `python -c "import sys; sys.path.insert(0,'.'); from pipeline.intent import analyze_intent; from pipeline.topic_thread import TopicThread; print('imports OK')"`
Expected: `imports OK`

- [ ] **Step 5: 重启服务 + 冒烟**

Run: `python run_server.py`（后台）→ `curl http://localhost:8000/api/status`
Expected: `{"rag":true,"llm":true,...}`

Run: 发一条 `/api/chat` 消息验证不报错：
```bash
curl -s -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"我最近工作压力很大"}' | head -c 300
```
Expected: 返回 JSON 且 `answer` 非空

- [ ] **Step 6: Commit**

```bash
git add web/app.py
git commit -m "feat: wire intent analyzer + three-layer memory into chat pipeline"
```

---

### Task 6: 场景话题自然化 `web/app.py` scene/topic prompt

**Files:**
- Modify: `web/app.py`（`scene_topic` 函数的 prompt 字符串，约 344-353 行）

**Interfaces:**
- Consumes: 无
- Produces: 无

- [ ] **Step 1: 改 scene/topic prompt 去三段式**

当前 prompt 是"先结合场景说一句眼前的景象→再自然接一句和刚才话题相关的话→最后可以留一个钩子"。改为自然开场：

```python
    prompt = (
        f"你是毛泽东，刚刚和对方一起到了新地方——{scene['name']}（{scene['type']}）。\n"
        f"场景氛围：{scene['atmosphere']}\n"
        f"身边的事物：{entities}\n"
        + (f"最近聊过：{mem}\n" if mem else "")
        + "请以毛泽东的口吻，自然地开场说一两句话：可以提一句眼前的景象，也可以接着刚才的话头说。"
        "像真人到新地方随口说的话，别套结构、别强行留钩子。"
        "不要用「现在」「我们」等翻译腔。直接说话，不要带方括号动作。"
    )
```

- [ ] **Step 2: 语法检查**

Run: `python -c "import ast; ast.parse(open('web/app.py',encoding='utf-8').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add web/app.py
git commit -m "refactor: naturalize scene transition opener"
```

---

### Task 7: 验证与调参

**Files:**
- 无新文件（人工验证）

**Interfaces:**
- Consumes: 全部前序任务产物

- [ ] **Step 1: 意图判断器单测**

Run: `python tests/test_intent.py -v` → PASS；`python tests/test_topic_thread.py -v` → PASS
再跑 20 条真实风格输入（写临时脚本或手动 curl），检查双轴标签是否符合直觉，调词库。

- [ ] **Step 2: 对话自然度 10 轮连测**

在 `http://localhost:8000` 连续问 10 轮（含不同意图：求答案/求安慰/闲聊/试探），人工检查：
- 结尾反问频率（应明显下降）
- 句式重复率（不应出现"一方面…另一方面"连续两轮）
- 结构多样性（不是每轮都论点→论据→反问）
- 情绪连续性（上轮低落，这轮不突兀）

- [ ] **Step 3: 记忆有效性验证**

聊到第 6~8 轮后，问一句涉及第 1~2 轮话题的话，验证：
- 话题线注入让 speak 能说"咱们又绕回XX"
- 近 2 轮原话让 speak 能引用对方原词
- 情绪字段让后续轮次回应更贴

- [ ] **Step 4: 记录结果 + 收尾**

把实测结果写回 `docs/superpowers/specs/2026-08-06-natural-conversation-redesign.md` 的验证记录，或另存 `docs/handoffs/2026-08-06-natural-conversation-result.md`。

---

## 自我审查

**规格覆盖检查：**
- §2.3 意图判断（双轴标签）→ Task 1 ✅
- 三层记忆（内容缓冲/摘要+情绪/话题主线）→ Task 2 + Task 5 ✅
- think 重写（基于意图选策略+心里话）→ Task 3 ✅
- speak 重写（自然规则）→ Task 4 ✅
- 主链路接入 → Task 5 ✅
- 场景话题自然化 → Task 6 ✅
- 验证（10轮连测/前后对比/意图单测）→ Task 7 ✅

**占位符扫描：** 所有代码块完整；无 TBD/TODO；每个测试有具体断言。

**类型一致性：**
- `analyze_intent(text) -> {"emotion", "needs"}` 在 Task 1 定义，Task 5 一致使用 ✅
- `TopicThread.update()/.summary()/.nodes()` 在 Task 2 定义，Task 5 使用 `update`/`summary` ✅
- `build_think_prompt(question, rags, memories, **extra)` 在 Task 3 改签名，Task 5 传 `topic_line/raw_recent/intent` ✅
- `session_memories` 元素加 `emotion` 字段，think 模板用 `mem.get('emotion')` 兼容 ✅
