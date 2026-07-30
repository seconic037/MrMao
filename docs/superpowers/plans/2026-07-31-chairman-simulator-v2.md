# 主席模拟器 V2 — Implementation Plan

> **For agentic workers:** Inline execution. Small scope (2 new files + 3 modifications).

**Goal:** 将毛选思维引擎升级为两阶段对话引擎，注入毛泽东人格，增加 MUD 动作和主动交互。

**Architecture:** think.jinja2（思维）→ speak.jinja2（表达）两阶段分离，前端加开场白/冷场计时器。

**Tech Stack:** 同现有项目 — Python/FastAPI/ChromaDB/Jinja2/DeepSeek

## Global Constraints

- 两阶段 LLM 调用，预计总延迟 < 8s
- 保留 qa_with_reasoning.jinja2 作为单阶段回退
- 冷场 = 30s，动作池 8 条
- 开场白池 4 条 + 可选热点
- 回答 3-5 句 + 反问结尾
- [动作] 每段最多 1 个

---

### Task 1: 两阶段 Prompt 文件

**Files:**
- Create: `reasoning/prompts/think.jinja2`
- Create: `reasoning/prompts/speak.jinja2`

- [ ] **Step 1: think.jinja2**

```
你是毛泽东的"内心思考"，不对外说话。

## 知识框架
{{ knowledge_base }}

## 相关原文
{% for r in rag_results %}
（{{ r.title }}，{{ r.date }}）{{ r.text }}
{% endfor %}

## 对方说
{{ question }}

## 任务
用 3-5 句话完成以下分析（可以用关键词，不用完整句子）：

1. **主要矛盾**：这件事的根本矛盾是什么？谁和谁在斗？
2. **立场**：站在哪边看问题？
3. **客观+主观**：客观条件是什么？主观上能做什么？
4. **可引用的诗词/典故**：有没有自己的诗词或典故可以呼应？
5. **引导方向**：接下来可以反问对方什么？
```

- [ ] **Step 2: speak.jinja2**

```
你是毛泽东。现在你在和人聊天。

## 你的性格
- 自信从容，不卑不亢。偶尔幽默，偶尔犀利。
- 善用比喻——把大道理用普通人的话说透。「你要晓得」「我看呐」开头。
- 常用句式：一方面…另一方面…、看起来…实际上…、不是…而是…
- 引经据典信手拈来——《红楼梦》《水浒传》《三国》随口提。
- 偶尔引用自己的诗词，但要自然融入。

## 说话习惯
- 每次 3-5 句话。不写文章，不列一二三四。
- 说人话。不用「根据XX的论述」这种句式。
- 可以加中括号动作：[弹了弹烟灰] [靠在藤椅上] [端起搪瓷杯喝了口茶]
- 每段话最多 1 个动作。

## 你心里想的是
{{ thinking_result }}

## 对方刚说
{{ question }}

## 现在你开口
语气要像你——毛泽东。结尾反问一句，看看对方怎么想。
```

- [ ] **Step 3: 提交**

```bash
git add reasoning/prompts/think.jinja2 reasoning/prompts/speak.jinja2
git commit -m "feat: add two-stage prompts (think + speak) for chairman persona"
```

---

### Task 2: 后端改造 — 两阶段 API + 开场白

**Files:**
- Modify: `web/app.py`
- Modify: `reasoning/framework.py`

- [ ] **Step 1: 扩展 framework.py 支持两阶段**

在 `MaoReasoningEngine` 类中新增 `build_think_prompt` 和 `build_speak_prompt` 方法：

```python
def build_think_prompt(self, question, rag_results=None):
    return self._jinja_env.get_template("think.jinja2").render(
        question=question,
        knowledge_base=self._knowledge_base,
        rag_results=rag_results or []
    )

def build_speak_prompt(self, question, thinking_result):
    return self._jinja_env.get_template("speak.jinja2").render(
        question=question,
        thinking_result=thinking_result
    )
```

保留原有 `build_prompt` 作为单阶段回退。

- [ ] **Step 2: 修改 web/app.py 的 /api/chat 为两阶段**

```python
@app.post("/api/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    if not llm:
        raise HTTPException(503, "LLM 未配置")
    
    rags = retriever.search(req.message, top_k=5) if retriever else []
    
    # 阶段 1：思维
    think_prompt = engine.build_think_prompt(req.message, rags)
    think_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": think_prompt}],
        temperature=0.3, max_tokens=300
    )
    thinking = think_resp.choices[0].message.content
    
    # 阶段 2：表达
    speak_prompt = engine.build_speak_prompt(req.message, thinking)
    speak_resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": "你是毛泽东本人，在和别人聊天。"},
                  {"role": "user", "content": speak_prompt}],
        temperature=0.9, max_tokens=400
    )
    
    return ChatResp(
        answer=speak_resp.choices[0].message.content,
        sources=[{"text": r.text[:200], "source": r.source, "title": r.title, "date": r.date, "score": r.score} for r in rags]
    )
```

- [ ] **Step 3: 新增 /api/greeting 端点**

```python
GREETINGS = [
    "来了？坐。今天想聊什么？",
    "我正好在看今天的报纸。你有什么事？",
    "[掐灭烟头] 说吧，遇到什么难题了？",
    "我刚写了首词，你要不要看看？"
]

IDLE_ACTIONS = [
    "[抽了口烟，等你开口]",
    "[端起搪瓷杯，喝了口浓茶]",
    "[靠在藤椅上，目光望向窗外]",
    "[拿笔在纸上写了几个字，又划掉了]",
    "[翻了翻手边的毛选]",
    "[站起来在屋里踱了两步]",
    "[掐灭烟头，若有所思地看着你]",
    "[微笑了一下，等着你继续]"
]

@app.get("/api/greeting")
async def greeting():
    import random
    return {"greeting": random.choice(GREETINGS)}

@app.get("/api/idle-actions")
async def idle_actions():
    import random
    return {"actions": random.sample(IDLE_ACTIONS, min(3, len(IDLE_ACTIONS)))}
```

- [ ] **Step 4: 提交**

```bash
git add web/app.py reasoning/framework.py
git commit -m "feat: two-stage chat API + greeting/idle endpoints"
```

---

### Task 3: 前端改造 — 开场白 + 冷场 + 动作渲染

**Files:**
- Modify: `web/static/app.js`
- Modify: `web/static/style.css`

- [ ] **Step 1: app.js 加开场白逻辑**

在文件末尾添加：

```javascript
// 开场白
setTimeout(async () => {
    try {
        const r = await fetch('/api/greeting');
        const d = await r.json();
        if (d.greeting) {
            const welcome = document.getElementById('welcome');
            if (welcome) welcome.remove();
            addMsg('assistant', d.greeting);
        }
    } catch(e) {}
}, 1000);
```

- [ ] **Step 2: app.js 加冷场计时器**

```javascript
// 冷场计时器
let idleTimer = null;
let idleEl = null;

function resetIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    if (idleEl) { idleEl.remove(); idleEl = null; }
    idleTimer = setTimeout(showIdleAction, 30000);
}

async function showIdleAction() {
    try {
        const r = await fetch('/api/idle-actions');
        const d = await r.json();
        if (d.actions?.length) {
            idleEl = document.createElement('div');
            idleEl.className = 'idle-action';
            idleEl.textContent = d.actions[Math.floor(Math.random() * d.actions.length)];
            document.getElementById('chat').appendChild(idleEl);
            idleEl.scrollIntoView();
            idleTimer = setTimeout(refreshIdleAction, 30000);
        }
    } catch(e) {}
}

function refreshIdleAction() {
    if (idleEl) idleEl.remove();
    showIdleAction();
}
```

在 `send()` 函数末尾加 `resetIdleTimer()`。

- [ ] **Step 3: style.css 加动作样式**

```css
.idle-action{text-align:center;color:var(--text-light);font-style:italic;padding:12px;font-size:14px;opacity:.7;animation:fadeIn 1s}
```

- [ ] **Step 4: 提交**

```bash
git add web/static/app.js web/static/style.css
git commit -m "feat: add greeting, idle timer, and action rendering to frontend"
```

---

### Task 4: 集成测试

- [ ] **Step 1: 启动服务测试**

```bash
python run_server.py --port=8001 &
sleep 5
# 测试普通对话
curl -s -X POST http://localhost:8001/api/chat -H "Content-Type: application/json" -d '{"message":"怎么判断一个人靠不靠谱"}' | python -c "import sys,json; d=json.load(sys.stdin); print(d['answer'][:200])"
# 测试开场白
curl -s http://localhost:8001/api/greeting
# 测试冷场动作
curl -s http://localhost:8001/api/idle-actions
```

Expected: 回答有人味儿，开场白和动作正常返回。

- [ ] **Step 2: 提交**

```bash
git add -A && git commit -m "test: integration test for chairman simulator V2"
```
