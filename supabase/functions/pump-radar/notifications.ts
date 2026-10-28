export function notificationText(a:any){
 const labels:any={early_watch:'👀 VALE ABRIR O GRÁFICO — EXPERIMENTAL',early_changed:'EXPERIMENTAL — TRIAGEM ALTERADA',candidate:'SINAL DE MERCADO — RISCO PARCIAL',conditions_lost:'CONDIÇÕES PERDIDAS',data_gap:'DADOS INDISPONÍVEIS'};
 const detail=a.kind==='early_watch'?'Possível oportunidade para análise manual. Verificações disponíveis atendidas em duas consultas. Abra o gráfico para avaliar o momento.\n':'';
 return `Crypto Sniper | ${labels[a.kind]||'AVISO'}\n${String(a.snapshot?.symbol||'?').slice(0,30)} | Solana\n${detail}CA: ${a.address}\n${(a.reasons||[]).join('\n').slice(0,1600)}\nConsulta: ${new Date(a.created_at*1000).toISOString()}\nTriagem parcial. Não é recomendação de compra nem previsão de lucro.\n${a.snapshot?.pair_url||''}`;
}

export async function deliverPersonal(state:any,db:any,started:number,send:any=fetch,clock=()=>Date.now()/1000){
 const connections=await db('rpc/sniper_telegram_credentials',{});
 const profiles=await db('sniper_profiles?active=eq.true&select=id,radar_mode,radar_mode_since');
 let attempted=0;
 for(const c of connections){
  if(!c.enabled||!c.connected_at||!c.chat_id)continue;
  const since=Date.parse(c.connected_at)/1000;
  const profile=profiles.find((p:any)=>p.id===c.user_id);
  const eligible=eligibleAlerts(state,profile?.radar_mode||'classic',clock()).filter((a:any)=>a.created_at>=Math.max(since,Date.parse(profile?.radar_mode_since||'1970-01-01')/1000));
  if(!eligible.length)continue;
  const prior=await db(`sniper_deliveries?user_id=eq.${c.user_id}&select=*&order=created_at.desc&limit=400`);
  for(const a of eligible){
   if(attempted>=10||clock()-started>95)return;
   const old=prior.find((d:any)=>d.alert_id===a.id);
   if(old&&(old.status!=='pending'||old.attempts>=3||Date.parse(old.next_attempt)/1000>clock()))continue;
   const attempts=(old?.attempts||0)+1;
   const record={user_id:c.user_id,alert_id:a.id,status:'pending',attempts,next_attempt:new Date((clock()+60)*1000).toISOString()};
   const path=`sniper_deliveries?user_id=eq.${c.user_id}&alert_id=eq.${a.id}`;
   // Persist the attempt first. At-least-once delivery: a timeout after acceptance
   // by Telegram can result in a duplicate on retry, rather than silent loss.
   if(old)await db(path,record,'PATCH');else await db('sniper_deliveries',record);
   attempted++;
   let status='pending',retryAfter=60;
   try{
    const r=await send(`https://api.telegram.org/bot${c.token}/sendMessage`,{
     method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({chat_id:c.chat_id,text:notificationText(a),link_preview_options:{is_disabled:true}}),
     signal:AbortSignal.timeout(5000)});
    const j=await r.json();
    if(r.status===429)retryAfter=Math.max(60,Math.min(86400,Number(j.parameters?.retry_after)||60));
    if(j.ok)status='sent';
    else if(r.status===403||r.status===401){status='failed';await db('sniper_telegram?user_id=eq.'+c.user_id,{enabled:false},'PATCH');}
   }catch{/* No token, Telegram response or exception URL enters logs/feed. */}
   if(status==='pending'&&attempts>=3)status='failed';
   await db(path,{status,...(status==='sent'?{sent_at:new Date(clock()*1000).toISOString()}:{next_attempt:new Date((clock()+retryAfter)*1000).toISOString()})},'PATCH');
  }
 }
}

export function eligibleAlerts(state:any,mode:string,now:number){
 return (state.alerts||[]).filter((a:any)=>{
  if(a.snapshot?.profile!=='free-market-v1'||now-a.created_at>1800||now<a.created_at)return false;
  const t=state.tokens?.[a.address]||state.early_tokens?.[a.address];
  if(mode==='early-v1'){
   if(!['early_watch','early_changed'].includes(a.kind)||!t?.early||t.early.id!==a.snapshot.early?.id)return false;
   if(a.kind==='early_changed')return t.early.status!=='reviewed';
   return t.early.status==='reviewed'&&t.snapshot?.risk?.status==='reviewed'&&now-t.early.last_at<=120&&
    t.snapshot.pair_address===a.snapshot.pair_address;
  }
  if(!['candidate','conditions_lost','data_gap'].includes(a.kind))return false;
  return a.kind!=='candidate'||a.snapshot.risk?.version==='risk-v1'&&a.snapshot.risk.status==='reviewed'&&
   state.tokens?.[a.address]?.status==='candidate'&&t.snapshot?.risk?.status==='reviewed'&&
   t.snapshot.pair_address===a.snapshot.pair_address;
 }).sort((a:any,b:any)=>b.created_at-a.created_at);
}
