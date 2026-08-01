// 主席模拟器 — 手机版
// ── SVG 图标库 ────────────────────────────────
const I={
home:'<svg class="ico" viewBox="0 0 24 24"><path d="M3 10L12 3l9 7v11h-6v-7H9v7H3z"/></svg>',
log:'<svg class="ico" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>',
scene:'<svg class="ico" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3" transform="rotate(45 12 12)"/><path d="M8 10l4-3 4 3M8 14l4 3 4-3"/></svg>',
read:'<svg class="ico" viewBox="0 0 24 24"><path d="M4 6h6l2-2h8v14H4z"/><path d="M4 6v14"/></svg>',
save:'<svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v7M9 11h6"/></svg>',
topic:'<svg class="ico" viewBox="0 0 24 24"><path d="M12 2l2.5 6.5L21 9l-5 4.5 1.5 6.5-5.5-3.5L6.5 20 8 13.5 3 9l6.5-.5z"/></svg>',
exit:'<svg class="ico" viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4M9 7l-5 5 5 5M4 12h12"/></svg>',
quiz:'<svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M10 8.5c0-.9.7-1.5 2-1.5s2 .6 2 1.5c0 1-1.5 1.5-2 2.5M12 16v.01"/></svg>',
summary:'<svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12h3l1-1 2 4 2-3h1"/></svg>',
cont:'<svg class="ico" viewBox="0 0 24 24"><path d="M7 5l12 7-12 7z"/></svg>',
del:'<svg class="ico" viewBox="0 0 24 24"><path d="M4 6h16v2H4zM7 6V4h10v2M10 10v7M14 10v7"/></svg>',
back:'<svg class="ico" viewBox="0 0 24 24"><path d="M18 5l-8 7 8 7"/></svg>',
expand:'<svg class="ico" viewBox="0 0 24 24"><path d="M8 14l4-4 4 4"/></svg>',
collapse:'<svg class="ico" viewBox="0 0 24 24"><path d="M8 10l4 4 4-4"/></svg>',
refresh:'<svg class="ico" viewBox="0 0 24 24"><path d="M4 4v5h5M20 20v-5h-5"/><path d="M5.5 14.5A7.5 7.5 0 0118.5 5.5M18.5 9.5A7.5 7.5 0 015.5 18.5"/></svg>',
random:'<svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M10 8.5c0-.9.7-1.5 2-1.5s2 .6 2 1.5c0 1-1.5 1.5-2 2.5M12 16v.01"/></svg>',
timer:'<svg class="ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3M10 2h4"/></svg>',
};
// 背景图映射
const SCENE_BG={shuwu:'bg-shuwu.png',keting:'bg-keting.png',xiaolu:'bg-xiaolu.png',shuxia:'bg-shuxia.png'};
const TRANS_BG={'菊香书屋门廊':'trans-doorway.png','走廊':'trans-corridor.png','丰泽园庭院入口':'trans-courtyard.png','傍晚庭院入口':'trans-dusk.png','庭院小径':'trans-path.png'};

// ── 标签切换 ────────────────────────────────
function switchTab(name){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.getElementById('page-'+name).classList.add('active');
    const tabEl=document.getElementById('tab-'+name);
    if(tabEl)tabEl.classList.add('active');
    if(name==='read')loadCatalogView();
    if(name!=='chat'&&currentPage==='chat')askSaveLog();
    currentPage=name;
}
let currentPage='home';
let hasNewMessages=false;
// 全局状态变量（曾缺失声明导致 send() 抛 ReferenceError）
let loading=false;
let currentScene='';
let sceneMode=false;
let idleTimer=null;
let currentFatigue='green';
let logData=null;
let idleEl=null;
let sceneSuggested=false;
let catalogData=null;
// 问题 3/5E：场景选择完成标志、NPC 话题防重、待发送消息（等场景选完再发）、场景选择弹窗状态
let scenePickDone=false;
let scenePickPending=false;
let sceneTopicShown=false;
let _pendingSend=null;

// ── 场景管理 ────────────────────────────────
async function setScene(sceneId,opts){
    opts=opts||{};
    if(loading||sceneId===currentScene)return;
    try{
        const r=await fetch('/api/scene/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scene:sceneId})});
        const d=await r.json();
        const oldScene=currentScene;
        currentScene=d.scene;
        updateSceneTags();
        updateCompactSceneBtns(); // 场景变化 → 刷新 compact 按钮文字（室内续茶递烟/室外喝水歇脚）
        // 过渡动画：transition 一定有值（后端已兜底）；scene 为空也播纯文字遮罩（问题 5B/5C）
        if(d.transition){
            await playTransition(d.transition,sceneId);
        }else{
            applySceneBg(sceneId);
        }
        resetIdleTimer();
        // 切换成功（场景确实变了）→ NPC 主动话题 + 新场景疲劳提示（问题 6/7）
        // opts.defer：由调用方（pickScene）在历史加载完成后触发，避免话题被顶出视口
        if(d.scene!==oldScene){
            sceneTopicShown=false;
            if(!opts.defer){
                showSceneTopic();
                showFatigueHint();
            }
        }
    }catch(e){console.error('Scene set failed:',e)}
}
function updateSceneTags(){
    document.querySelectorAll('.scene-tag').forEach(t=>t.classList.toggle('active',t.dataset.scene===currentScene));
}
function applySceneBg(sceneId){
    const page=document.getElementById('page-chat');
    if(!sceneMode){clearSceneBg();return;}
    const bg=SCENE_BG[sceneId];
    if(bg)page.style.backgroundImage=`url(/static/img/scenes/${bg})`;
}
function clearSceneBg(){
    document.getElementById('page-chat').style.backgroundImage='';
}
async function playTransition(transition,targetScene){
    const overlay=document.getElementById('sceneTransition');
    const textEl=document.getElementById('sceneTransitionText');
    const bgImg=TRANS_BG[transition.scene];
    if(bgImg)overlay.style.backgroundImage=`url(/static/img/scenes/${bgImg})`;
    overlay.style.display='flex';
    textEl.textContent='';
    // 逐字显示过渡文字
    const chars=[...transition.text];
    for(let i=0;i<chars.length;i++){
        textEl.textContent+=chars[i];
        await new Promise(r=>setTimeout(r,60));
    }
    await new Promise(r=>setTimeout(r,600));
    overlay.style.display='none';
    overlay.style.backgroundImage='';
    applySceneBg(targetScene);
}
async function askQuiz(){
    if(!sceneMode||loading)return;
    document.getElementById('msg').value='主席，您考考我吧';
    send();
}
function showQuiz(quiz){
    const modal=document.createElement('div');
    modal.className='quiz-modal';
    modal.innerHTML=`<div class="quiz-modal-content">
        <div class="quiz-modal-title">📝 主席考考你</div>
        <div class="quiz-modal-q">${quiz.q}</div>
        <div class="quiz-options">${quiz.opts.map((o,i)=>`<span class="quiz-opt" onclick="answerQuiz(${quiz.id},${i},this)">${o}</span>`).join('')}</div>
        <div class="quiz-close" onclick="this.parentElement.parentElement.remove()">✕ 跳过</div>
    </div>`;
    document.body.appendChild(modal);
}
function answerQuiz(id,ans,el){
    const modal=el.closest('.quiz-modal');
    if(modal)modal.remove();
    document.getElementById('msg').value=String(ans);
    send();
}
function updateQuizResult(result){
    // 在最后一条消息气泡中标记正确/错误
    const msgs=document.querySelectorAll('.message.assistant');
    const last=msgs[msgs.length-1];
    if(last&&last.querySelector('.quiz-options')){
        const opts=last.querySelectorAll('.quiz-opt');
        // 不做额外标记，结果已在下一条消息中显示
    }
}
// ── 入口面板 ────────────────────────────────
async function showEntryPanel(){
    // 先弹场景选择
    if(sceneMode){
        document.getElementById('sceneModal').style.display='flex';
        return;
    }
    try{const r=await fetch('/api/session/status');const s=await r.json();const r2=await fetch('/api/logs');const logs=await r2.json();
        const el=document.getElementById('entryOptions');
        let html='';
        if(s.active)html+=`<div class="entry-opt" onclick="closeEntryModal();enterChat()">💬 继续上次聊天<br><small>${s.rounds}轮对话，${(s.tokens/1000).toFixed(0)}K tokens</small></div>`;
        if(!s.active&&logs.sessions&&logs.sessions.length>0){
            html+='<div class="modal-btns" style="margin-top:8px"><select id="logSelect" style="padding:8px;border-radius:8px;border:1px solid var(--border);font-size:13px">';
            logs.sessions.forEach(l=>{html+=`<option value="${l.name}">${l.title||l.name} · ${l.rounds||'?'}条</option>`});
            html+='</select><button onclick="resumeFromEntryLog()" style="margin-top:6px">📜 继续这个话题</button></div>';
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
    scenePickDone=false; // 全新会话需重新选场景
    enterChat();
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
    // 问题 3：普通模式 + 聊天区为空 + 未选过场景 → 弹 4 场景+随机选择，选完再进聊天
    if(!sceneMode&&!scenePickDone&&document.getElementById('chat').children.length===0){
        try{
            const s=await fetch('/api/session/status');const sd=await s.json();
            if(!sd.active){
                scenePickPending=true;
                document.getElementById('sceneModal').style.display='flex';
                return true; // 已弹场景选择：调用方应挂起待发消息（ask/chatAboutHot）
            }
        }catch(e){}
    }
    scenePickDone=true;
    // 加载当前场景
    try{const sr=await fetch('/api/scene/get');const sd=await sr.json();currentScene=sd.scene;updateSceneTags();applySceneBg(currentScene)}catch(e){}
    // 检查是否有活跃会话
    try{const r=await fetch('/api/session/status');const d=await r.json();
        if(d.active){
            // 聊天区空则加载最近消息
            const chat=document.getElementById('chat');
            if(chat.children.length===0){
                try{
                    const lr=await fetch('/api/logs');
                    const ld=await lr.json();
                    if(ld.entries&&ld.entries.length){
                        const recent=ld.entries.slice(-20);
                        recent.forEach(e=>addMsg(e.role==='chairman'?'assistant':'user',escHtml(e.content).replace(/\n/g,'<br>')));
                    }
                }catch(e){}
            }
        }else{
            try{const g=await fetch('/api/greeting');const dd=await g.json();if(dd.greeting)addMsg('assistant',dd.greeting)}catch(e){}
        }
    }catch(e){}
    return false;
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
        // 出题
        if(d.quiz){
            setTimeout(()=>showQuiz(d.quiz),800);
        }
        // 答题结果
        if(d.quiz_result){
            updateQuizResult(d.quiz_result);
        }
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
        if(i>=len){
            if(data)updateStats(data);
            if(data){currentFatigue=data.fatigue||'green';updateFatigueUI();updateCompactBtns()}
            // 场景切换：等打字动画完成后再切（问题 5E，避免与 typewrite 并发）
            if(data&&data.scene_switch&&data.scene_switch.target&&data.scene_switch.target!==currentScene){
                setScene(data.scene_switch.target);
            }
            return
        }
        let chunk=1;
        if(text[i]==='['){const end=text.indexOf(']',i);if(end>i){chunk=end-i+1}else{chunk=1}}
        el.innerHTML+=text.substring(i,i+chunk).replace(/\n/g,'<br>');
        i+=chunk;el.scrollIntoView();
        const delay=chunk>1?speed*2:speed;
        setTimeout(tick,delay);
    }
    tick();
}

// ── 统计 ────────────────────────────────────
function updateStats(d){
    if(d.tokens)document.getElementById('stats').innerHTML=`📊 ${(d.tokens/1000).toFixed(1)}K | 累计 ${(d.cumulative_tokens/1000).toFixed(1)}K | ≈¥${(d.cumulative_tokens/1_000_000).toFixed(3)}`;
}
function updateFatigueUI(){
    const bar=document.getElementById('fatigueBar');if(!bar)return;
    bar.className='fatigue-bar '+(currentFatigue||'green');
    bar.textContent={green:'老人家看上去精神饱满',yellow:'老人家揉了揉太阳穴，有点累了',red:'老人家眼皮有点沉，该歇会儿了'}[currentFatigue]||'';
}
function updateCompactBtns(){
    const w=document.getElementById('compactBtns');if(!w)return;
    w.style.display=(currentFatigue==='yellow'||currentFatigue==='red')?'flex':'none';
    if(w.style.display==='flex')updateCompactSceneBtns();
}
// 问题 7：compact 按钮文字按场景变体（室内续茶递烟 / 室外喝口水歇歇脚）
function updateCompactSceneBtns(){
    const btns=document.querySelectorAll('#compactBtns button');
    if(!btns.length)return;
    const indoor=currentScene==='shuwu'||currentScene==='keting';
    btns[0].textContent=indoor?'🍵 续茶':'💧 喝口水';
    btns[1].textContent=indoor?'🚬 递烟':'🪨 歇歇脚';
}
async function doCompact(){
    try{await fetch('/api/compact',{method:'POST'});currentFatigue='green';updateFatigueUI();updateCompactBtns();addMsg('assistant','[老人家端起茶杯喝了一口，精神了不少] 好了，接着聊。')}catch(e){}
}

// ── 冷场 + 离开倒计时 ────────────────────────────────────
let idleCount=0, exitTimer=null, exitCountdown=null;
function resetIdleTimer(){
    if(idleTimer)clearTimeout(idleTimer);
    if(idleEl){idleEl.remove();idleEl=null;}
    if(exitTimer)clearTimeout(exitTimer);
    if(exitCountdown)clearInterval(exitCountdown);
    removeExitBar();
    idleCount=0;
    sceneSuggested=false;
    // 30s 冷场 → 8min 预警 → 10min 离开
    idleTimer=setTimeout(showIdleAction,30000);
    exitTimer=setTimeout(showExitWarning,8*60000);
}
async function showIdleAction(){
    idleCount++;
    try{const r=await fetch('/api/idle-actions');const d=await r.json();if(d.actions?.length){idleEl=document.createElement('div');idleEl.className='idle-action';idleEl.textContent=d.actions[Math.floor(Math.random()*d.actions.length)];document.getElementById('chat').appendChild(idleEl);idleEl.scrollIntoView()}}catch(e){}
    // 切换建议触发条件（问题 7）：空闲 8min（16 次×30s）或 疲劳黄/红 + 空闲 4min（8 次）
    const tired=currentFatigue==='yellow'||currentFatigue==='red';
    if((idleCount>=16||(tired&&idleCount>=8))&&!sceneSuggested){
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
    idleTimer=setTimeout(refreshIdleAction,30000);
}
function refreshIdleAction(){if(idleEl)idleEl.remove();showIdleAction();}

async function showExitWarning(){
    // 8分钟预警
    try{
        const r=await fetch('/api/idle-actions');const d=await r.json();
        if(d.actions?.length){
            const warnEl=document.createElement('div');
            warnEl.className='idle-action';
            warnEl.style.opacity='1';
            warnEl.textContent=d.actions[0]; // 疲劳动作
            document.getElementById('chat').appendChild(warnEl);
            warnEl.scrollIntoView();
        }
    }catch(e){}
    // 2分钟后正式离开
    exitTimer=setTimeout(showExitMessage,2*60000);
}
async function showExitMessage(){
    try{
        const r=await fetch('/api/scene/exit');const d=await r.json();
        addMsg('assistant',d.message);
        startExitCountdown();
    }catch(e){}
}
function startExitCountdown(){
    let sec=60;
    const bar=document.createElement('div');
    bar.className='exit-countdown';
    bar.id='exitCountdownBar';
    bar.innerHTML=`⏳ 主席已离开，<span id="exitSec">${sec}</span> 秒后自动保存并返回首页 <button onclick="cancelExit()">再聊会儿</button><button onclick="exitNow()" class="secondary">立即退出</button>`;
    document.querySelector('.app').appendChild(bar);
    exitCountdown=setInterval(()=>{
        sec--;
        const el=document.getElementById('exitSec');
        if(el)el.textContent=sec;
        if(sec<=0){clearInterval(exitCountdown);exitNow();}
    },1000);
}
function cancelExit(){
    clearInterval(exitCountdown);
    removeExitBar();
    resetIdleTimer();
}
function removeExitBar(){
    const bar=document.getElementById('exitCountdownBar');
    if(bar)bar.remove();
}
async function exitNow(){
    removeExitBar();
    await saveSession();
    switchTab('home');
}
// ── 日志底部弹出层 ──────────────────────
function toggleLogSheet(){
    const sheet=document.getElementById('logSheet');
    const backdrop=document.getElementById('logBackdrop');
    if(sheet.classList.contains('open')){
        sheet.classList.remove('open','full');
        backdrop.style.display='none';
        document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
        document.getElementById('tab-home').classList.add('active');
    }else{
        loadLogData();
        sheet.classList.add('open');
        backdrop.style.display='block';
        document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
        document.getElementById('tab-log').classList.add('active');
    }
}
function toggleLogFull(){
    const sheet=document.getElementById('logSheet');
    sheet.classList.toggle('full');
    const hint=sheet.querySelector('.log-expand-hint');
    hint.textContent=sheet.classList.contains('full')?'▼':'▲';
}
async function loadLogData(){
    try{const r=await fetch('/api/logs');logData=await r.json();showCurrentLogTab()}catch(e){}
}
function showCurrentLogTab(){
    const el=document.getElementById('logBody');if(!logData?.entries?.length){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    el.innerHTML=logData.entries.map(e=>`<div class="log-entry"><b>${e.role==='chairman'?'主席':'你'}：</b>${e.content}</div>`).join('');
    if(logData.active_rounds>0)el.innerHTML+='<div class="log-actions"><button onclick="summarizeCurrent()">'+I.summary+' 一键总结</button></div>';
    document.querySelectorAll('#logSheet .log-tab').forEach((t,i)=>t.classList.toggle('active',i===0));
}
let logEditState=null;
function showHistoryLogs(){
    const el=document.getElementById('logBody');if(!logData?.sessions){el.innerHTML='<div class="log-loading">暂无记录</div>';return}
    logEditState=null;
    el.innerHTML=logData.sessions.map(s=>{
        const time=s.time?s.time.substring(5,16):s.name.substring(8,19);
        const rounds=s.rounds??0;
        const preview=s.preview||'(空)';
        return `<div class="log-session-item2" onclick="viewLogContent('${s.name}')">
            <div class="log-session-preview">${escHtml(preview)}</div>
            <div class="log-session-meta">
                <span>${time} · ${rounds}条</span>
                <span class="log-acts">
                    <span onclick="event.stopPropagation();summarizeLog('${s.name}')" title="总结">${I.summary}</span>
                    <span onclick="event.stopPropagation();resumeFromLog('${s.name}')" title="继续聊">${I.cont}</span>
                    <span class="log-del" onclick="event.stopPropagation();deleteLogWithConfirm('${s.name}')">${I.del}</span>
                </span>
            </div>
        </div>`
    }).join('');
    document.querySelectorAll('#logSheet .log-tab').forEach((t,i)=>t.classList.toggle('active',i===1));
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
async function viewLogContent(filename){
    const el=document.getElementById('logBody');
    el.innerHTML='<div class="log-loading">加载中...</div>';
    try{
        const r=await fetch(`/api/logs/entries?filename=${encodeURIComponent(filename)}`);
        const d=await r.json();
        logEditState={filename, entries:d.entries||[], deleted:new Set()};
        renderLogEdit();
    }catch(e){el.innerHTML='<div class="log-loading">加载失败</div>'}
}
function renderLogEdit(){
    if(!logEditState)return;
    const el=document.getElementById('logBody');
    const {filename, entries, deleted}=logEditState;
    let timeStr='';
    for(let e of entries){if(e.time){timeStr=e.time.substring(5,16);break}}
    let html=`<div class="log-viewer-bar"><span onclick="goBackHistory()" style="cursor:pointer;color:var(--primary);font-size:15px">← 返回</span><span style="font-weight:600">${timeStr||filename}</span><span style="color:var(--text-light)">${entries.length}条</span></div>`;
    html+='<div class="log-viewer-content">';
    entries.forEach((e,i)=>{
        if(deleted.has(i)){
            html+=`<div class="log-entry deleted" onclick="toggleDeleteEntry(${i})">↩ 已删除 — <span style="color:var(--text-light)">${escHtml(e.content).substring(0,30)}...</span></div>`;
        }else{
            html+=`<div class="log-entry2"><b>${e.role==='chairman'?'主席':'你'}：</b>${escHtml(e.content)}</div>`;
        }
    });
    html+='</div>';
    html+=`<div class="log-viewer-actions">
        <button onclick="resumeFromLog('${filename}')">${I.cont} 继续聊</button>
        <button onclick="summarizeLog('${filename}')">${I.summary} 总结</button>
        <button onclick="deleteLogWithConfirm('${filename}')" style="color:#c62828">${I.del} 删除</button>
    </div>`;
    el.innerHTML=html;
}
function toggleDeleteEntry(idx){
    if(logEditState.deleted.has(idx)){logEditState.deleted.delete(idx)}else{logEditState.deleted.add(idx)}
    renderLogEdit();
}
function toggleAddForm(){
    const f=document.getElementById('logAddForm');
    f.style.display=f.style.display==='none'?'block':'none';
}
function doAddEntry(){
    const role=document.getElementById('addRole').value;
    const content=document.getElementById('addContent').value.trim();
    if(!content)return;
    logEditState.entries.push({role,content,time:new Date().toISOString()});
    document.getElementById('addContent').value='';
    renderLogEdit();
}
async function doSaveEdits(){
    if(!logEditState)return;
    const {filename, entries, deleted}=logEditState;
    const filtered=entries.filter((_,i)=>!deleted.has(i));
    try{
        const r=await fetch('/api/logs/entries/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename,entries:filtered})});
        if(!r.ok){const e=await r.json();throw new Error(e.detail)}
        logEditState=null;
        await loadLogData();
        showHistoryLogs();
    }catch(e){alert('保存失败: '+e.message)}
}
function goBackHistory(){
    if(logEditState&&logEditState.deleted.size>0){
        if(confirm('有未保存的修改，确定返回？')){logEditState=null;showHistoryLogs()}
    }else{logEditState=null;showHistoryLogs()}
}
async function resumeFromEntryLog(){
    const fname=document.getElementById('logSelect').value;
    closeEntryModal();
    await resumeFromLog(fname);
}
async function resumeFromLog(fname){
    try{
        console.log('resumeFromLog called with:', fname);
        // 先切到聊天
        switchTab('chat');
        console.log('tab switched, chat page active');
        addMsg('assistant','[老人家正在翻之前的聊天记录...]');
        const placeholder=document.getElementById('chat').lastChild;
        if(placeholder)placeholder.classList.add('loading');
        // 关日志弹层
        const sheet=document.getElementById('logSheet');
        if(sheet){sheet.classList.remove('open','full');}
        const bd=document.getElementById('logBackdrop');
        if(bd){bd.style.display='none';}
        // 填充历史5条
        const lr=await fetch('/api/logs/entries?filename='+encodeURIComponent(fname));
        const ld=await lr.json();
        console.log('entries fetched:', ld.entries?.length);
        // 清除加载消息
        const chat=document.getElementById('chat');
        if(chat.lastChild&&chat.lastChild.classList.contains('loading'))chat.lastChild.remove();
        if(ld.entries&&ld.entries.length){
            const last5=ld.entries.slice(-5);
            last5.forEach(e=>addMsg(e.role==='chairman'?'assistant':'user',escHtml(e.content).replace(/\n/g,'<br>')));
            console.log('added', last5.length, 'history messages');
        }
        // 主席承接
        try{
            const r=await fetch('/api/session/summarize?filename='+encodeURIComponent(fname),{method:'POST'});
            const d=await r.json();
            // 截断中文时避免切断字符（substring 可能在 UTF-16 代理对/汉字边界截出残字）
            let head=d.summary||'';
            if(head.length>50)head=head.substring(0,50).replace(/[，。、；：！？…\s]+$/,'')+'…';
            addMsg('assistant',`[老人家抽了口烟，像是想起了什么] 上回咱们说到${head}。后来你咋想的？`);
        }catch(e){addMsg('assistant','[老人家抽了口烟] 上次的事，接着说。'); console.log('summary failed:', e.message)}
        hasNewMessages=true;
    }catch(e){
        console.error('resumeFromLog error:', e.message, e.stack);
        switchTab('chat');
    }
}
async function summarizeCurrent(){
    if(!logData?.current)return;
    const el=document.getElementById('logBody');el.innerHTML+='<div class="log-loading">总结中...</div>';
    try{const r=await fetch(`/api/session/summarize?filename=${encodeURIComponent(logData.current)}`,{method:'POST'});const d=await r.json();
        el.innerHTML+='<div class="log-summary"><b>'+I.summary+' AI 总结：</b><br>'+d.summary+'</div>'}catch(e){}
}
async function summarizeLog(filename){
    const el=document.getElementById('logBody');el.innerHTML+='<div class="log-loading">总结中...</div>';
    try{const r=await fetch(`/api/session/summarize?filename=${encodeURIComponent(filename)}`,{method:'POST'});const d=await r.json();
        el.innerHTML+='<div class="log-summary"><b>'+I.summary+' AI 总结：</b><br>'+d.summary+'</div>'}catch(e){}
}
async function deleteLogWithConfirm(filename){
    if(!confirm('确定删除这条日志？此操作不可恢复。'))return;
    try{await fetch(`/api/logs/${filename}`,{method:'DELETE'});const r=await fetch('/api/logs');logData=await r.json();showHistoryLogs()}catch(e){}
}
function ask(t){
    document.getElementById('msg').value=t;
    // 问题 3：等 enterChat 确定是否弹场景选择（异步），弹了则挂起待发
    enterChat().then(popped=>{
        if(popped){
            _pendingSend=t;
        }else{
            setTimeout(()=>send(),200);
        }
    });
}
// ── 聊天操作栏 ──────────────────────────
let savedToast=null;
async function saveSession(){
    try{
        await fetch('/api/session/save',{method:'POST'});
        if(savedToast)clearTimeout(savedToast);
        const toast=document.createElement('div');
        toast.className='save-toast';toast.textContent='保存成功';
        document.body.appendChild(toast);
        savedToast=setTimeout(()=>toast.remove(),2000);
    }catch(e){alert('保存失败')}
}
function findTopic(){
    switchTab('home');
    document.getElementById('hotspotPanel').scrollIntoView({behavior:'smooth'});
}
// ── 场景模式 ──────────────────────────
function toggleSceneMode(){
    sceneMode=!sceneMode;
    updateSceneUI();
    try{localStorage.setItem('mrmao_scene',sceneMode?'on':'off')}catch(e){}
}
function updateSceneUI(){
    const overlay=document.querySelector('.chat-overlay');
    const page=document.getElementById('page-chat');
    const tab=document.getElementById('tab-scene');
    const toggle=document.getElementById('sceneToggle');
    if(sceneMode){
        if(overlay)overlay.classList.add('on');
        // 仅追加 scene-bg 类，不得改写 className 破坏 active 状态
        if(page){
            page.classList.remove('scene-bg','shuwu','keting','xiaolu','shuxia');
            if(currentScene)page.classList.add('scene-bg',currentScene)
        }
        if(tab)tab.classList.add('active');
        if(toggle){toggle.innerHTML=I.scene;toggle.title='关闭场景模式';toggle.style.opacity='1'}
    }else{
        if(overlay)overlay.classList.remove('on');
        if(page){
            page.classList.remove('scene-bg','shuwu','keting','xiaolu','shuxia');
            page.style.backgroundImage=''; // 问题 2：普通模式无背景图（清 inline）
        }
        if(tab)tab.classList.remove('active');
        if(toggle){toggle.innerHTML=I.scene;toggle.title='开启场景模式';toggle.style.opacity='.3'}
    }
}
function toggleSceneModeHome(){
    sceneMode=!sceneMode;
    updateSceneUI();
    try{localStorage.setItem('mrmao_scene',sceneMode?'on':'off')}catch(e){}
}
function applySceneMode(){
    try{const v=localStorage.getItem('mrmao_scene');if(v==='on'){sceneMode=true}else{sceneMode=false}}catch(e){}
    updateSceneUI();
}
function initIcons(){
    // 底部栏
    const set=(id,svg)=>{const el=document.getElementById(id);if(el)el.innerHTML=svg};
    set('homeIcon',I.home);set('logIcon',I.log);set('sceneIcon',I.scene);set('readIcon',I.read);
    // 聊天操作栏
    set('btnSave',I.save+' 保存');set('btnTopic',I.topic+' 找话题');
    set('btnQuiz',I.quiz+' 考考');set('btnExit',I.exit+' 退出');
    // 场景切换
    set('sceneToggle',I.scene);
    // 热搜刷新
    const ref=document.querySelector('.hotspot-refresh');
    if(ref)ref.innerHTML=I.refresh;
}
async function pickScene(id,label){
    document.getElementById('sceneModal').style.display='none';
    const sw=document.getElementById('sceneSwitchModal');if(sw)sw.style.display='none';
    const labelMap={shuwu:'📚 菊香书屋',keting:'🛋️ 丰泽园客厅',xiaolu:'🌳 小路上',shuxia:'🌿 树下'};
    const labelEl=document.getElementById('sceneLabel');
    if(labelEl)labelEl.textContent=labelMap[id]||label||id;
    scenePickDone=true;
    scenePickPending=false;
    // defer：历史消息加载完成后（enterChat 之后）再触发 NPC 话题，避免被顶出视口（问题 6 实测发现）
    await setScene(id,{defer:true});
    await enterChat();
    showSceneTopic();
    showFatigueHint();
    // 问题 3：首页话题/热点等场景选完后发送
    if(_pendingSend){const t=_pendingSend;_pendingSend=null;document.getElementById('msg').value=t;send();}
}
function pickSceneRandom(){
    const scenes=[['shuwu','📚 菊香书屋'],['keting','🛋️ 丰泽园客厅'],['xiaolu','🌳 小路上'],['shuxia','🌿 树下']];
    const [id,label]=scenes[Math.floor(Math.random()*scenes.length)];
    pickScene(id,label);
}

// ── 主动切换面板（问题 1）──────────────────
function toast(msg){
    if(savedToast)clearTimeout(savedToast);
    const el=document.createElement('div');
    el.className='save-toast';el.textContent=msg;
    document.body.appendChild(el);
    savedToast=setTimeout(()=>el.remove(),2200);
}
async function showSceneSwitchPanel(){
    if(!sceneMode){
        toast('当前为普通模式，不可切换场景，请先打开场景模式');
        return;
    }
    try{
        const r=await fetch('/api/scene/switch-options');
        const d=await r.json();
        document.getElementById('sceneSwitchPrompt').textContent=d.prompt;
        document.getElementById('sceneSwitchList').innerHTML=d.targets.map(t=>
            `<div class="scene-pick" onclick="pickScene('${t.id}','${t.emoji} ${t.name}')">${t.emoji} ${t.name}</div>`
        ).join('');
        document.getElementById('sceneSwitchModal').style.display='flex';
    }catch(e){toast('切换面板加载失败')}
}
function closeSceneSwitchModal(){const m=document.getElementById('sceneSwitchModal');if(m)m.style.display='none'}

// ── 切换后 NPC 主动话题（问题 6）────────────
async function showSceneTopic(){
    if(sceneTopicShown)return;
    sceneTopicShown=true;
    try{
        const r=await fetch('/api/scene/topic',{method:'POST'});
        const d=await r.json();
        if(d.topic)typewrite(d.topic,null);
        if(d.quiz)setTimeout(()=>showQuiz(d.quiz),800);
    }catch(e){console.error('Scene topic failed:',e)}
}

// ── 切换后新场景疲劳提示（问题 7）────────────
async function showFatigueHint(){
    try{
        const r=await fetch('/api/scene/fatigue-hint',{method:'POST'});
        const d=await r.json();
        if(d.hint&&d.level!=='green'){
            const el=document.createElement('div');
            el.className='idle-action';
            el.style.opacity='1';
            el.textContent=d.hint;
            document.getElementById('chat').appendChild(el);
            el.scrollIntoView();
        }
    }catch(e){}
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
async function loadHotspots(){try{const r=await fetch('/api/hotspots');const d=await r.json();const el=document.getElementById('hotspotList');el.innerHTML=d.items.map(h=>`<div class="hotspot-item" onclick="showHotModal('${h.title.replace(/'/g,"\\'")}')"><span>${h.title}${h.tag?`<span class="hot-tag">${h.tag}</span>`:''}</span></div>`).join('');document.getElementById('hotspotSource').textContent=d.source||'百度热搜'}catch(e){}}
async function refreshHotspots(){
    const el=document.getElementById('hotspotList');el.innerHTML='<div class="log-loading">刷新中...</div>';
    try{const r=await fetch('/api/hotspots/refresh',{method:'POST'});const d=await r.json();
        el.innerHTML=d.items.map(h=>`<div class="hotspot-item" onclick="showHotModal('${h.title.replace(/'/g,"\\'")}')"><span>${h.title}${h.tag?`<span class="hot-tag">${h.tag}</span>`:''}</span></div>`).join('');
        document.getElementById('hotspotSource').textContent=d.source||'百度热搜'}catch(e){el.innerHTML='<div class="log-loading">刷新失败</div>'}
}

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
    enterChat().then(popped=>{
        document.getElementById('msg').value=currentHotTitle+'，您怎么看？';
        // 把缩略内容作为隐藏上下文注入
        window._hotContext=currentHotBrief;
        // 问题 3：弹了场景选择则等选完再发送
        if(popped){
            _pendingSend=currentHotTitle+'，您怎么看？';
        }else{
            setTimeout(()=>send(),200);
        }
    });
}

// ── 启动 ────────────────────────────────────
fetch('/api/status').then(r=>r.json()).then(s=>{if(!s.rag)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ RAG未就绪');if(!s.llm)document.getElementById('stats')&&(document.getElementById('stats').innerHTML='⚠ LLM未配置')});
loadTopics();loadHotspots();loadKbStats();applySceneMode();initIcons();

// ── 知识库统计 ──────────────────────────────
async function loadKbStats(){try{const r=await fetch('/api/kb-stats');const d=await r.json();document.getElementById('kbStat').textContent=`知识库总量：${d.word_count_wan} 万字`}catch(e){}}
