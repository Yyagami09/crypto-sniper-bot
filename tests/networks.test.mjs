import test from 'node:test';
import assert from 'node:assert/strict';
import {networkCatalog,networkSnapshot,scanNetwork,publicNetworks,collectNetworks} from '../supabase/functions/pump-radar/networks.ts';
import {freeRules,applyFree} from '../supabase/functions/pump-radar/free-core.ts';
const now=2000000000,address='0x'+'a'.repeat(40),pool='0x'+'b'.repeat(64);
const network=networkCatalog.find(x=>x.id==='robinhood');
const pair={chainId:'robinhood',baseToken:{address,symbol:'TEST',name:'Test'},pairAddress:pool,priceUsd:'0.1',
 liquidity:{usd:30000},marketCap:1000000,volume:{m5:6000},txns:{m5:{buys:20,sells:10}},priceChange:{m5:3},pairCreatedAt:(now-3600)*1000};
const discovery={data:[{attributes:{reserve_in_usd:'30000'},relationships:{base_token:{data:{id:'robinhood_'+address}}}}]};

test('Robinhood v4 pool IDs work, casing is normalized, market cap and FDV remain separate',()=>{
 const s=networkSnapshot('robinhood',address.toUpperCase().replace('0X','0x'),pair,now);
 assert.equal(s.chain_id,'robinhood');assert.equal(s.pair_address,pool);
 assert.equal(s.pair_url,'https://dexscreener.com/robinhood/'+pool);
 assert.equal(s.risk.status,'unsupported');assert.equal(s.mint_disabled,null);
 assert.equal(networkSnapshot('robinhood',address,{...pair,marketCap:null,fdv:900000},now).valuation_type,'FDV');
 assert.throws(()=>networkSnapshot('base',address,pair,now));
 assert.throws(()=>networkSnapshot('robinhood',address,{...pair,baseToken:{address:'0x'+'c'.repeat(40)}},now));
});
test('cross-chain data cannot confirm a Solana signal, even if all market criteria match',()=>{
 const s=networkSnapshot('robinhood',address,pair,now),state={alerts:[]},t={address};
 applyFree(state,t,s,now);applyFree(state,t,s,now+300);
 assert.equal(state.alerts.length,0);assert.equal(t.status,'incomplete');
});
test('scan isolates chain/address namespaces, chooses highest-liquidity matching pool and never creates alerts',async()=>{
 const feeds={};
 const get=async(url)=>url.includes('gecko')?discovery:[{...pair,chainId:'base',liquidity:{usd:999999}},pair,{...pair,pairAddress:'0x'+'d'.repeat(40),liquidity:{usd:40000}}];
 const feed=await scanNetwork(network,null,get,[],()=>now,freeRules);
 assert.equal(Object.keys(feed.tokens).length,1);assert.equal(feed.tokens[address].status,'watch');
 assert.equal(feed.tokens[address].snapshot.liquidity,40000);assert.deepEqual(feed.alerts,[]);
 const state={networks:{robinhood:feed,unknown:{secret:'PRIVATE'}},private_key:'PRIVATE'};
 feed.secret='PRIVATE';feed.tokens[address].secret='PRIVATE';feed.tokens[address].snapshot.secret='PRIVATE';
 const out=publicNetworks(state,freeRules);
 assert.ok(!JSON.stringify(out).includes('PRIVATE'));assert.equal(out.robinhood.tokens[address].snapshot.risk.status,'unsupported');
});
test('failed collection preserves old timestamps and marks values incomplete instead of fresh',async()=>{
 const get=async(url)=>url.includes('gecko')?discovery:[pair];
 const feed=await scanNetwork(network,null,get,[],()=>now,freeRules);
 const failure=await scanNetwork(network,feed,async()=>{throw Error('rate limited');},[],()=>now+60,freeRules);
 assert.equal(failure.run.status,'partial');assert.equal(failure.tokens[address].status,'incomplete');
 assert.equal(failure.tokens[address].snapshot.observed_at,now);assert.equal(failure.run.checked,0);
});
test('secondary collection obeys its global deadline without overwriting Solana tokens or alerts',async()=>{
 const state={tokens:{solana:{unchanged:true}},alerts:[{id:'existing'}]};
 await collectNetworks(state,()=>{throw Error('must not fetch after deadline');},[],()=>now+86,now,freeRules);
 assert.deepEqual(state.tokens,{solana:{unchanged:true}});assert.deepEqual(state.alerts,[{id:'existing'}]);
 assert.deepEqual(state.networks,{});
});
