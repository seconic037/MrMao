// 主席模拟器 V2 — 前端逻辑
let loading = false;
let idleTimer = null;
let idleEl = null;
let currentFatigue = 'green';

// ── 进入聊天 ──────────────────────────────────
async function enterChat() {
    document.getElementById('cover').style.display = 'none';
    document.getElementById('chat').style.display = 'flex';
    document.getElementById('stats').style.display = 'block';
    document.getElementById('fatigueBar').style.display = 'block';
    resetIdleTimer();
    try {
        const r = await fetch('/api/greeting');
        const d = await r.json();
        if (d.greeting) addMsg('assistant', d.greeting);
    } catch(e) {}
}

// ── 让主席休息 ────────────────────────────────
function restChairman() {
    document.getElementById('cover').style.display = 'flex';
    document.getElementById('chat').style.display = 'none';
    document.getElementById('chat').innerHTML = '';
    document.getElementById('stats').style.display = 'none';
    document.getElementById('fatigueBar').style.display = 'none';
    document.getElementById('compactBtns').style.display = 'none';
    if (idleEl) { idleEl.remove(); idleEl = null; }
    if (idleTimer) clearTimeout(idleTimer);
    setStatus('休息中');
    fetch('/api/compact', { method: 'POST' }).catch(() => {});
}

// ── 消息 ──────────────────────────────────────
async function send() {
    const m = document.getElementById('msg').value.trim();
    if (!m || loading) return;
    addMsg('user', m);
    document.getElementById('msg').value = '';
    setStatus('思考中...');
    loading = true;
    document.getElementById('sendBtn').disabled = true;
    resetIdleTimer();
    try {
        const r = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: m })
        });
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || '请求失败'); }
        const d = await r.json();
        addMsg('assistant', d.answer || '');
        updateStats(d);
        currentFatigue = d.fatigue || 'green';
        updateFatigueUI();
        updateCompactButtons();
    } catch (e) { addMsg('assistant', '❌ ' + e.message); }
    setStatus('就绪');
    loading = false;
    document.getElementById('sendBtn').disabled = false;
}

function addMsg(role, html) {
    const d = document.createElement('div');
    d.className = 'message ' + role;
    d.innerHTML = html.replace(/\n/g, '<br>');
    document.getElementById('chat').appendChild(d);
    d.scrollIntoView();
}

function ask(t) {
    enterChat();
    document.getElementById('msg').value = t;
    setTimeout(() => send(), 100);
}

// ── 统计栏 ────────────────────────────────────
function updateStats(d) {
    const el = document.getElementById('stats');
    if (d.tokens) {
        const cost = (d.cumulative_tokens / 1_000_000).toFixed(3);
        el.innerHTML = `📊 本轮: ${(d.tokens/1000).toFixed(1)}K | 累计: ${(d.cumulative_tokens/1000).toFixed(1)}K tokens | ≈¥${cost}`;
    }
    if (d.fatigue === 'yellow' || d.fatigue === 'red') {
        fetch('/api/idle-actions').then(r => r.json()).then(data => {
            if (data.actions?.length) {
                const a = document.createElement('div');
                a.className = 'idle-action';
                a.textContent = data.actions[0].replace('等你开口', '').replace('等着你继续', '');
                document.getElementById('chat').appendChild(a);
                a.scrollIntoView();
            }
        });
    }
}

function setStatus(txt) {
    document.getElementById('status').textContent = '● ' + txt;
}

// ── 疲劳度 ────────────────────────────────────
function updateFatigueUI() {
    const bar = document.getElementById('fatigueBar');
    if (!bar) return;
    bar.className = 'fatigue-bar ' + currentFatigue;
    const labels = { green: '🟢 精神饱满', yellow: '🟡 有点累了', red: '🔴 需要休息' };
    bar.textContent = labels[currentFatigue] || '';
}

function updateCompactButtons() {
    const wrap = document.getElementById('compactBtns');
    if (!wrap) return;
    wrap.style.display = (currentFatigue === 'yellow' || currentFatigue === 'red') ? 'flex' : 'none';
}

async function doCompact() {
    try {
        const r = await fetch('/api/compact', { method: 'POST' });
        const d = await r.json();
        currentFatigue = 'green';
        updateFatigueUI();
        updateCompactButtons();
        addMsg('assistant', '[老人家端起茶杯喝了一口，精神了不少] 好了，接着聊。');
    } catch (e) { console.error(e); }
}

// ── 冷场计时器 ─────────────────────────────────
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
    } catch (e) { }
}

function refreshIdleAction() {
    if (idleEl) idleEl.remove();
    showIdleAction();
}

// ── 日志侧栏 ──────────────────────────────────
async function toggleLogs() {
    const panel = document.getElementById('logPanel');
    if (panel.style.display === 'block') {
        panel.style.display = 'none';
        return;
    }
    panel.style.display = 'block';
    panel.innerHTML = '<div class="log-loading">加载中...</div>';
    try {
        const r = await fetch('/api/logs');
        const d = await r.json();
        let html = '<div class="log-header">📋 对话日志 <span onclick="toggleLogs()" style="cursor:pointer;float:right">✕</span></div>';
        html += '<div class="log-sessions">';
        for (const s of (d.sessions || []).slice(0, 10)) {
            html += `<div class="log-session">📄 ${s.name} (${(s.size/1024).toFixed(1)}KB)</div>`;
        }
        html += '</div>';
        if (d.entries?.length) {
            html += '<div class="log-current">当前会话：<br>';
            for (const e of d.entries.slice(-20)) {
                const cls = e.role === 'chairman' ? 'log-chairman' : 'log-user';
                html += `<div class="${cls}"><b>${e.role === 'chairman' ? '主席' : '你'}：</b>${e.content.substring(0, 50)}...</div>`;
            }
            html += '</div>';
        }
        panel.innerHTML = html;
    } catch (e) { panel.innerHTML = '<div class="log-loading">加载失败</div>'; }
}

// ── 初始化 ────────────────────────────────────
fetch('/api/status').then(r => r.json()).then(s => {
    if (!s.rag) setStatus('RAG未就绪');
    if (!s.llm) setStatus('LLM未配置');
});
loadTopics();
loadCatalog();
loadHotspots();

// ── 热点话题 ──────────────────────────────────
async function loadHotspots() {
    try {
        const r = await fetch('/api/hotspots');
        const d = await r.json();
        const el = document.getElementById('hotspotList');
        if (!el || !d.hotspots) return;
        el.innerHTML = d.hotspots.map(h => 
            `<div class="hotspot-item" onclick="enterChat();setTimeout(()=>{document.getElementById('msg').value='${h.title}，你怎么看？';send()},200)">
                <span>${h.title}${h.tag?`<span class="hot-tag">${h.tag}</span>`:''}</span>
            </div>`
        ).join('');
    } catch(e) {}
}

// ── 首页话题 ──────────────────────────────────
async function loadTopics() {
    try {
        const r = await fetch('/api/catalog');
        const d = await r.json();
        const el = document.getElementById('topicList');
        if (!el || !d.topics) return;
        el.innerHTML = d.topics.map(t => 
            `<span class="topic-item" onclick="enterChat();setTimeout(()=>{document.getElementById('msg').value='${t}';send()},200)">${t}</span>`
        ).join('');
    } catch(e) {}
}

// ── 著作目录 ──────────────────────────────────
let catalogData = null;
async function loadCatalog() {
    try {
        const r = await fetch('/api/catalog');
        const d = await r.json();
        catalogData = d.catalog;
    } catch(e) {}
}

function toggleCatalog() {
    const el = document.getElementById('catalog');
    const tog = document.querySelector('.catalog-toggle');
    if (el.style.display === 'block') {
        el.style.display = 'none'; tog.textContent = '展开';
        return;
    }
    if (!catalogData) { loadCatalog(); return; }
    let html = '';
    catalogData.forEach(cat => {
        html += `<div class="cat-group"><div class="cat-name" onclick="toggleVol(this)">📁 ${cat.name}</div><div class="vol-list">`;
        cat.volumes.forEach(vol => {
            html += `<div class="vol-item" onclick="loadArticleList('${vol.id}')">📄 ${vol.name} (${vol.count}篇)</div>`;
        });
        html += '</div></div>';
    });
    el.innerHTML = html;
    el.style.display = 'block';
    tog.textContent = '收起';
}

function toggleVol(el) {
    const list = el.nextElementSibling;
    list.classList.toggle('open');
}

async function loadArticleList(volId) {
    const map = {mx1:'毛选第一卷',mx2:'毛选第二卷',mx3:'毛选第三卷',mx4:'毛选第四卷',
                 wj5:'毛泽东文集第五卷',wj6:'毛泽东文集第六卷',wj7:'毛泽东文集第七卷',
                 sc1:'毛泽东诗词',jw1:'建国以来毛泽东文稿'};
    try {
        const r = await fetch(`/api/articles?source=${encodeURIComponent(map[volId]||'')}`);
        const d = await r.json();
        const el = document.getElementById('catalog');
        let html = '<div class="reader-back" onclick="toggleCatalog()">← 返回目录</div>';
        d.articles.forEach(a => {
            html += `<div class="article-item" onclick="readArticle('${encodeURIComponent(a.source)}','${encodeURIComponent(a.title)}')">${a.title} (${a.date})</div>`;
        });
        el.innerHTML = html;
    } catch(e) {}
}

async function readArticle(source, title) {
    try {
        const r = await fetch(`/api/read?source=${source}&title=${title}`);
        const d = await r.json();
        document.getElementById('readerTitle').textContent = d.title;
        document.getElementById('readerContent').textContent = d.content || d.error || '';
        document.getElementById('catalog').style.display = 'none';
        document.getElementById('reader').style.display = 'block';
    } catch(e) {}
}

function closeReader() {
    document.getElementById('reader').style.display = 'none';
    document.getElementById('catalog').style.display = 'block';
}
