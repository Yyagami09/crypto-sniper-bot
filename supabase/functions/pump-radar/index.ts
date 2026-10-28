import {n,validAddress,event} from './core.ts';
import {freeRules,fromDex,applyFree,updateOutcomes,publicFeed} from './free-core.ts';
import {deliverPersonal} from './notifications.ts';
import {enrichRisks} from './risk.ts';
import {collectNetworks} from './networks.ts';
import {observeEarly,finishEarly,publicEarly,earlyRules} from './early.ts';
const now=()=>Date.now()/1000;
const pause=(ms:number)=>new Promise(r=>setTimeout(r,ms));
const respond=(data:any,status=200)=>Response.json(data,{status});
const base=Deno.env.get('SUPABASE_URL')!,service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
async function db(path:string,body?:any,method?:string){
 const r=await fetch(`${base}/rest/v1/${path}`,{method:method||(body===undefined?'GET':'POST'),
 headers:{apikey:service,Authorization:`Bearer ${service}`,'Content-Type':'application/json',Prefer:'return=representation'},
 body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(8000)});
 if(!r.ok)throw new Error('database_error');return r.status===204?null:await r.json();
}
async function sameSecret(a:string,b:string){
 const hash=async(s:string)=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
 const x=await hash(a),y=await hash(b);let delta=0;for(let i=0;i<x.length;i++)delta|=x[i]^y[i];return delta===0;
}
Deno.serve(async(req)=>{
 if(req.method!=='POST')return respond({error:'method_not_allowed'},405);
 const supplied=req.headers.get('x-pump-token');if(!supplied)return respond({error:'unauthorized'},401);
 let cfg:any;try{cfg=await db('rpc/pump_worker_config',{});}catch{return respond({error:'configuration_unavailable'},503);}
 if(!cfg?.cron_token||!await sameSecret(supplied,cfg.cron_token))return respond({error:'unauthorized'},401);
 const owner=crypto.randomUUID(),started=now();let state:any,acquired=false;
 try{
  acquired=await db('rpc/pump_acquire',{p_owner:owner});if(!acquired)return respond({status:'busy'});
  state=(await db('pump_radar_state?id=eq.main&select=payload'))[0].payload;
  const commit=async()=>{if(!await db('rpc/pump_commit',{p_owner:owner,p_payload:state}))throw new Error('lease_lost');};
  const publish=async()=>await db('rpc/pump_publish_market_feed',{p_payload:publicFeed(state)});
  if(state.profile!=='free-market-v1'){
   // Keep any former private history separate; never publish it as the public feed.
   if(Object.keys(state.tokens||{}).length||state.alerts?.length)state.previous_private={tokens:state.tokens,alerts:state.alerts};
   state.tokens={};state.alerts=[];state.backoff_until=0;state.profile='free-market-v1';
  }
  if(state.backoff_until>now())return respond({status:'cooldown'});
  if(state.risk_policy!=='risk-v1'){
   for(const t of Object.values<any>(state.tokens))t.qualified_at=0;
   state.risk_policy='risk-v1';
  }
  const trialEnabled=(await db('sniper_profiles?active=eq.true&radar_mode=eq.early-v1&select=id&limit=1')).length>0;
  state.early_enabled=trialEnabled;state.early_tokens||={};
  state.run={started_at:started,status:'running',demo:false,rules:freeRules,checked:0,errors:0,
   source_errors:[],engine:'supabase-free-market',telegram_configured:!!(cfg.telegram_token&&cfg.telegram_chat)};
  await commit();
  let profiles:any[]=[];
  const get=async(url:string,timeout=10000)=>{
   const r=await fetch(url,{headers:{Accept:'application/json'},signal:AbortSignal.timeout(timeout)});
   if(!r.ok)throw new Error('public_source_unavailable');return await r.json();
  };
  try{
   const discovered:any[]=[];
   const discovery=await Promise.allSettled([
    get('https://api.geckoterminal.com/api/v2/networks/solana/new_pools'),
    get('https://api.dexscreener.com/token-profiles/latest/v1')]);
   try{
    if(discovery[0].status!=='fulfilled')throw new Error('discovery');
    const j=discovery[0].value;
    if(!Array.isArray(j.data))throw new Error('schema');
    for(const row of j.data){
     const id=row.relationships?.base_token?.data?.id;
     if(typeof id==='string'&&id.startsWith('solana_'))discovered.push({address:id.slice(7),source:'GeckoTerminal new pools',liquidity:n(row.attributes?.reserve_in_usd)});
    }
   }catch{state.run.source_errors.push('GeckoTerminal: descoberta indisponível');}
   try{
    if(discovery[1].status!=='fulfilled')throw new Error('discovery');
    const j=discovery[1].value;
    if(!Array.isArray(j))throw new Error('schema');
    profiles=j;
    for(const x of j)if(x.chainId==='solana')discovered.push({address:x.tokenAddress,source:'DEX Screener — perfil recente (pode ser promocional)',liquidity:null});
   }catch{state.run.source_errors.push('DEX Screener: perfis indisponíveis');}
   for(const [a,t] of Object.entries<any>(state.tokens))if(now()-t.first_seen>86400&&t.status!=='candidate')delete state.tokens[a];
   for(const item of discovered){
    const a=item.address;if(!validAddress(a)||state.tokens[a]||item.liquidity!==null&&item.liquidity<2000)continue;
    if(Object.keys(state.tokens).length>=freeRules.max_tracked){
     const old=Object.values<any>(state.tokens).filter(t=>!['candidate','confirming'].includes(t.status)&&t.last_checked>0&&now()-t.first_seen>1800).sort((a,b)=>a.first_seen-b.first_seen)[0];
     if(!old)continue;delete state.tokens[old.address];
    }
    state.tokens[a]={address:a,first_seen:now(),last_checked:0,status:'queued',reasons:[],history:[],discovery_source:item.source};
   }
   if(trialEnabled){
    for(const a of Object.keys(state.early_tokens))if(state.tokens[a])delete state.early_tokens[a];
    for(const item of discovered){
     const a=item.address;if(!validAddress(a)||state.tokens[a]||state.early_tokens[a]||item.liquidity!==null&&item.liquidity<2000)continue;
     if(Object.keys(state.early_tokens).length>=earlyRules.extra_tracked){
      const old=Object.values<any>(state.early_tokens).filter(t=>now()-t.first_seen>600).sort((a,b)=>a.first_seen-b.first_seen)[0];
      if(!old)continue;delete state.early_tokens[old.address];
     }
     state.early_tokens[a]={address:a,first_seen:now(),last_checked:0,status:'queued',reasons:[],history:[],discovery_source:item.source};
    }
   }
   const allTokens={...state.tokens,...(trialEnabled?state.early_tokens:{})};
   const addresses=Object.keys(allTokens).filter(validAddress).slice(0,freeRules.max_tracked+(trialEnabled?earlyRules.extra_tracked:0));
   if(!addresses.length&&state.run.source_errors.length)throw new Error('discovery_unavailable');
   if(addresses.length){
    const batches=[];for(let i=0;i<addresses.length;i+=30)batches.push(addresses.slice(i,i+30));
    const pairResponses=await Promise.all(batches.map(batch=>get('https://api.dexscreener.com/tokens/v1/solana/'+batch.join(','))));
    if(pairResponses.some(p=>!Array.isArray(p)))throw new Error('schema_changed');
    const pairs=pairResponses.flat();
    if(!Array.isArray(pairs))throw new Error('schema_changed');
    const byToken:any={};
    for(const p of pairs){const a=p.baseToken?.address;if(addresses.includes(a)&&p.chainId==='solana'&&(!byToken[a]||(n(p.liquidity?.usd)||0)>(n(byToken[a].liquidity?.usd)||0)))byToken[a]=p;}
    let accounts:any[]=[];
    try{
     const r=await fetch('https://api.mainnet.solana.com',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jsonrpc:'2.0',id:1,method:'getMultipleAccounts',params:[addresses,{encoding:'jsonParsed',commitment:'confirmed'}]}),signal:AbortSignal.timeout(10000)});
     const j=await r.json();if(!r.ok||j.error||!Array.isArray(j.result?.value))throw new Error('rpc');accounts=j.result.value;
    }catch{state.run.source_errors.push('Solana RPC: permissões não puderam ser verificadas');}
    const snapshots:any[]=[];
    for(let ix=0;ix<addresses.length;ix++){
     const a=addresses[ix],t=allTokens[a];
     try{
      const snap=fromDex(a,byToken[a],accounts[ix],now());snap.sources.discovery=t.discovery_source;
      snapshots.push(snap);
     }catch{
      if(t.status==='candidate')event(state,t,'data_gap',['Dados de mercado indisponíveis'],now());
      t.status='incomplete';t.qualified_at=0;t.last_checked=now();t.reasons=['Pool não encontrada ou dados incompatíveis'];if(t.early)t.early.status='pending';state.run.errors++;
     }
     state.run.checked++;
    }
    const rpc=async(batch:string[])=>{
     const r=await fetch('https://api.mainnet.solana.com',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jsonrpc:'2.0',id:2,method:'getMultipleAccounts',params:[batch,{encoding:'jsonParsed',commitment:'confirmed'}]}),signal:AbortSignal.timeout(6000)});
     const j=await r.json();if(!r.ok||j.error||!Array.isArray(j.result?.value))throw new Error('risk_rpc_unavailable');return j.result.value;
    };
    await enrichRisks(snapshots,state,(url:string)=>get(url,4000),rpc,now,started);
    const trialRows:any[]=[],liveTrials=new Set<string>();
    for(const snap of snapshots){
     const t=allTokens[snap.address];
     if(state.tokens[snap.address])applyFree(state,t,snap,now());
     else{t.snapshot=snap;t.last_checked=now();t.status='watch';}
     if(trialEnabled){const record=observeEarly(state,t,snap,now());if(record){liveTrials.add(snap.address+':'+snap.pair_address);trialRows.push(publicEarly(t));}}
    }
    if(trialEnabled){
     trialRows.push(...finishEarly(state,liveTrials,now()).map(r=>publicEarly({early:r})));
     await commit(); // Persist stable experiment IDs before the history upsert.
     try{await db('rpc/dex_save_early_trials',{p_rows:trialRows});}
     catch{state.run.source_errors.push('Registro do experimento indisponível neste ciclo; comparação pode ter lacunas');}
    }
    const pendingRisk=snapshots.filter(s=>s.risk.status==='pending').length;
    if(pendingRisk)state.run.source_errors.push(`${pendingRisk} tokens aguardam relatório/consulta de risco. Até 4 relatórios por ciclo, com orçamento de 10 a cada 5 min; ausências não liberam sinais.`);
   }
   updateOutcomes(state,now());
   state.run.status=state.run.errors||state.run.source_errors.length?'partial':'ok';state.backoff_until=0;
  }catch{
   state.run.status='error';state.run.error='public_sources_unavailable';state.backoff_until=now()+120;
  }
  state.run.completed_at=now();state.alerts=state.alerts.slice(-400);await commit();await publish();
  let attempts=0;
  for(const a of [...state.alerts].sort((a,b)=>b.created_at-a.created_at)){
   if(a.delivery!=='pending'||a.kind.startsWith('early_'))continue;
   if(a.kind==='candidate'&&(a.snapshot.risk?.status!=='reviewed'||state.tokens[a.address]?.status!=='candidate'||state.tokens[a.address]?.snapshot?.risk?.status!=='reviewed')){a.delivery='expired';continue;}
   if(now()-a.created_at>1800){a.delivery='expired';continue;}
   if(!cfg.telegram_token||!cfg.telegram_chat||a.next_attempt>now()||attempts>=3||now()-started>100)continue;
   if(a.attempts>=3){a.delivery='failed';continue;}
   attempts++;a.attempts=(a.attempts||0)+1;
   const label=a.kind==='candidate'?'SINAL DE MERCADO — RISCO PARCIAL':a.kind;
   const text=`Crypto Sniper gratuito | ${label}\n${a.snapshot.symbol||'?'} | Solana\nCA: ${a.address}\n${a.reasons.join('\n')}\nConsulta: ${new Date(a.created_at*1000).toISOString()}\nTriagem parcial. Venda não simulada; insiders e bundles não auditados. Sem previsão de lucro.\n${a.snapshot.pair_url}`;
   try{
    const r=await fetch(`https://api.telegram.org/bot${cfg.telegram_token}/sendMessage`,{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({chat_id:cfg.telegram_chat,text,link_preview_options:{is_disabled:true}}),signal:AbortSignal.timeout(5000)});
    const result=await r.json();if(result.ok)a.delivery='sent';else a.next_attempt=now()+Math.max(60,Math.min(86400,Number(result.parameters?.retry_after)||60));
   }catch{a.next_attempt=now()+60;}
   await commit();await pause(1100);
  }
  try{await deliverPersonal(state,db,started);}catch{/* Delivery retries next cycle; collection remains available. */}
  await commit();
  try{await collectNetworks(state,get,profiles,now,started,freeRules);await commit();await publish();}catch{/* Secondary observations cannot delay or invalidate the published Solana signals. */}
  return respond({status:state.run.status,checked:state.run.checked,public_feed:true});
 }catch{return respond({error:'radar_unavailable'},503);}
 finally{if(acquired)try{await db('rpc/pump_release',{p_owner:owner});}catch{/* expires */}}
});
