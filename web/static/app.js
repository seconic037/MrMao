// 主席模拟器 — 手机版
let loading=false,idleTimer=null,idleEl=null,currentFatigue='green',catalogData=null,logData=null;

// ── 标签切换 ────────────────────────────────
function switchTab(name){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.getElementById('page-'+name).classList.add('active');
    document.getElementById('tab-'+name).classList.add('active');
    if(name==='read')loadCatalogView();
    if(name!=='chat'&&currentPage==='chat')askSaveLog();
    currentPage=name;
}
let currentPage='home';
let hasNewMessages=false;

// ── 入口面板 ────────────────────────────────
async function showEntryPanel(){
    try{const r=await fetch('/api/session/status');const s=await r.json();const r2=await fetch('/api/logs');const logs=await r2.json();
        const el=document.getElementById('entryOptions');
        let html='';
        if(s.active)html+=`<div class="entry-opt" onclick="closeEntryModal();switchTab('chat')">💬 继续上次聊天<br><small>${s.rounds}轮对话，${(s.tokens/1000).toFixed(0)}K tokens</small></div>`;
        if(!s.active&&logs.sessions&&logs.sessions.length>0){
            html+='<div class="modal-btns" style="margin-top:8px"><select id="logSelect" style="padding:8px;border-radius:8px;border:1px solid var(--border);font-size:13px">';
            logs.sessions.forEach(l=>{html+=`<option value="${l.name}">${l.title||l.name} · ${l.rounds||'?'}条</option>`});
            html+='</select><button onclick="resumeFromLog()" style="margin-top:6px">📜 继续这个话题</button></div>';
        }
        html+='<div class="entry-opt" onclick="startNewSession()">🆕 从头开始</div>';
        if(!html)html='<p style="color:var(--text-light)">暂无聊天记录。开始全新对话吧。</p><div class="entry-opt" onclick="startNewSession()">🆕 开始全新对话</div>';
        el.innerHTML=html;
        document.getElementById('entryModal').style.display='flex';
    }catch(e){enterChat();}
}
function closeEntryModal(){document.getElementById('entryModal').style.display='none'}
function startNewSession(){
    closeEntryModal();
    fetch('/api/session/discard',{method:'POST'});
    enterChat();
}
async function resumeFromLog(){
    const fname=document.getElementById('logSelect').value;
    closeEntryModal();
    try{const r=await fetch(`/api/session/summarize?filename=${encodeURIComponent(fname)}`,{method:'POST'});const d=await r.json();
        switchTab('chat');const greeting='上次咱们聊到：'+d.summary.substring(0,60)+'。后来您怎么看？';
        addMsg('assistant',greeting);
        // 注入上下文
        window._hotContext='【对话背景】'+d.summary;
    }catch(e){switchTab('chat')}
}

// ── 退出弹窗 ────────────────────────────────
async function askSaveLog(){
    if(!hasNewMessages)return;
    const el=document.getElementById('exitModal');el.style.display='flex';
    try{const r=await fetch('/api/session/status');const d=await r.json();
        el.querySelector('p').textContent=`当前对话有 ${d.rounds} 轮，是否保存？`
    }catch(e){}
}
function closeExitModal(){document.getElementById('exitModal').style.display='none'}
async function exitAndSave(){
    closeExitModal();
    await fetch('/api/session/save',{method:'POST'});
    hasNewMessages=false;
    switchTab('home');
}
async function exitAndDiscard(){
    closeExitModal();
    await fetch('/api/session/discard',{method:'POST'});
    hasNewMessages=false;
    switchTab('home');
}
// ── 聊天 ────────────────────────────────────
async function enterChat(){
    switchTab('chat');
    resetIdleTimer();
    // 检查是否有活跃会话
    try{const r=await fetch('/api/session/status');const d=await r.json();if(!d.active){
        try{const g=await fetch('/api/greeting');const dd=await g.json();if(dd.greeting)addMsg('assistant',dd.greeting)}catch(e){}
    }}catch(e){}
}
async function send(){
    const m=document.getElementById('msg').value.trim();
    if(!m||loading)return;
    addMsg('user',m);
    // 热点上下文：注入到 API 请求但不在聊天显示
    let apiMsg=m;
    if(window._hotContext){apiMsg=m+'\n\n【背景信息】'+window._hotContext;window._hotContext=null;}
    document.getElementById('msg').value='';loading=true;document.getElementById('sendBtn').disabled=true;resetIdleTimer();hasNewMessages=true;
    // 等待动画 + 动态省略号
    const loadingEl=addMsg('assistant','[主席抽了口烟，正在思考]');
    loadingEl.classList.add('loading');
    let dots=0;const dotTimer=setInterval(()=>{dots=(dots+1)%4;loadingEl.innerHTML='[主席抽了口烟，正在思考'+'.'.repeat(dots)+']'},500);
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:apiMsg})});
        if(!r.ok){const e=await r.json();throw new Error(e.detail||'请求失败')}
        const d=await r.json();
        clearInterval(dotTimer);loadingEl.remove();
        typewrite(d.answer||'',d);
    }catch(e){clearInterval(dotTimer);loadingEl.remove();addMsg('assistant','❌ '+e.message)}
    loading=false;document.getElementById('sendBtn').disabled=false;
}
function addMsg(role,html){
    const d=document.createElement('div');d.className='message '+role;d.innerHTML=html.replace(/\n/g,'<br>');
    document.getElementById('chat').appendChild(d);d.scrollIntoView();return d;
}
function typewrite(text,data){
    const el=addMsg('assistant','');
    let i=0;const len=text.length;
    const speed=len<100?25:len<300?40:60;
    function tick(){
        if(i>=len){if(data)updateStats(data);if(data){currentFatigue=data.fatigue||'green';updateFatigueUI();updateCompactBtns()}return}
        let chunk=1;
        if(text[i]==='['){const end=text.indexOf(']',i);if(end>i){chunk=end-i+1}else{chunk=1}}
        el.innerHTML+=text.substring(i,i+chunk).replace(/\n/g,'<br>');
        i+=chunk;el.scrollIntoView();
        const delay=chunk>1?speed*2:speed;
        setTimeout(tick,delay);
    }
    tick();
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

// ── 记录 ──────────────────────────────────
async function openLogs(){
    const panel=document.getElementById('logPanel');panel.style.display='block';
    panel.innerHTML='<div class="log-loading">加载中...</div>';
    try{const r=await fetch('/api/logs');logData=await r.json();renderLogPanel()}catch(e){panel.innerHTML='<div class="log-loading">加载失败</div>'}
}
function closeLogs(){document.getElementById('logPanel').style.display='none'}
function renderLogPanel(){
    const panel=document.getElementById('logPanel');
    let html='<div class="log-header">📋 聊天日志 <span onclick="closeLogs()" style="cursor:pointer;float:right">✕</span></div>';
    html+='<div class="log-tabs"><span class="log-tab active" onclick="showCurrentLogTab()">当前会话</span><span class="log-tab" onclick="showHistoryLogs()">历史记录</span></div>';
    html+='<div class="log-body" id="logBody"></div>';
    panel.innerHTML=html;showCurrentLogTab();
}
function showCurrentLogTab(){
    const el=document.getElementById('logBody');if(!logData?.entries?.length){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    el.innerHTML=logData.entries.map(e=>`<div class="log-entry"><b>${e.role==='chairman'?'主席':'你'}：</b>${e.content}</div>`).join('');
    if(logData.active_rounds>0)el.innerHTML+='<div class="log-actions"><button onclick="summarizeCurrent()">🤖 一键总结</button></div>';
    document.querySelectorAll('#logPanel .log-tab').forEach((t,i)=>t.classList.toggle('active',i===0));
}
function showHistoryLogs(){
    const el=document.getElementById('logBody');if(!logData?.sessions){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    el.innerHTML=logData.sessions.map(s=>{
        const label=s.title||(s.time?s.time.substring(5,16):s.name);
        return `<div class="log-session-item">
            <span class="log-title" onclick="editTitle('${s.name}','${(s.title||'').replace(/'/g,"\\'")}')">📄 ${label} · ${s.rounds||'?'}条</span>
            <span class="log-acts"><span onclick="summarizeLog('${s.name}')" style="color:var(--primary);cursor:pointer;margin-right:8px" title="一键总结">🤖</span><span class="log-del" onclick="deleteLogWithConfirm('${s.name}')">🗑</span></span>
        </div>`
    }).join('');
    document.querySelectorAll('#logPanel .log-tab').forEach((t,i)=>t.classList.toggle('active',i===1));
}
async function deleteLogWithConfirm(filename){
    if(!confirm('确定删除这条日志？此操作不可恢复。'))return;
    try{await fetch(`/api/logs/${filename}`,{method:'DELETE'});const r=await fetch('/api/logs');logData=await r.json();showHistoryLogs()}catch(e){}
}
async function summarizeCurrent(){
    if(!logData?.current)return;
    const el=document.getElementById('logBody');el.innerHTML+='<div class="log-loading">总结中...</div>';
    try{const r=await fetch(`/api/session/summarize?filename=${encodeURIComponent(logData.current)}`,{method:'POST'});const d=await r.json();
        el.innerHTML+='<div class="log-summary"><b>🤖 AI 总结：</b><br>'+d.summary+'</div>'}catch(e){}
}
async function summarizeLog(filename){
    const el=document.getElementById('logBody');el.innerHTML+='<div class="log-loading">总结中...</div>';
    try{const r=await fetch(`/api/session/summarize?filename=${encodeURIComponent(filename)}`,{method:'POST'});const d=await r.json();
        el.innerHTML+='<div class="log-summary"><b>🤖 AI 总结：</b><br>'+d.summary+'</div>'}catch(e){}
}
async function editTitle(filename,currentTitle){
    const t=prompt('编辑日志标题：',currentTitle||'');
    if(t===null)return;
    try{await fetch(`/api/session/title?filename=${encodeURIComponent(filename)}&title=${encodeURIComponent(t)}`,{method:'POST'});const r=await fetch('/api/logs');logData=await r.json();showHistoryLogs()}catch(e){}
}

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
async function loadTopics(){try{const r=await fetch('/api/catalog');const d=await r.json();const el=document.getElementById('topicList');el.innerHTML=d.topics.map(t=>`<span class="topic-item" data-q="${t.replace(/"/g,'&quot;')}">${t}</span>`).join('');el.querySelectorAll('.topic-item').forEach(s=>s.onclick=()=>ask(s.dataset.q))}catch(e){}}
async function loadHotspots(){try{const r=await fetch('/api/hotspots');const d=await r.json();const el=document.getElementById('hotspotList');el.innerHTML=d.hotspots.map(h=>`<div class="hotspot-item" onclick="showHotModal('${h.title.replace(/'/g,"\\'")}')"><span>${h.title}${h.tag?`<span class="hot-tag">${h.tag}</span>`:''}</span></div>`).join('');}catch(e){}}

// ── 热点弹窗 ────────────────────────────────
let currentHotTitle='',currentHotBrief='';
async function showHotModal(title){
    currentHotTitle=title;currentHotBrief='';
    document.getElementById('hotModalTitle').textContent=title;
    document.getElementById('hotModalBrief').textContent='加载中...';
    document.getElementById('hotModal').style.display='flex';
    try{const r=await fetch(`/api/hotspot/preview?title=${encodeURIComponent(title)}`,{method:'POST'});const d=await r.json();currentHotBrief=d.brief||title;document.getElementById('hotModalBrief').textContent=currentHotBrief}catch(e){document.getElementById('hotModalBrief').textContent=title}
}
function closeHotModal(){document.getElementById('hotModal').style.display='none'}
function chatAboutHot(){
    document.getElementById('hotModal').style.display='none';
    enterChat();
    document.getElementById('msg').value=currentHotTitle+'，您怎么看？';
    // 把缩略内容作为隐藏上下文注入
    window._hotContext=currentHotBrief;
    setTimeout(()=>send(),200);
}

// ── 启动 ────────────────────────────────────
fetch('/api/status').then(r=>r.json()).then(s=>{if(!s.rag)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ RAG未就绪');if(!s.llm)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ LLM未配置')});
loadTopics();loadHotspots();loadKbStats();

// ── 知识库统计 ──────────────────────────────
async function loadKbStats(){try{const r=await fetch('/api/kb-stats');const d=await r.json();document.getElementById('kbStat').textContent=`知识库总量：${d.word_count_wan} 万字`}catch(e){}}
