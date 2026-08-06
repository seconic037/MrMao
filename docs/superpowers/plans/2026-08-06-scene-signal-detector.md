# 场景信号检测器 + 性格层实现计划（S3+S4+S6）

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 executing-plans 按任务逐步实现。步骤用 checkbox（`- [ ]`）跟踪。

**Goal:** 在 `pipeline/intent.py` 中实现场景信号检测器（scenes 5 标签 + situations 9 情境 + arousal 唤醒度），接入 think/speak prompt，并改造前端冷场挂起。

**Architecture:** 检测器扩充 `analyze_intent()` 返回 dict（新增 `scenes`/`situations`/`arousal` 键），词库信号词 + 规则粗判（复用 `_count_hits`/`_has_neg_prefix`）；think 注入场景与情境并选择 ≤2 个特质，speak 按场景/特质约束表达；前端 idle 改"首动→挂起→纯计时"。

**Tech Stack:** Python 3.11 · unittest · Jinja2 · 原生 JS

## Global Constraints

- 所有文件 UTF-8；中文注释；类/函数用英文
- 测试用 unittest（项目无 pytest）
- 不 push GitHub；本地 commit 可选
- 复用现有 `_count_hits`/`_has_neg_prefix`，不引入新依赖
- 场景/情境只改表达、不改 kind→策略选择（C4）；情绪轴门控特质激活（C1）；特质限频 ≤2、无例句库（C6）
- 不动 speak 禁术语（S1 暂缓）

---

### Task 1: intent.py 新增场景/情境/唤醒度判定

**Files:**
- Modify: `pipeline/intent.py`
- Test: `tests/test_intent.py`

**Interfaces:**
- Consumes: `_count_hits(text, words)`、`_has_neg_prefix(text, idx)`（已有）
- Produces: `analyze_intent(text)` 返回 dict 新增键：
  - `"arousal": "high"|"low"|"neutral"`（情绪强度）
  - `"scenes": {conflict, humor_offer, refuse_request, silence, outburst: 0~1}`
  - `"situations": {空谈, 纠结细节, 迷茫求方向, 闲聊, 越线, 传道授业, 轻松, 悲观, 深夜: 0~1}`

- [ ] **Step 1: 写失败测试**（tests/test_intent.py 追加）

```python
    # ── S3+S4 检测器新增 ──
    def test_scene_conflict(self):
        r = analyze_intent("你说得不对，我不同意你的看法")
        self.assertGreater(r["scenes"]["conflict"], 0)
    def test_scene_refuse_request(self):
        r = analyze_intent("帮我骂个人，替我出气")
        self.assertGreater(r["scenes"]["refuse_request"], 0)
    def test_scene_outburst_high_arousal(self):
        r = analyze_intent("我崩溃了！！！凭什么这么对我！！")
        self.assertGreater(r["scenes"]["outburst"], 0)
        self.assertEqual(r["arousal"], "high")
    def test_situation_teach(self):
        r = analyze_intent("您讲讲这个道理，怎么理解")
        self.assertGreater(r["situations"]["传道授业"], 0)
    def test_situation_pessimistic(self):
        r = analyze_intent("没希望了，白干了，算了吧")
        self.assertGreater(r["situations"]["悲观"], 0)
    def test_scenes_always_present(self):
        r = analyze_intent("今天天气不错")
        for k in ("conflict","humor_offer","refuse_request","silence","outburst"):
            self.assertIn(k, r["scenes"])
        self.assertIn("轻松", r["situations"])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_intent -v`
Expected: FAIL（KeyError: 'scenes'）

- [ ] **Step 3: 实现词库 + 判定逻辑**（pipeline/intent.py 追加）

```python
# ── 场景标签信号（服务 7~11 层，手册 v4 典型信号铺开版）──
SCENE_SIGNALS = {
    "conflict": ["我不同意", "你说得不对", "你错了", "但是", "可是", "恰恰相反", "不见得",
                 "未必", "不敢苟同", "你这么说不对", "道理不是这样", "我看未必", "这不对吧",
                 "你太绝对了", "不能这么说", "你说的不对"],
    "humor_offer": ["逗您玩", "开玩笑", "调侃", "您老", "老顽固", "哈哈", "嘻嘻", "您也会错",
                    "逮着您了", "您也有不会的"],
    "refuse_request": ["帮我骂", "替我出气", "帮我教训", "帮我整", "帮我写", "替我编", "帮我查",
                       "帮我删", "帮我转账", "帮我撒谎", "帮我瞒", "帮我骗", "帮我打"],
    "silence": ["嗯嗯", "哦哦", "是哦", "好的", "知道了", "嗯", "哦", "行", "。。", "…", "哈"],
    "outburst": ["崩溃", "气死了", "大哭", "受不了", "凭什么", "太欺负人", "我不行了", "绝望了",
                 "杀了我吧", "呜呜呜", "啊啊啊", "活不下去", "想死"],
}

# ── 激活情境信号（服务性格层 10 特质）──
SITUATION_SIGNALS = {
    "空谈": ["道理我都懂", "理论上", "原则上", "说白了", "本质", "宏观", "战略上", "说起来",
            "空谈", "纸上谈兵", "大道理"],
    "纠结细节": ["但是细节", "具体到", "然而", "可问题是", "这个细节", "那一步", "那个环节",
                "具体怎么", "细节上"],
    "迷茫求方向": ["我该往哪走", "选哪个", "不知道怎么办", "方向", "出路", "接下来", "以后怎么办",
                  "怎么选择", "何去何从"],
    "越线": ["你不对", "你的路线错了", "你那套过时了", "你当年", "批评你", "你错了", "你这是",
             "你怎么能", "你太过分了"],
    "传道授业": ["您讲讲", "这道理", "怎么理解", "解释一下", "为什么这么说", "说给我听", "教教我",
                 "您给讲讲", "请教"],
    "悲观": ["没希望", "完了", "白干了", "到头来", "有什么用", "没意思", "算了吧", "认命了",
             "就这样吧", "放弃吧"],
}

# 负面高唤醒词（强度档）：outburst 用
HIGH_AROUSAL_NEG = ["崩溃", "气死了", "大哭", "受不了", "绝望", "活不下去", "想死", "凭什么",
                    "太欺负人", "杀了我吧"]
# 负面低唤醒词（消沉/疲惫）
LOW_AROUSAL_NEG = ["累了", "疲惫", "无奈", "没劲", "算了", "就这样", "没意思", "躺平", "好累",
                   "撑不住"]

HIGH_AROUSAL_POS = ["太棒了", "太好了", "激动", "兴奋", "厉害", "绝了", "爽", "成功啦"]
```

```python
def _scene_membership(text: str, scene_signals: dict) -> dict:
    """计算各场景标签隶属度：命中数 → min(0.5 + 0.3*hits, 1.0)。"""
    out = {}
    for tag, words in scene_signals.items():
        hits = _count_hits(text, words)
        out[tag] = min(0.5 + 0.3 * hits, 1.0) if hits else 0.0
    return out


def _situation_membership(text: str, situation_signals: dict) -> dict:
    """计算各激活情境隶属度。闲聊=兜底：无任何情境命中且情绪中性时给 0.6。"""
    out = {}
    for tag, words in situation_signals.items():
        hits = _count_hits(text, words)
        out[tag] = min(0.5 + 0.3 * hits, 1.0) if hits else 0.0
    return out


def _detect_arousal(text: str, emotion: str) -> str:
    """唤醒度判定（S6 四象限）：感叹号/强度词/语气词/重复字。"""
    exclaims = text.count("！") + text.count("!")
    repeat = any(c * 3 in text for c in "啊啊呜呜哈哈嘿嘿")
    if emotion == "negative":
        if _count_hits(text, HIGH_AROUSAL_NEG) or exclaims >= 2 or repeat:
            return "high"
        if _count_hits(text, LOW_AROUSAL_NEG):
            return "low"
    elif emotion == "positive":
        if _count_hits(text, HIGH_AROUSAL_POS) or exclaims >= 1:
            return "high"
        return "low"
    return "neutral"
```

- [ ] **Step 4: 改造 analyze_intent 返回**（追加 scenes/situations/arousal + 轻松情境兜底）

```python
    kind = _classify_kind(text, emotion, needs, test_hits, approval_hits)
    scenes = _scene_membership(text, SCENE_SIGNALS)
    situations = _situation_membership(text, SITUATION_SIGNALS)
    # 轻松情境：情绪非负面且无其他情境命中时兜底 0.6
    if emotion != "negative" and not any(v > 0 for v in situations.values()):
        situations["轻松"] = 0.6
    # 唤醒度（S6）
    arousal = _detect_arousal(text, emotion)
    # C1 情绪门控：情绪负面时幽默情境归零（手册 8.4）
    if emotion == "negative":
        scenes["humor_offer"] = 0.0
        situations["轻松"] = 0.0
    return {"emotion": emotion, "needs": needs, "kind": kind,
            "arousal": arousal, "scenes": scenes, "situations": situations}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python -m unittest tests.test_intent -v`
Expected: PASS（含新增 6 用例）

- [ ] **Step 6: Commit**

```bash
git add pipeline/intent.py tests/test_intent.py
git commit -m "feat: 场景信号检测器——scenes/situations/arousal 判定（S3+S4+S6）"
```

---

### Task 2: think.jinja2 注入场景/情境/唤醒度 + 特质选择

**Files:**
- Modify: `reasoning/prompts/think.jinja2`

**Interfaces:**
- Consumes: Task 1 的 `analyze_intent` 返回（scenes/situations/arousal）
- Produces: think 输出里包含"本轮激活特质"（≤2 个，供 speak 约束）

- [ ] **Step 1: 在 think.jinja2 追加注入段**（`## 对方此刻` 之后）

```jinja2
## 对方此刻的强度与场景（规则粗判，基本可信）
- 情绪强度：{{ arousal if arousal else '中性' }}（高=强烈，低=平静/消沉）
- 场景信号：{% for k,v in scenes.items() if v > 0.3 %}{{ k }}({{'%.0f' % (v*100) }}%) {% endfor %}
- 情境信号：{% for k,v in situations.items() if v > 0.3 %}{{ k }}({{'%.0f' % (v*100) }}%) {% endfor %}
```

- [ ] **Step 2: 在思考任务里加特质选择步骤**（`## 你的思考任务` 追加第 5 步）

```jinja2
5. 如果上面情境信号命中（空谈/迷茫/越线/传道授业/悲观等），选 1~2 个最贴切的性格侧面在表达里带出来（重实践/抓本质/爱才/平易/威严/善比喻/幽默/乐观/浪漫），但只是"怎么说的方式"，不改"这轮做什么"。情绪负面时不要幽默（先共情）。
```

- [ ] **Step 3: 验证渲染**（用 framework 构建一次 prompt）

Run: `python -c "from reasoning.framework import MaoReasoningEngine; e=MaoReasoningEngine(); p=e.build_think_prompt('q',[],[]); assert '场景信号' in p; print('think 注入 OK')"`
Expected: think 注入 OK

- [ ] **Step 4: Commit**

```bash
git add reasoning/prompts/think.jinja2
git commit -m "feat: think 注入场景/情境/唤醒度 + 特质选择任务（C5 接口）"
```

---

### Task 3: speak.jinja2 新增场景约束 + 特质约束

**Files:**
- Modify: `reasoning/prompts/speak.jinja2`

**Interfaces:**
- Consumes: think 输出（含激活特质提及）；scene_context
- Produces: speak 输出按场景/特质约束的自然表达

- [ ] **Step 1: 追加"特殊场景应对"段**（`## 自然对话规则` 之后）

```jinja2
## 特殊场景应对（命中时才用，未命中忽略）
- 对方在抬杠/不同意你：先接住分歧（"这话我听见了"），面子给足；原则问题才硬，对事不对人；分歧太僵可自嘲松动，但对方情绪低落时不幽默。
- 对方在开玩笑：顺势接住，别板脸；只损事不损人，一轮最多一处幽默。
- 对方提过分要求：拒绝的是事不是人，必带理由，尽量给替代；涉及原则直接拒，不绕弯。
- 对方只回"嗯/哦"：换个角度或换个话题，别硬追问。
- 对方情绪爆发（大哭/暴怒）：先稳住情绪，不评判不否定，陪着比出主意重要；动作（递茶/拍拍肩）比长篇安慰有力。
```

- [ ] **Step 2: 验证渲染**

Run: `python -c "from reasoning.framework import MaoReasoningEngine; e=MaoReasoningEngine(); p=e.build_speak_prompt('q','think'); assert '特殊场景应对' in p; print('speak OK')"`
Expected: speak OK

- [ ] **Step 3: Commit**

```bash
git add reasoning/prompts/speak.jinja2
git commit -m "feat: speak 新增特殊场景应对约束（7~11 层）"
```

---

### Task 4: web/app.py 接入 + 冷场挂起后端

**Files:**
- Modify: `web/app.py`

**Interfaces:**
- Consumes: Task 1/2/3 的检测器与 prompt
- Produces: think prompt 拿到完整 intent；idle-actions API 支持挂起语义

- [ ] **Step 1: 确认 intent 已含新键并注入**（app.py 925 行已传 intent=intent 进 build_think_prompt，framework 会把 intent 透传给 think.jinja2——验证 think.jinja2 里能取到 scenes/situations/arousal）

Run: `python -c "
import sys; sys.path.insert(0,'.')
from pipeline.intent import analyze_intent
it = analyze_intent('你说得不对')
print(it['scenes']['conflict'], it['arousal'])
"`
Expected: `0.8 neutral`（conflict 命中，arousal 中性）

- [ ] **Step 2: idle 后端支持"首动→挂起"**（idle-actions API 不动；挂起状态由前端 timer 控制，后端无需改——验证即可）

- [ ] **Step 3: Commit**（若 app.py 无需改动则跳过此步，直接进行 Task 5）

---

### Task 5: 前端冷场挂起（app.js）

**Files:**
- Modify: `web/static/app.js:397-430`

**Interfaces:**
- Consumes: `/api/idle-actions`（不变）
- Produces: 30s 首动 1 条 → 挂起（不再每 30s 换）→ 4min 纯计时场景建议 → 8min 离开预警

- [ ] **Step 1: 改 showIdleAction 为单次 + 纯计时挂起**

```javascript
async function showIdleAction(){
    idleCount++;
    // 只发一次确认动作，然后挂起（用户思考/离开时不再每30s骚扰）
    try{
        const r=await fetch('/api/idle-actions');const d=await r.json();
        if(d.actions?.length){idleEl=document.createElement('div');idleEl.className='idle-action';idleEl.textContent=d.actions[Math.floor(Math.random()*d.actions.length)];document.getElementById('chat').appendChild(idleEl);idleEl.scrollIntoView()}
    }catch(e){}
    // 场景建议改为纯计时：4min（8次×30s）直接触发，不依赖 refresh 循环
    const tired=currentFatigue==='yellow'||currentFatigue==='red';
    if((idleCount>=8||(tired&&idleCount>=4))&&!sceneSuggested){
        sceneSuggested=true;
        try{
            const sr=await fetch('/api/scene/suggest');const sd=await sr.json();
            if(sd.target&&sd.target!==currentScene){
                const suggestEl=document.createElement('div');
                suggestEl.className='idle-action';
                suggestEl.innerHTML=`${sd.message} <button onclick="setScene('${sd.target}')" style="margin-left:8px;padding:2px 10px;border-radius:10px;border:1px solid var(--primary);background:var(--primary);color:#fff;font-size:12px;cursor:pointer">好</button><button onclick="this.parentElement.remove()" style="margin-left:4px;padding:2px 10px;border-radius:10px;border:1px solid var(--border);background:transparent;font-size:12px;cursor:pointer">再坐会儿</button>`;
                document.getElementById('chat').appendChild(suggestEl);
                suggestEl.scrollIntoView();
            }
        }catch(e){}
    }
    // 挂起：不再重排定时器（原 refreshIdleAction 删除）
}
```

- [ ] **Step 2: 删除 refreshIdleAction 及对其引用**（app.js 430 行函数删除；showIdleAction 内不再调用）

- [ ] **Step 3: 验证语法**

Run: `node --check web/static/app.js`
Expected: 无输出（语法 OK）

- [ ] **Step 4: Commit**

```bash
git add web/static/app.js
git commit -m "feat: 冷场挂起——首动后静默，场景建议改纯计时（UX 修正）"
```

---

### Task 6: 全量回归 + 收尾

**Files:**
- Test: `tests/test_intent.py`、`tests/test_topic_thread.py`、`tests/test_kb_ops.py`

- [ ] **Step 1: 全量测试**

Run: `python -m unittest discover tests`
Expected: 全部 PASS（52 + 新增 6 = 58 用例）

- [ ] **Step 2: 语法验证全部改动文件**

Run: `python -c "import ast; [ast.parse(open(f,encoding='utf-8').read()) for f in ['pipeline/intent.py','web/app.py']]; print('syntax ok')"`
Expected: syntax ok

- [ ] **Step 3: 更新 progress.md 台账**

追加：S3+S4+S6 检测器已实现（commit 列表），测试 58 用例

- [ ] **Step 4: 更新设计文档状态行**（`scene-signal-detector-design.md` 状态 → ✅ 已实现）
