import test from 'node:test';
import assert from 'node:assert/strict';
import {unseenAlerts} from '../pump/browser_alerts.js';
import {matchingStart,publicConnection,validPassword,validUsername} from '../supabase/functions/sniper-account/core.ts';
import {deliverPersonal} from '../supabase/functions/pump-radar/notifications.ts';

test('first load is silent; new alerts notify once; stale alerts stay silent',()=>{
 const state={},old={id:'old',created_at:100,kind:'candidate'},fresh={id:'new',created_at:1000,kind:'candidate'};
 assert.deepEqual(unseenAlerts(state,[old],1000),[]);
 assert.deepEqual(unseenAlerts(state,[old,fresh],1000),[fresh]);
 assert.deepEqual(unseenAlerts(state,[fresh],1001),[]);
 assert.deepEqual(unseenAlerts(state,[{...old,id:'stale'},{...fresh,id:'future',created_at:1100}],1001),[]);
});
test('Telegram confirmation binds the fresh private /start challenge to its sender',()=>{
 const since=Date.now()/1000-30,good={date:since+5,text:'/start secret',chat:{type:'private',id:42},from:{id:42}};
 const check=m=>matchingStart([{message:m}],'secret',since);
 assert.equal(check(good),good);
 assert.equal(check({...good,text:'/start other'}),undefined);
 assert.equal(check({...good,date:since-60}),undefined);
 assert.equal(check({...good,chat:{type:'group',id:42}}),undefined);
 assert.equal(check({...good,from:{id:99}}),undefined);
});
test('connection status never exposes the token, chat ID or Vault secret',()=>{
 const out=JSON.stringify(publicConnection({enabled:true,token:'HIDDEN',chat_id:'HIDDEN',secret_id:'HIDDEN',bot_username:'testbot',challenge:'HIDDEN'}));
 assert.ok(!out.includes('HIDDEN'));
 assert.ok(validUsername('amigo_1'));assert.ok(!validUsername('admin@example.com'));assert.ok(!validPassword('1234'));
});
const now=2000000000;
const connection={user_id:'u1',enabled:true,connected_at:new Date((now-600)*1000).toISOString(),chat_id:42,token:'PRIVATE_TOKEN'};
const alert={id:'a1',kind:'candidate',created_at:now-60,address:'A',snapshot:{profile:'free-market-v1',symbol:'TEST'},reasons:['partial']};
test('personal delivery skips old, demo, sent and not-yet-due events and persists an attempt before sending',async()=>{
 const writes=[],sent=[];
 const state={alerts:[alert,{...alert,id:'old',created_at:now-700},{...alert,id:'demo',snapshot:{profile:'demo'}}]};
 const db=async(path,body,method)=>{
  if(path.startsWith('rpc/'))return [connection];
  if(body){writes.push({path,body,method});return [];}
  return [];
 };
 await deliverPersonal(state,db,now,async(url,opts)=>{assert.equal(writes[0].body.attempts,1);sent.push(JSON.parse(opts.body));return {json:async()=>({ok:true})};},()=>now);
 assert.equal(sent.length,1);assert.equal(writes.at(-1).body.status,'sent');
 assert.ok(!sent[0].text.includes('PRIVATE_TOKEN'));
 for(const record of [{status:'sent',attempts:1},{status:'pending',attempts:3},{status:'pending',attempts:1,next_attempt:new Date((now+20)*1000).toISOString()}]){
  const once=async(path,body)=>path.startsWith('rpc/')?[connection]:body?[]:[{alert_id:'a1',...record}];
  await deliverPersonal({alerts:[alert]},once,now,()=>{throw new Error('must not send');},()=>now);
 }
});
test('a blocked Telegram bot is disabled and does not retry forever',async()=>{
 const writes=[];
 const db=async(path,body)=>{if(path.startsWith('rpc/'))return [connection];if(body){writes.push({path,body});return [];}return [];};
 await deliverPersonal({alerts:[alert]},db,now,async()=>({status:403,json:async()=>({ok:false})}),()=>now);
 assert.ok(writes.some(w=>w.path.startsWith('sniper_telegram')&&w.body.enabled===false));
 assert.equal(writes.at(-1).body.status,'failed');
});
