// 主席模拟器 — 手机版
let loading=false,idleTimer=null,idleEl=null,currentFatigue='green',catalogData=null,logData=null;

// ── 标签切换 ────────────────────────────────
function switchTab(name){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.getElementById('page-'+name).classList.add('active');
    document.getElementById('tab-'+name).classList.add('active');
    if(name==='logs')loadLogs();
    if(name==='read')loadCatalogView();
}
// ── 聊天 ────────────────────────────────────
async function enterChat(){
    switchTab('chat');
    resetIdleTimer();
    try{const r=await fetch('/api/greeting');const d=await r.json();if(d.greeting)addMsg('assistant',d.greeting)}catch(e){}
}
async function send(){
    const m=document.getElementById('msg').value.trim();
    if(!m||loading)return;
    addMsg('user',m);document.getElementById('msg').value='';loading=true;document.getElementById('sendBtn').disabled=true;resetIdleTimer();
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
        if(!r.ok){const e=await r.json();throw new Error(e.detail||'请求失败')}
        const d=await r.json();
        addMsg('assistant',d.answer||'');updateStats(d);currentFatigue=d.fatigue||'green';updateFatigueUI();updateCompactBtns();
    }catch(e){addMsg('assistant','❌ '+e.message)}
    loading=false;document.getElementById('sendBtn').disabled=false;
}
function addMsg(role,html){
    const d=document.createElement('div');d.className='message '+role;d.innerHTML=html.replace(/\n/g,'<br>');
    document.getElementById('chat').appendChild(d);d.scrollIntoView();
}
function ask(t){document.getElementById('msg').value=t;enterChat();setTimeout(()=>send(),200);}

// ── 统计 ────────────────────────────────────
function updateStats(d){
    if(d.tokens)document.getElementById('stats').innerHTML=`📊 ${(d.tokens/1000).toFixed(1)}K | 累计 ${(d.cumulative_tokens/1000).toFixed(1)}K | ≈¥${(d.cumulative_tokens/1_000_000).toFixed(3)}`;
}
function updateFatigueUI(){
    const bar=document.getElementById('fatigueBar');if(!bar)return;
    bar.className='fatigue-bar '+(currentFatigue||'green');
    bar.textContent={green:'🟢 精神饱满',yellow:'🟡 累了',red:'🔴 该休息了'}[currentFatigue]||'';
}
function updateCompactBtns(){
    const w=document.getElementById('compactBtns');if(!w)return;
    w.style.display=(currentFatigue==='yellow'||currentFatigue==='red')?'flex':'none';
}
async function doCompact(){
    try{await fetch('/api/compact',{method:'POST'});currentFatigue='green';updateFatigueUI();updateCompactBtns();addMsg('assistant','[老人家端起茶杯喝了一口，精神了不少] 好了，接着聊。')}catch(e){}
}

// ── 冷场 ────────────────────────────────────
function resetIdleTimer(){if(idleTimer)clearTimeout(idleTimer);if(idleEl){idleEl.remove();idleEl=null;}idleTimer=setTimeout(showIdleAction,30000);}
async function showIdleAction(){
    try{const r=await fetch('/api/idle-actions');const d=await r.json();if(d.actions?.length){idleEl=document.createElement('div');idleEl.className='idle-action';idleEl.textContent=d.actions[Math.floor(Math.random()*d.actions.length)];document.getElementById('chat').appendChild(idleEl);idleEl.scrollIntoView();idleTimer=setTimeout(refreshIdleAction,30000)}}catch(e){}
}
function refreshIdleAction(){if(idleEl)idleEl.remove();showIdleAction();}

// ── 记录页 ──────────────────────────────────
async function loadLogs(){try{const r=await fetch('/api/logs');logData=await r.json();showCurrentLog()}catch(e){}}
function showCurrentLog(){
    const el=document.getElementById('logBody');if(!logData?.entries){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    el.innerHTML=logData.entries.map(e=>`<div class="log-entry"><b>${e.role==='chairman'?'主席':'你'}：</b>${e.content}</div>`).join('');
    document.querySelectorAll('#page-logs .log-tab').forEach((t,i)=>t.classList.toggle('active',i===0));
}
function showHistoryLogs(){
    const el=document.getElementById('logBody');if(!logData?.sessions){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    el.innerHTML=logData.sessions.map(s=>`<div class="log-session-item"><span>📄 ${s.name} (${(s.size/1024).toFixed(1)}KB)</span><span class="log-del" onclick="deleteLog('${s.name}')">🗑</span></div>`).join('');
    document.querySelectorAll('#page-logs .log-tab').forEach((t,i)=>t.classList.toggle('active',i===1));
}
async function deleteLog(name){if(!confirm('删除这条记录？'))return;try{await fetch(`/api/logs/${name}`,{method:'DELETE'});showHistoryLogs()}catch(e){}}

// ── 阅读页 ──────────────────────────────────
async function loadCatalogView(){
    try{const r=await fetch('/api/catalog');catalogData=(await r.json()).catalog;
        const el=document.getElementById('catalogView');
        el.innerHTML=catalogData.map(c=>`<div class="cat-name" onclick="toggleCat(this)">📁 ${c.name}</div><div class="vol-list" style="display:none">${c.volumes.map(v=>`<div class="vol-item" onclick="loadArticles('${v.id}')">📄 ${v.name} (${v.count}篇)</div>`).join('')}</div>`).join('');
    }catch(e){}
}
function toggleCat(el){const list=el.nextElementSibling;list.style.display=list.style.display==='block'?'none':'block';}
async function loadArticles(volId){
    const map={mx1:'毛选第一卷',mx2:'毛选第二卷',mx3:'毛选第三卷',mx4:'毛选第四卷',wj5:'毛泽东文集第五卷',wj6:'毛泽东文集第六卷',wj7:'毛泽东文集第七卷',sc1:'毛泽东诗词',jw1:'建国以来毛泽东文稿'};
    try{const r=await fetch(`/api/articles?source=${encodeURIComponent(map[volId]||'')}`);const d=await r.json();
        document.getElementById('catalogView').innerHTML='<div style="color:var(--primary);cursor:pointer;padding:8px" onclick="loadCatalogView()">← 返回目录</div>'+d.articles.map(a=>`<div class="article-item" onclick="readArticle('${encodeURIComponent(a.source)}','${encodeURIComponent(a.title)}')">${a.title} (${a.date})</div>`).join('')
    }catch(e){}
}
function showCatalogView(){document.getElementById('catalogView').style.display='block';document.getElementById('readerView').style.display='none';loadCatalogView();}
async function readArticle(source,title){
    try{const r=await fetch(`/api/read?source=${source}&title=${title}`);const d=await r.json();
        document.getElementById('catalogView').style.display='none';document.getElementById('readerView').style.display='block';
        document.getElementById('readerTitle').innerHTML=`<span onclick="showCatalogView()" style="cursor:pointer;color:var(--primary)">← 返回</span> ${d.title}`;
        document.getElementById('readerContent').textContent=d.content||d.error||'';
    }catch(e){}
}

// ── 首页 ────────────────────────────────────
async function loadTopics(){try{const r=await fetch('/api/catalog');const d=await r.json();document.getElementById('topicList').innerHTML=d.topics.map(t=>`<span class="topic-item" onclick="ask('${t}')">${t}</span>`).join('')}catch(e){}}
async function loadHotspots(){try{const r=await fetch('/api/hotspots');const d=await r.json();document.getElementById('hotspotList').innerHTML=d.hotspots.map(h=>`<div class="hotspot-item" onclick="ask('${h.title}，你怎么看？')"><span>${h.title}${h.tag?`<span class="hot-tag">${h.tag}</span>`:''}</span></div>`).join('')}catch(e){}}

// ── 启动 ────────────────────────────────────
fetch('/api/status').then(r=>r.json()).then(s=>{if(!s.rag)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ RAG未就绪');if(!s.llm)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ LLM未配置')});
loadTopics();loadHotspots();
