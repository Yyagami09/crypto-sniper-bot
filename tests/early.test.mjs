import test from 'node:test';
import assert from 'node:assert/strict';
import {observeEarly,earlyAssessment,finishEarly,publicEarly} from '../supabase/functions/pump-radar/early.ts';
import {evaluateFree,publicFeed} from '../supabase/functions/pump-radar/free-core.ts';
import {eligibleAlerts,deliverPersonal} from '../supabase/functions/pump-radar/notifications.ts';
const now=2000000000,a='2'.repeat(32),pair='3'.repeat(32);
const snap=(time=now)=>({address:a,chain_id:'solana',symbol:'EARLY',pair_address:pair,profile:'free-market-v1',
 price:.001,liquidity:30000,valuation:60000,valuation_type:'Market cap',pool_created_at:now-180,
 volume_5m:100,buy_count_5m:3,sell_count_5m:2,change_5m:-1,observed_at:time,
 mint_disabled:true,freeze_disabled:true,extensions_review:false,
 risk:{version:'risk-v1',status:'reviewed',checked_at:time,lp_chain_checked:true}});
function observe(state,t,s,time){t.snapshot=s;t.last_checked=time;return observeEarly(state,t,s,time);}

test('an early observation can qualify below 100k without momentum while classic stays unchanged',()=>{
 const state={alerts:[]},t={address:a,status:'watch'};
 let r=observe(state,t,snap(),now);assert.equal(r.status,'observing');assert.equal(state.alerts.length,0);
 r=observe(state,t,snap(now+60),now+60);assert.equal(r.status,'reviewed');
 assert.equal(state.alerts.length,1);assert.equal(state.alerts[0].kind,'early_watch');
 assert.equal(evaluateFree(snap(now+60),null,now+60).status,'watch');assert.equal(t.status,'watch');
 for(let i=2;i<10;i++)observe(state,t,snap(now+i*60),now+i*60);
 assert.equal(state.alerts.filter(a=>a.kind==='early_watch').length,1);
});
test('missing risk, active authority, stale observations and unavailable liquidity never pass the initial triage',()=>{
 for(const extra of [{risk:null},{mint_disabled:false},{liquidity:null},{observed_at:now-121},{risk:{status:'reviewed'}}]){
  const state={alerts:[]},t={address:a,status:'watch'};
  observe(state,t,{...snap(),...extra},now);const r=observe(state,t,{...snap(now+60),...extra},now+60);
  assert.notEqual(r.status,'reviewed');assert.equal(state.alerts.length,0);
 }
 const r={first_price:.001,first_liquidity:30000};
 assert.equal(earlyAssessment({...snap(),liquidity:null},r,now).liquidity_since_first_pct,null);
});
test('the early clock needs separate valid readings and restarts after gaps or risk failure',()=>{
 const state={alerts:[]},t={address:a};observe(state,t,snap(),now);
 assert.equal(observe(state,t,snap(now+10),now+10).status,'observing');
 assert.equal(observe(state,t,snap(now+300),now+300).status,'observing');
 observe(state,t,{...snap(now+360),risk:null},now+360);
 assert.equal(observe(state,t,snap(now+420),now+420).status,'observing');
 assert.equal(observe(state,t,snap(now+480),now+480).status,'reviewed');
});
test('extension retains an alert instead of celebrating the late observation and pool change starts a new baseline',()=>{
 const state={alerts:[]},t={address:a};observe(state,t,snap(),now);
 let r=observe(state,t,{...snap(now+60),price:.0016},now+60);
 assert.equal(r.status,'extended');assert.equal(state.alerts.length,0);
 const first=r.id;r=observe(state,t,{...snap(now+120),pair_address:'4'.repeat(32),price:.0016},now+120);
 assert.notEqual(r.id,first);assert.equal(r.first_price,.0016);assert.equal(r.observations,1);
});
test('all records retain initial references, later classic timing, observed outcomes and interrupted coverage',()=>{
 const state={alerts:[]},t={address:a,status:'watch'};
 const first=observe(state,t,snap(),now);observe(state,t,snap(now+60),now+60);
 t.status='candidate';t.last_signal_at=now+300;
 let r=observe(state,t,{...snap(now+300),price:.0012},now+300);
 assert.equal(r.first_at,now);assert.equal(r.classic_at,now+300);
 assert.ok(Math.abs(r.classic_since_first_pct-20)<.001);
 r=observe(state,t,{...snap(now+900),price:.0008},now+900);
 assert.ok(Math.abs(r.change_15m.pct+20)<.001);assert.ok(r.max_drop_pct<0);
 const changed=finishEarly(state,new Set(),now+960);
 assert.equal(changed[0].id,first.id);assert.equal(changed[0].tracking_stopped_at,now+960);
 assert.equal(changed[0].change_1h,undefined);
});
test('experimental and classic alerts are isolated per-account and rollback immediately excludes experimental events',async()=>{
 const state={tokens:{},alerts:[]},t={address:a,status:'watch'};state.tokens[a]=t;
 observe(state,t,snap(),now);observe(state,t,snap(now+60),now+60);
 state.alerts.push({id:'classic',kind:'candidate',address:a,created_at:now+60,snapshot:t.snapshot});
 t.status='candidate';
 assert.equal(eligibleAlerts(state,'early-v1',now+60).length,1);
 assert.equal(eligibleAlerts(state,'early-v1',now+60)[0].kind,'early_watch');
 assert.equal(eligibleAlerts(state,'classic',now+60).length,1);
 assert.equal(eligibleAlerts(state,'classic',now+60)[0].kind,'candidate');
 t.early.status='blocked';assert.equal(eligibleAlerts(state,'early-v1',now+60).length,0);
});
test('public feed never exposes raw experiment cache fields or turns experimental records into gold candidates',()=>{
 const state={tokens:{},early_tokens:{},alerts:[],early_cohorts:{secret:'PRIVATE'}};
 const t={address:a,status:'watch'};observe(state,t,snap(),now);t.early.secret='PRIVATE';state.early_tokens[a]=t;
 const feed=publicFeed(state);
 assert.equal(Object.keys(feed.tokens).length,0);assert.ok(!JSON.stringify(feed).includes('PRIVATE'));
 assert.equal(feed.early_tokens[a].early.first_price,.001);assert.equal(feed.early_tokens[a].status,'watch');
});

test('delivery follows each saved account mode and excludes notices from before activation',async()=>{
 const state={tokens:{},alerts:[]},t={address:a,status:'watch'};state.tokens[a]=t;
 observe(state,t,snap(),now);observe(state,t,snap(now+60),now+60);
 t.status='candidate';state.alerts.push({id:'classic',kind:'candidate',address:a,created_at:now+60,snapshot:t.snapshot});
 const connections=['early','classic','later'].map(user_id=>({user_id,enabled:true,connected_at:new Date((now-60)*1000).toISOString(),chat_id:user_id,token:'test'}));
 const profiles=connections.map(c=>({id:c.user_id,radar_mode:c.user_id==='classic'?'classic':'early-v1',radar_mode_since:new Date((c.user_id==='later'?now+120:now)*1000).toISOString()}));
 const sent=[];
 const db=async(path,body)=>path.startsWith('rpc/')?connections:path.startsWith('sniper_profiles')?profiles:[];
 await deliverPersonal(state,db,now+60,async(url,opts)=>{sent.push(JSON.parse(opts.body));return {json:async()=>({ok:true})};},()=>now+60);
 assert.equal(sent.length,2);
 assert.ok(sent.find(m=>m.chat_id==='early').text.includes('EXPERIMENTAL'));
 assert.ok(!sent.find(m=>m.chat_id==='classic').text.includes('EXPERIMENTAL'));
 assert.ok(!sent.some(m=>m.chat_id==='later'));
});

test('early observations retain the liquidity deterioration veto even above the minimum dollar floor',()=>{
 const state={alerts:[]},t={address:a};observe(state,t,{...snap(),liquidity:60000},now);
 const r=observe(state,t,{...snap(now+60),liquidity:35000},now+60);
 assert.equal(r.status,'blocked');assert.equal(state.alerts.length,0);
});
