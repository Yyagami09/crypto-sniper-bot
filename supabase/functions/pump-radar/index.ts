import {n,validAddress,event} from './core.ts';
import {freeRules,fromDex,applyFree,updateOutcomes,publicFeed} from './free-core.ts';
const now=()=>Date.now()/1000;
const pause=(ms:number)=>new Promise(r=>setTimeout(r,ms));
const respond=(data:any,status=200)=>Response.json(data,{status});
const base=Deno.env.get('SUPABASE_URL')!,service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
async function db(path:string,body?:any){
 const r=await fetch(`${base}/rest/v1/${path}`,{method:body===undefined?'GET':'POST',
 headers:{apikey:service,Authorization:`Bearer ${service}`,'Content-Type':'application/json'},
 body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(8000)});
 if(!r.ok)throw new Error('database_error');return await r.json();
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
  state.run={started_at:started,status:'running',demo:false,rules:freeRules,checked:0,errors:0,
   source_errors:[],engine:'supabase-free-market',telegram_configured:!!(cfg.telegram_token&&cfg.telegram_chat)};
  await commit();
  const get=async(url:string)=>{
   const r=await fetch(url,{headers:{Accept:'application/json'},signal:AbortSignal.timeout(10000)});
   if(!r.ok)throw new Error('public_source_unavailable');return await r.json();
  };
  try{
   const discovered:any[]=[];
   try{
    const j=await get('https://api.geckoterminal.com/api/v2/networks/solana/new_pools');
    if(!Array.isArray(j.data))throw new Error('schema');
    for(const row of j.data){
     const id=row.relationships?.base_token?.data?.id;
     if(typeof id==='string'&&id.startsWith('solana_'))discovered.push({address:id.slice(7),source:'GeckoTerminal new pools',liquidity:n(row.attributes?.reserve_in_usd)});
    }
   }catch{state.run.source_errors.push('GeckoTerminal: descoberta indisponível');}
   try{
    const j=await get('https://api.dexscreener.com/token-profiles/latest/v1');
    if(!Array.isArray(j))throw new Error('schema');
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
   const addresses=Object.keys(state.tokens).filter(validAddress).slice(0,freeRules.max_tracked);
   if(!addresses.length&&state.run.source_errors.length)throw new Error('discovery_unavailable');
   if(addresses.length){
    const pairs=await get('https://api.dexscreener.com/tokens/v1/solana/'+addresses.join(','));
    if(!Array.isArray(pairs))throw new Error('schema_changed');
    const byToken:any={};
    for(const p of pairs){const a=p.baseToken?.address;if(addresses.includes(a)&&p.chainId==='solana'&&(!byToken[a]||(n(p.liquidity?.usd)||0)>(n(byToken[a].liquidity?.usd)||0)))byToken[a]=p;}
    let accounts:any[]=[];
    try{
     const r=await fetch('https://api.mainnet.solana.com',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jsonrpc:'2.0',id:1,method:'getMultipleAccounts',params:[addresses,{encoding:'jsonParsed',commitment:'confirmed'}]}),signal:AbortSignal.timeout(10000)});
     const j=await r.json();if(!r.ok||j.error||!Array.isArray(j.result?.value))throw new Error('rpc');accounts=j.result.value;
    }catch{state.run.source_errors.push('Solana RPC: permissões não puderam ser verificadas');}
    for(let ix=0;ix<addresses.length;ix++){
     const a=addresses[ix],t=state.tokens[a];
     try{
      const snap=fromDex(a,byToken[a],accounts[ix],now());snap.sources.discovery=t.discovery_source;
      applyFree(state,t,snap,now());
     }catch{
      if(t.status==='candidate')event(state,t,'data_gap',['Dados de mercado indisponíveis'],now());
      t.status='incomplete';t.qualified_at=0;t.last_checked=now();t.reasons=['Pool não encontrada ou dados incompatíveis'];state.run.errors++;
     }
     state.run.checked++;
    }
   }
   updateOutcomes(state,now());
   state.run.status=state.run.errors||state.run.source_errors.length?'partial':'ok';state.backoff_until=0;
  }catch{
   state.run.status='error';state.run.error='public_sources_unavailable';state.backoff_until=now()+600;
  }
  state.run.completed_at=now();state.alerts=state.alerts.slice(-400);await commit();await publish();
  let attempts=0;
  for(const a of state.alerts){
   if(a.delivery!=='pending')continue;
   if(now()-a.created_at>1800){a.delivery='expired';continue;}
   if(!cfg.telegram_token||!cfg.telegram_chat||a.next_attempt>now()||attempts>=3||now()-started>100)continue;
   if(a.attempts>=3){a.delivery='failed';continue;}
   attempts++;a.attempts=(a.attempts||0)+1;
   const label=a.kind==='candidate'?'SINAL DE MERCADO — RISCO PARCIAL':a.kind;
   const text=`Crypto Sniper gratuito | ${label}\n${a.snapshot.symbol||'?'} | Solana\nCA: ${a.address}\n${a.reasons.join('\n')}\nConsulta: ${new Date(a.created_at*1000).toISOString()}\nNão verifica insiders, concentração ou bundles. Sem previsão de lucro.\n${a.snapshot.pair_url}`;
   try{
    const r=await fetch(`https://api.telegram.org/bot${cfg.telegram_token}/sendMessage`,{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({chat_id:cfg.telegram_chat,text,link_preview_options:{is_disabled:true}}),signal:AbortSignal.timeout(5000)});
    const result=await r.json();if(result.ok)a.delivery='sent';else a.next_attempt=now()+300;
   }catch{a.next_attempt=now()+300;}
   await commit();await pause(1100);
  }
  await commit();return respond({status:state.run.status,checked:state.run.checked,public_feed:true});
 }catch{return respond({error:'radar_unavailable'},503);}
 finally{if(acquired)try{await db('rpc/pump_release',{p_owner:owner});}catch{/* expires */}}
});
