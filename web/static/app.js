let loading=false;
async function send(){
    const m=document.getElementById('msg').value.trim();
    if(!m||loading)return;
    const w=document.getElementById('welcome');if(w)w.remove();
    addMsg('user',m);document.getElementById('msg').value='';
    document.getElementById('status').textContent='● 思考中';
    loading=true;document.getElementById('sendBtn').disabled=true;
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
        if(!r.ok){const e=await r.json();throw new Error(e.detail||'请求失败')}
        const d=await r.json();
        let txt=d.answer||'';
        if(d.sources&&d.sources.length){
            txt+='<div class="sources">📚 引用来源：';
            d.sources.forEach((s,i)=>txt+=`<div class="source-item"><span class="source-tag">[${i+1}]</span> ${s.source}·${s.title}${s.date?' ('+s.date+')':''} <span style="opacity:.6">${(s.score*100).toFixed(0)}%</span></div>`);
            txt+='</div>';
        }
        addMsg('assistant',txt);
        document.getElementById('status').textContent='● 就绪';
    }catch(e){addMsg('assistant','❌ '+e.message);document.getElementById('status').textContent='● 就绪'}
    loading=false;document.getElementById('sendBtn').disabled=false;
}
function ask(t){document.getElementById('msg').value=t;send();}
function addMsg(role,html){
    const d=document.createElement('div');d.className='message '+role;d.innerHTML=html;
    document.getElementById('chat').appendChild(d);d.scrollIntoView();
}
fetch('/api/status').then(r=>r.json()).then(s=>{
    if(!s.rag)document.getElementById('status').textContent='● RAG未就绪';
    if(!s.llm)document.getElementById('status').textContent='● LLM未配置';
});
