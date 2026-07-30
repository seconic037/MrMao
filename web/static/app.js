// 主席模拟器 V2 — 前端逻辑
let loading = false;
let idleTimer = null;
let idleEl = null;
let currentFatigue = 'green';

// ── 消息 ──────────────────────────────────────
async function send() {
    const m = document.getElementById('msg').value.trim();
    if (!m || loading) return;
    const w = document.getElementById('welcome'); if (w) w.remove();
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

function ask(t) { document.getElementById('msg').value = t; send(); }

// ── 统计栏 ────────────────────────────────────
function updateStats(d) {
    const el = document.getElementById('stats');
    if (d.tokens) {
        const cost = (d.cumulative_tokens / 1_000_000).toFixed(3);
        el.innerHTML = `📊 本轮: ${(d.tokens/1000).toFixed(1)}K | 累计: ${(d.cumulative_tokens/1000).toFixed(1)}K tokens | ≈¥${cost}`;
    }
    // 疲劳动作
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
        addMsg('assistant', '[端起茶杯喝了一口，精神了不少] 好了，接着聊。');
    } catch (e) { console.error(e); }
}

// ── 开场白 ────────────────────────────────────
setTimeout(async () => {
    try {
        const r = await fetch('/api/greeting');
        const d = await r.json();
        if (d.greeting) {
            const w = document.getElementById('welcome');
            if (w) w.remove();
            addMsg('assistant', d.greeting);
            resetIdleTimer();
        }
    } catch (e) { }
}, 1000);

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
resetIdleTimer();
