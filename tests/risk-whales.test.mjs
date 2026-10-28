import test from 'node:test';
import assert from 'node:assert/strict';
import {cleanReport,assessRisk,enrichRisks} from '../supabase/functions/pump-radar/risk.ts';
import {observeWhales} from '../supabase/functions/pump-radar/whales.ts';
import {evaluateFree} from '../supabase/functions/pump-radar/free-core.ts';
import {liquidityTrend} from '../supabase/functions/pump-radar/trends.ts';
const now=2000000000,mint='2'.repeat(32),pool='3'.repeat(32),lp='6'.repeat(32),lpAccount='7'.repeat(32),creator='8'.repeat(32);
const program='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';
const snapshot=()=>({address:mint,pair_address:pool,price:2,liquidity:50000,volume_5m:10000,
 supply_raw:'1000000000',token_decimals:6,valuation:1000000,pool_created_at:now-3600,
 buy_count_5m:20,sell_count_5m:10,change_5m:5,mint_disabled:true,freeze_disabled:true,extensions_review:false});
const raw=()=>({mint,creator,risks:[],topHolders:[{address:'A'.repeat(32),owner:pool,pct:70},
 {address:'4'.repeat(32),owner:'4'.repeat(32),pct:2},{address:'5'.repeat(32),owner:'5'.repeat(32),pct:3}],
 markets:[{pubkey:pool,lp:{lpMint:lp,lpLockedPct:100,reserveSupply:'1000000',holders:[{address:lpAccount,owner:'9'.repeat(32)}]}}]});
const account=(mint,owner,amount,decimals=6)=>({owner:program,data:{parsed:{type:'account',info:{mint,owner,tokenAmount:{amount,decimals}}}}});
const accounts=()=>new Map([[lp,{owner:program,data:{parsed:{type:'mint',info:{supply:'1000000'}}}}],
 [lpAccount,account(lp,'9'.repeat(32),'1000000')]]);
const cached=()=>({fetched_at:now,report:cleanReport(raw(),mint)});

test('LP protection, selected pool, concentration outside pools and on-chain ownership are separate from market score',()=>{
 const risk=assessRisk(snapshot(),cached(),accounts(),now);
 assert.equal(risk.status,'reviewed');assert.equal(risk.top10_ex_pool_pct,5);
 assert.equal(risk.creator_lp_pct,0);assert.equal(risk.sell_check,'not_simulated');
 assert.equal(evaluateFree({...snapshot(),risk},null,now).status,'qualified');
});
test('a GANG-like unlocked LP and 100% creator ownership veto otherwise qualifying market activity',()=>{
 const c=cached();c.report.markets[0].locked_pct=0;
 c.report.risks=[{name:'Large Amount of LP Unlocked',level:'danger'}];
 const chain=accounts();chain.set(lpAccount,account(lp,creator,'1000000'));
 const risk=assessRisk(snapshot(),c,chain,now);
 assert.equal(risk.status,'blocked');assert.equal(risk.creator_lp_pct,100);
 assert.ok(risk.reasons.some(r=>r.includes('Criador detém')));
 assert.equal(evaluateFree({...snapshot(),risk},null,now).status,'blocked');
});
test('missing, stale, wrong-pool or malformed reports never become a security pass',()=>{
 assert.equal(assessRisk(snapshot(),null,accounts(),now).status,'pending');
 const old=cached();old.fetched_at=now-1801;assert.equal(assessRisk(snapshot(),old,accounts(),now).status,'pending');
 assert.equal(assessRisk({...snapshot(),pair_address:'A'.repeat(32)},cached(),accounts(),now).status,'pending');
 assert.equal(assessRisk(snapshot(),cached(),new Map(),now).status,'pending');
 assert.throws(()=>cleanReport({...raw(),mint:'A'.repeat(32)},mint));
 assert.equal(evaluateFree(snapshot(),null,now).status,'incomplete');
 assert.equal(evaluateFree({...snapshot(),risk:{version:'risk-v1',status:'reviewed'}},null,now).status,'incomplete');
});
test('high concentration and extreme turnover hold signals without claiming honeypot',()=>{
 const c=cached();c.report.holders[1].pct=60;
 assert.equal(assessRisk(snapshot(),c,accounts(),now).status,'blocked');
 const risk=assessRisk({...snapshot(),volume_5m:600000},cached(),accounts(),now);
 assert.equal(risk.status,'blocked');assert.match(risk.reasons[0],/não comprova manipulação/);
});
test('whale balance comparisons detect increases, price alone does not create inflow, and first observation is a baseline',()=>{
 const state={},s=snapshot(),report=cached().report;
 const chain=new Map([['4'.repeat(32),account(mint,'4'.repeat(32),'20000000')]]);
 let w=observeWhales(s,report,chain,state,now);
 assert.equal(w.status,'observing');assert.equal(w.items[0].delta_tokens,null);
 chain.set('4'.repeat(32),account(mint,'4'.repeat(32),'30000000'));
 w=observeWhales(s,report,chain,state,now+300);
 assert.equal(w.increases,1);assert.equal(w.items[0].delta_tokens,10);assert.equal(w.items[0].delta_usd,20);
 w=observeWhales({...s,price:4},report,chain,state,now+600);
 assert.equal(w.status,'unchanged');assert.equal(w.items[0].delta_usd,0);
 assert.equal(evaluateFree({...s,risk:assessRisk(s,cached(),accounts(),now),whales:w},null,now).status,'qualified');
});
test('RPC absence never fabricates a whale exit; confirmed closed accounts can show a balance decrease',()=>{
 const state={},report=cached().report,s=snapshot();
 observeWhales(s,report,new Map([['4'.repeat(32),account(mint,'4'.repeat(32),'20000000')]]),state,now);
 assert.equal(observeWhales(s,report,new Map(),state,now+300).status,'unavailable');
 const result=observeWhales(s,report,new Map([['4'.repeat(32),null]]),state,now+600);
 assert.equal(result.decreases,1);assert.equal(result.items[0].delta_tokens,-20);
});

test('burned LP is not confused with 100% control of the whole pool',()=>{
 const c=cached();c.report.markets[0].locked_pct=99;c.report.markets[0].reserve_supply_raw='100000000';
 const chain=accounts();chain.set(lpAccount,account(lp,creator,'1000000'));
 const risk=assessRisk(snapshot(),c,chain,now);
 assert.equal(risk.creator_lp_pct,100);assert.equal(risk.creator_pool_claim_pct,1);
 assert.equal(risk.status,'reviewed');
});

test('gradual withdrawal requires several LP declines and both pool reserves declining',()=>{
 const state={};let trend;
 for(let i=0;i<4;i++)trend=liquidityTrend({...snapshot(),base_reserve:1000*(1-i*.06),quote_reserve:100*(1-i*.06)},
  {lp_chain_checked:true,lp_supply_raw:String(1000000-i*30000)},state,now+i*300);
 assert.equal(trend.status,'warning');assert.equal(trend.observations,4);
 const trading={};
 for(let i=0;i<4;i++)trend=liquidityTrend({...snapshot(),base_reserve:1000*(1+i*.06),quote_reserve:100*(1-i*.06)},
  {lp_chain_checked:true,lp_supply_raw:'1000000'},trading,now+i*300);
 assert.equal(trend.status,'no_pattern');
 trend=liquidityTrend({...snapshot(),pair_address:'B'.repeat(32),base_reserve:500,quote_reserve:50},
  {lp_chain_checked:true,lp_supply_raw:'500000'},state,now+1200);
 assert.equal(trend.status,'collecting');assert.equal(trend.observations,1);
});

test('persistent reductions in large holder balances remain an advisory observation',()=>{
 const state={},s=snapshot(),report=cached().report;let out;
 for(let i=0;i<4;i++)out=observeWhales(s,report,new Map([['4'.repeat(32),account(mint,'4'.repeat(32),String(100000000-i*10000000))]]),state,now+i*300);
 assert.equal(out.gradual_reductions,1);assert.equal(out.items[0].gradual_reduction,true);
 assert.equal(evaluateFree({...s,risk:assessRisk(s,cached(),accounts(),now),whales:out},null,now).status,'qualified');
});

test('one-minute wallet samples show changes and preserve the twelve-minute gradual-reduction window',()=>{
 const state={},s=snapshot(),report=cached().report;let out;
 for(let i=0;i<=12;i++){
  out=observeWhales(s,report,new Map([['4'.repeat(32),account(mint,'4'.repeat(32),String(100000000-i*1000000))]]),state,now+i*60);
  if(i>0){assert.equal(out.decreases,1);assert.equal(out.items[0].delta_tokens,-1);}
  if(i<12)assert.equal(out.gradual_reductions,0);
 }
 assert.equal(out.gradual_reductions,1);
});
test('faster scans do not shorten the LP slow-rug observation window',()=>{
 const state={};let trend;
 for(let i=0;i<=12;i++){
  trend=liquidityTrend({...snapshot(),base_reserve:1000-i*20,quote_reserve:100-i*2},
   {lp_chain_checked:true,lp_supply_raw:String(1000000-i*10000)},state,now+i*60);
  if(i<12)assert.notEqual(trend.status,'warning');
 }
 assert.equal(trend.status,'warning');assert.equal(trend.observations,4);assert.equal(trend.window_minutes,12);
});

test('report scheduling is fair, bounds requests across minute scans and backs off unavailable reports',async()=>{
 const state={},calls=[];
 const snapshots=Array.from({length:12},(_,i)=>({...snapshot(),address:String(i+2).replace(/0/g,'A').repeat(32),volume_5m:12000-i}));
 for(let minute=0;minute<4;minute++){
  let time=now+minute*60;
  await enrichRisks(snapshots,state,async(url)=>{calls.push(url);throw Error('unavailable');},async()=>[],()=>time,time,async(ms)=>{time+=ms/1000;});
 }
 assert.equal(calls.length,10);assert.equal(new Set(calls).size,10);
 assert.ok(snapshots.every(s=>s.risk.status!=='reviewed'));
 let time=now+240;
 await enrichRisks(snapshots,state,async(url)=>{calls.push(url);throw Error('unavailable');},async()=>[],()=>time,time,async()=>{});
 assert.equal(calls.length,10);
 time=now+301;
 await enrichRisks(snapshots,state,async(url)=>{calls.push(url);throw Error('unavailable');},async()=>[],()=>time,time,async()=>{});
 assert.ok(calls.length>10);assert.ok(calls.length<=14);
});
test('warm report cache bypasses report HTTP but still verifies fresh LP accounts',async()=>{
 const state={risk_reports:{[mint]:cached()}},s=snapshot();let rpcs=0;
 await enrichRisks([s],state,()=>{throw Error('must use cache');},async(batch)=>{rpcs++;return batch.map(a=>accounts().get(a)||null);},()=>now,now,async()=>{});
 assert.equal(s.risk.status,'reviewed');assert.equal(rpcs,1);
});

test('RugCheck summary separates provider flags from local heuristics and expired reports stay unknown',()=>{
 const c=cached();c.report.risks=[{name:'Critical provider flag',level:'danger'},{name:'Provider warning',level:'warn'}];
 const risk=assessRisk({...snapshot(),volume_5m:600000},c,accounts(),now);
 assert.equal(risk.rugcheck.status,'reported');
 assert.deepEqual(risk.rugcheck.critical,['Critical provider flag']);
 assert.deepEqual(risk.rugcheck.warnings,['Provider warning']);
 assert.ok(!JSON.stringify(risk.rugcheck).includes('Atividade atípica'));
 const stale=assessRisk(snapshot(),{...c,fetched_at:now-1801},accounts(),now);
 assert.equal(stale.rugcheck.status,'stale');assert.deepEqual(stale.rugcheck.critical,[]);
});
