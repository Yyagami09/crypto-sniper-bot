import {ApiError,validUsername,validPassword,matchingStart,publicConnection} from './core.ts';
const base=Deno.env.get('SUPABASE_URL')!,service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const reply=(data:any,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
async function api(path:string,body?:any,method?:string,bearer=service){
 const r=await fetch(base+path,{method:method||(body===undefined?'GET':'POST'),
  headers:{apikey:service,Authorization:`Bearer ${bearer}`,'Content-Type':'application/json',Prefer:'return=representation'},
  body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
 if(!r.ok)throw new ApiError('operation_failed',r.status===429?429:400);
 return r.status===204?null:await r.json();
}
const db=(path:string,body?:any,method?:string)=>api('/rest/v1/'+path,body,method);
async function tg(token:string,method:string,body:any={}){
 try{
  const r=await fetch(`https://api.telegram.org/bot${token}/${method}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(7000)});
  const j=await r.json();if(!j.ok)throw new ApiError(r.status===409?'bot_in_use':'telegram_unavailable');return j.result;
 }catch(e){if(e instanceof ApiError)throw e;throw new ApiError('telegram_unavailable');}
}
async function createUser(username:string,password:string,name:string,role='user'){
 if(!validUsername(username)||!validPassword(password)||!name||name.length>80)throw new ApiError('invalid_user');
 const u=await api('/auth/v1/admin/users',{email:`${username}@crypto-sniper.invalid`,password,email_confirm:true});
 try{await db('sniper_profiles',{id:u.id,username,display_name:name,role});}
 catch(e){await api('/auth/v1/admin/users/'+u.id,undefined,'DELETE');throw e;}
 return {username,role};
}
Deno.serve(async req=>{
 if(req.method!=='POST')return reply({error:'method_not_allowed'},405);
 try{
  const raw=await req.text();if(raw.length>6000)throw new ApiError('too_large',413);
  let body:any;try{body=JSON.parse(raw);}catch{throw new ApiError('invalid_request');}
  if(body.action==='bootstrap'){
   const supplied=req.headers.get('x-pump-token');if(!supplied)throw new ApiError('unauthorized',401);
   const cfg=await db('rpc/pump_worker_config',{});
   const digest=async(s:string)=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
   const a=await digest(supplied),b=await digest(cfg.cron_token||'');let diff=0;for(let i=0;i<a.length;i++)diff|=a[i]^b[i];
   if(!cfg.cron_token||diff)throw new ApiError('unauthorized',401);
   if((await db('sniper_profiles?select=id&limit=1')).length)throw new ApiError('already_initialized',409);
   await createUser('admin',body.admin_password,'Administrador','admin');
   await createUser('teste',body.test_password,'Conta de teste');
   return reply({created:['admin','teste']});
  }
  const bearer=req.headers.get('Authorization')?.replace(/^Bearer /,'');
  if(!bearer)throw new ApiError('unauthorized',401);
  let u:any;try{u=await api('/auth/v1/user',undefined,'GET',bearer);}catch{throw new ApiError('unauthorized',401);}
  const profile=(await db(`sniper_profiles?id=eq.${u.id}&select=*`))[0];
  if(!profile?.active)throw new ApiError('access_denied',403);
  const uid=u.id,action=body.action;
  if(action==='session')return reply({profile});
  if(action==='radar_mode'){
   if(!['classic','early-v1'].includes(body.mode))throw new ApiError('invalid_request');
   const rows=await db('sniper_profiles?id=eq.'+uid,{radar_mode:body.mode,radar_mode_since:new Date().toISOString()},'PATCH');
   return reply({profile:rows[0]});
  }
  if(action==='change_password'){
   if(!validPassword(body.password))throw new ApiError('weak_password');
   await api('/auth/v1/user',{password:body.password},'PUT',bearer);return reply({ok:true});
  }
  if(action?.startsWith('admin_')){
   if(profile.role!=='admin')throw new ApiError('admin_required',403);
   if(action==='admin_list')return reply({users:await db('sniper_profiles?select=*&order=created_at.asc')});
   if(action==='admin_create')return reply(await createUser(body.username,body.password,body.display_name,'user'));
   const target=(await db(`sniper_profiles?id=eq.${encodeURIComponent(body.user_id||'')}&select=*`))[0];
   if(!target)throw new ApiError('user_not_found');
   if(target.id===uid)throw new ApiError('own_account_protected');
   if(target.role==='admin')throw new ApiError('admin_account_protected');
   if(action==='admin_toggle'){
    await db('sniper_profiles?id=eq.'+target.id,{active:!target.active},'PATCH');
    await api('/auth/v1/admin/users/'+target.id,{ban_duration:target.active?'876000h':'none'},'PUT');
    return reply({ok:true});
   }
   if(action==='admin_reset'){
    if(!validPassword(body.password))throw new ApiError('weak_password');
    await api('/auth/v1/admin/users/'+target.id,{password:body.password},'PUT');return reply({ok:true});
   }
   throw new ApiError('unknown_action');
  }
  const connection=(await db('rpc/sniper_telegram_credentials',{p_user:uid}))[0];
  if(action==='telegram_status'){
   const last=await db(`sniper_deliveries?user_id=eq.${uid}&select=status,sent_at,created_at&order=created_at.desc&limit=1`);
   return reply({connection:publicConnection(connection),last_delivery:last[0]||null});
  }
  if(action==='telegram_prepare'){
   if(connection&&Date.now()-Date.parse(connection.challenge_at)<15000)throw new ApiError('wait_before_retry',429);
   if(typeof body.token!=='string'||!/^\d{5,20}:[A-Za-z0-9_-]{25,80}$/.test(body.token))throw new ApiError('invalid_bot_token');
   const bot=await tg(body.token,'getMe'),hook=await tg(body.token,'getWebhookInfo');
   if(hook.url)throw new ApiError('bot_has_webhook');
   const challenge=crypto.randomUUID().replaceAll('-','');
   await db('rpc/sniper_save_telegram',{p_user:uid,p_bot:bot.id,p_username:bot.username,p_token:body.token,p_challenge:challenge});
   return reply({connection:{connected:false,bot_username:bot.username,link:`https://t.me/${bot.username}?start=${challenge}`}});
  }
  if(action==='telegram_confirm'){
   if(!connection)throw new ApiError('prepare_first');
   if(connection.enabled)return reply({connection:publicConnection(connection)});
   if(Date.now()-Date.parse(connection.challenge_at)>900000)throw new ApiError('connection_expired');
   const updates=await tg(connection.token,'getUpdates',{timeout:0,limit:100,allowed_updates:['message']});
   const m=matchingStart(updates,connection.challenge,Date.parse(connection.challenge_at)/1000-2);
   if(!m)throw new ApiError('start_not_received');
   await db('sniper_telegram?user_id=eq.'+uid,{chat_id:m.chat.id,enabled:true,connected_at:new Date().toISOString()},'PATCH');
   return reply({connected:true});
  }
  if(action==='telegram_test'){
   if(!connection?.enabled)throw new ApiError('connect_first');
   if(connection.last_test_at&&Date.now()-Date.parse(connection.last_test_at)<60000)throw new ApiError('wait_before_retry',429);
   await db('sniper_telegram?user_id=eq.'+uid,{last_test_at:new Date().toISOString()},'PATCH');
   await tg(connection.token,'sendMessage',{chat_id:connection.chat_id,text:'🔔 Crypto Sniper: teste de notificação. Sua conexão está funcionando. Este é um teste, sem sinal de mercado.'});
   return reply({ok:true});
  }
  if(action==='telegram_disconnect'){
   await db('rpc/sniper_disconnect_telegram',{p_user:uid});return reply({ok:true});
  }
  throw new ApiError('unknown_action');
 }catch(e){return reply({error:e instanceof ApiError?e.code:'service_unavailable'},e instanceof ApiError?e.status:503);}
});
