import test from 'node:test';
import assert from 'node:assert/strict';
import {normalize,evaluate,apply,n,flag} from '../supabase/functions/pump-radar/core.ts';
const now=2000000000,a='2'.repeat(32);
const info={address:a,symbol:'TEST',price:{price:.0011,price_5m:.001,volume_5m:18000,buy_volume_5m:11000,sell_volume_5m:7000},
 circulating_supply:1000000000,liquidity:65000,holder_count:450,creation_timestamp:now-7200,launchpad_status:2};
const security={top_10_holder_rate:.15,renounced_mint:true,renounced_freeze_account:true};
const rank={observed_at:now,rug_ratio:.05,bundler_rate:.08,rat_trader_amount_rate:.05,is_wash_trading:false};
const sample=()=>normalize(a,info,security,rank,now);
test('numeric unknowns and boolean tri-state',()=>{for(const x of [null,'',undefined,'NaN',true,{},[]])assert.equal(n(x),null);assert.equal(flag('unknown'),null);assert.equal(flag(false),false);});
test('nested price, supply and recent discovery',()=>{const s=sample();assert.equal(s.market_cap,1100000);assert.equal(s.rug,.05);assert.equal(evaluate(s,null,now).status,'qualified');});
test('old discovery is not a security pass',()=>{const s=normalize(a,info,security,{...rank,observed_at:now-121},now);assert.equal(evaluate(s,null,now).status,'incomplete');});
test('explicit risks override missing fields',()=>{const s=sample();s.mint_disabled=false;s.rug=null;assert.equal(evaluate(s,null,now).status,'blocked');});
test('two observations, exit event and restart deduplication',()=>{let state={alerts:[]},t={address:a,history:[]};apply(state,t,sample(),now);assert.equal(t.status,'confirming');apply(state,t,sample(),now+60);assert.equal(state.alerts.length,1);assert.equal(t.status,'candidate');[state,t]=JSON.parse(JSON.stringify([state,t]));const bad=sample();bad.liquidity=40000;apply(state,t,bad,now+120);assert.equal(state.alerts[1].kind,'conditions_lost');apply(state,t,sample(),now+180);apply(state,t,sample(),now+240);assert.equal(state.alerts.filter(x=>x.kind==='candidate').length,1);});
test('long gaps and mismatched tokens cannot confirm',()=>{const state={alerts:[]},t={address:a};apply(state,t,sample(),now);apply(state,t,sample(),now+1000);assert.equal(t.status,'confirming');assert.throws(()=>normalize(a,{...info,address:'3'.repeat(32)},security,rank,now));});
