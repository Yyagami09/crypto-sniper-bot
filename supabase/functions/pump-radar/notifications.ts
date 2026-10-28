export function notificationText(a:any){
 const labels:any={candidate:'SINAL DE MERCADO — RISCO PARCIAL',conditions_lost:'CONDIÇÕES PERDIDAS',data_gap:'DADOS INDISPONÍVEIS'};
 return `Crypto Sniper | ${labels[a.kind]||'AVISO'}\n${String(a.snapshot?.symbol||'?').slice(0,30)} | Solana\nCA: ${a.address}\n${(a.reasons||[]).join('\n').slice(0,1600)}\nConsulta: ${new Date(a.created_at*1000).toISOString()}\nTriagem parcial. Não é recomendação de compra nem previsão de lucro.\n${a.snapshot?.pair_url||''}`;
}

export async function deliverPersonal(state:any,db:any,started:number,send:any=fetch,clock=()=>Date.now()/1000){
 const connections=await db('rpc/sniper_telegram_credentials',{});
 const alerts=(state.alerts||[]).filter((a:any)=>a.snapshot?.profile==='free-market-v1'&&
  ['candidate','conditions_lost','data_gap'].includes(a.kind)&&clock()-a.created_at<=1800);
 let attempted=0;
 for(const c of connections){
  if(!c.enabled||!c.connected_at||!c.chat_id)continue;
  const since=Date.parse(c.connected_at)/1000;
  const eligible=alerts.filter((a:any)=>a.created_at>=since);
  if(!eligible.length)continue;
  const prior=await db(`sniper_deliveries?user_id=eq.${c.user_id}&select=*&order=created_at.desc&limit=400`);
  for(const a of eligible){
   if(attempted>=10||clock()-started>95)return;
   const old=prior.find((d:any)=>d.alert_id===a.id);
   if(old&&(old.status!=='pending'||old.attempts>=3||Date.parse(old.next_attempt)/1000>clock()))continue;
   const attempts=(old?.attempts||0)+1;
   const record={user_id:c.user_id,alert_id:a.id,status:'pending',attempts,next_attempt:new Date((clock()+300)*1000).toISOString()};
   const path=`sniper_deliveries?user_id=eq.${c.user_id}&alert_id=eq.${a.id}`;
   // Persist the attempt first. At-least-once delivery: a timeout after acceptance
   // by Telegram can result in a duplicate on retry, rather than silent loss.
   if(old)await db(path,record,'PATCH');else await db('sniper_deliveries',record);
   attempted++;
   let status='pending';
   try{
    const r=await send(`https://api.telegram.org/bot${c.token}/sendMessage`,{
     method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({chat_id:c.chat_id,text:notificationText(a),link_preview_options:{is_disabled:true}}),
     signal:AbortSignal.timeout(5000)});
    const j=await r.json();
    if(j.ok)status='sent';
    else if(r.status===403||r.status===401){status='failed';await db('sniper_telegram?user_id=eq.'+c.user_id,{enabled:false},'PATCH');}
   }catch{/* No token, Telegram response or exception URL enters logs/feed. */}
   if(status==='pending'&&attempts>=3)status='failed';
   await db(path,{status,...(status==='sent'?{sent_at:new Date(clock()*1000).toISOString()}:{})},'PATCH');
  }
 }
}
