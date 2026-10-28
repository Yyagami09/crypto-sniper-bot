import {rules,n,validAddress,normalize,apply,event} from './core.ts';
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
  if(state.backoff_until>now())return respond({status:'cooldown'});
  state.run={started_at:started,status:'running',demo:false,rules,checked:0,errors:0,engine:'supabase-edge'};
  await commit();
  if(!cfg.gmgn_key){state.run.status='missing_key';state.run.completed_at=now();await commit();return respond({status:'missing_key'});}
  let last=0;
  async function gmgn(path:string,params:any,body?:any){
   await pause(Math.max(0,1100-(Date.now()-last)));last=Date.now();
   const url=new URL('https://openapi.gmgn.ai'+path);
   Object.entries({...params,timestamp:Math.floor(now()),client_id:crypto.randomUUID()}).forEach(([k,v])=>url.searchParams.set(k,String(v)));
   const r=await fetch(url,{method:body?'POST':'GET',headers:{'X-APIKEY':cfg.gmgn_key,'Content-Type':'application/json'},
    body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(8000)});
   if(!r.ok)throw new Error([401,403,429].includes(r.status)?'api_access_or_rate_limit':'provider_error');
   const result=await r.json();if(result.code!==0)throw new Error('provider_rejected');return result.data;
  }
  try{
   const recent=await gmgn('/v1/trenches',{chain:'sol'},{version:'v2',completed:{filters:['offchain','onchain'],launchpad_platform_v2:true,quote_address_type:[4,5,3,1,13,0],limit:50}});
   const trending=await gmgn('/v1/market/rank',{chain:'sol',interval:'5m',limit:50});
   if(!Array.isArray(recent.completed)||!Array.isArray(trending.rank))throw new Error('schema_changed');
   state.tokens??={};state.alerts??=[];
   for(const [a,t] of Object.entries<any>(state.tokens))if(now()-t.first_seen>rules.retention_hours*3600&&t.status!=='candidate')delete state.tokens[a];
   for(const item of [...recent.completed,...trending.rank]){
    const a=item.address;if(!validAddress(a))continue;
    const risk={observed_at:now(),rug_ratio:item.rug_ratio,bundler_rate:item.bundler_rate,rat_trader_amount_rate:item.rat_trader_amount_rate,is_wash_trading:item.is_wash_trading};
    if(state.tokens[a]){state.tokens[a].discovery_risk=risk;continue;}
    const liq=n(item.liquidity);if(liq!==null&&liq<rules.min_liquidity)continue;
    if(Object.keys(state.tokens).length>=rules.max_tracked){
     const old=Object.values<any>(state.tokens).filter(t=>!['candidate','confirming'].includes(t.status)&&t.last_checked>0&&now()-t.last_checked>600).sort((a,b)=>a.first_seen-b.first_seen)[0];
     if(!old)continue;delete state.tokens[old.address];
    }
    state.tokens[a]={address:a,first_seen:now(),last_checked:0,status:'queued',reasons:[],history:[],discovery_risk:risk};
   }
   const ordered=Object.values<any>(state.tokens).sort((a,b)=>a.last_checked-b.last_checked);
   const hot=ordered.filter(t=>['candidate','confirming'].includes(t.status)).slice(0,rules.batch_size/2);
   const selected=[...hot,...ordered.filter(t=>!hot.includes(t)).slice(0,rules.batch_size-hot.length)];
   for(const t of selected){
    if(now()-started>85)break;
    await commit();
    try{
     const i=await gmgn('/v1/token/info',{chain:'sol',address:t.address});
     const s=await gmgn('/v1/token/security',{chain:'sol',address:t.address});
     apply(state,t,normalize(t.address,i,s,t.discovery_risk,now()),now());
    }catch(e){
     if(e instanceof Error&&e.message==='api_access_or_rate_limit')throw e;
     if(t.status==='candidate')event(state,t,'data_gap',['Consulta indisponível; confirmação interrompida'],now());
     t.status='incomplete';t.qualified_at=0;t.last_checked=now();t.reasons=['Consulta indisponível ou formato incompatível'];state.run.errors++;
    }
    state.run.checked++;
   }
   state.run.status=state.run.errors?'partial':'ok';state.backoff_until=0;
  }catch(e){
   state.run.status='error';state.run.error=e instanceof Error&&['schema_changed','api_access_or_rate_limit','provider_rejected'].includes(e.message)?e.message:'provider_error';
   state.backoff_until=now()+600;
  }
  state.run.completed_at=now();state.alerts=state.alerts.slice(-400);await commit();
  // Outbox: bounded delivery, only if the owner configured their private bot/chat.
  let attempts=0;
  for(const a of state.alerts){
   if(a.delivery!=='pending')continue;
   if(now()-a.created_at>900){a.delivery='expired';continue;}
   if(!cfg.telegram_token||!cfg.telegram_chat||a.next_attempt>now()||attempts>=3||now()-started>100)continue;
   if(a.attempts>=3){a.delivery='failed';continue;}
   attempts++;a.attempts=(a.attempts||0)+1;
   const text=`Crypto Sniper | ${a.kind}\n${a.snapshot.symbol||'?'} | Solana\nCA: ${a.address}\n${a.reasons.join('\n')}\nConsulta: ${new Date(a.created_at*1000).toISOString()}\nTriagem experimental; confira os dados atuais.\nhttps://gmgn.ai/sol/token/${a.address}`;
   try{
    const r=await fetch(`https://api.telegram.org/bot${cfg.telegram_token}/sendMessage`,{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({chat_id:cfg.telegram_chat,text,link_preview_options:{is_disabled:true}}),signal:AbortSignal.timeout(5000)});
    const result=await r.json();if(result.ok)a.delivery='sent';else a.next_attempt=now()+120;
   }catch{a.next_attempt=now()+120;}
   await commit();await pause(1100);
  }
  await commit();return respond({status:state.run.status,checked:state.run.checked});
 }catch{return respond({error:'radar_unavailable'},503);}
 finally{if(acquired)try{await db('rpc/pump_release',{p_owner:owner});}catch{/* lease expires */}}
});
