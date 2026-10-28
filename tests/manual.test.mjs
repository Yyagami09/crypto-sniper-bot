import test from 'node:test';
import assert from 'node:assert/strict';
import {parseManualInput,parseCandles,chartEvidence,manualVerdict,analyzeManual} from '../supabase/functions/sniper-account/manual.ts';
const now=2000000040,mint='2'.repeat(32),pool='3'.repeat(32),program='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';
const closed=Math.floor(now/60)*60-60;
const candles=()=>Array.from({length:30},(_,i)=>[closed-(29-i)*60,1+i*.01,1.03+i*.01,.98+i*.01,1.01+i*.01,10]);
const base={price:1,chain_id:'solana',mint_disabled:true,freeze_disabled:true,extensions_review:false,liquidity:30000,risk:{status:'reviewed',lp_chain_checked:true}};

test('manual inputs are network-bound and never accept arbitrary request URLs',()=>{
 assert.equal(parseManualInput('solana',mint).type,'token');
 assert.equal(parseManualInput('solana','https://dexscreener.com/solana/'+pool).type,'pair');
 for(const input of ['https://evil.example/solana/'+mint,'https://dexscreener.com@evil.example/solana/'+mint,'https://dexscreener.com/base/0x'+'a'.repeat(40),'../../private'])assert.throws(()=>parseManualInput('solana',input));
 assert.throws(()=>parseManualInput('unknown',mint));
 assert.equal(parseManualInput('robinhood','https://dexscreener.com/robinhood/0x'+'b'.repeat(64)).type,'pair');
});
test('forming, malformed or impossible candles are excluded; recent gaps cannot become a reentry signal',()=>{
 const rows=candles(),raw={data:{attributes:{ohlcv_list:[...rows,rows[0],[closed+60,1,2,.5,1,2],[closed,2,1,3,2,1]]}}};
 const parsed=parseCandles(raw,now);assert.equal(parsed.length,30);
 assert.equal(chartEvidence(parsed,now).status,'available');
 assert.equal(chartEvidence(parsed.slice(-5),now).status,'insufficient');
 assert.equal(chartEvidence(parsed,now+300).status,'stale');
 assert.equal(chartEvidence(parsed.filter((_,i)=>i<10||i>14),now).status,'gaps');
 assert.equal(manualVerdict(base,{status:'insufficient',reason:'No candles'},'reentry').tone,'gray');
});
test('partial risk and unsupported chains never become an approval, regardless of chart recovery',()=>{
 const chart=chartEvidence(candles(),now);
 assert.equal(manualVerdict({...base,risk:{status:'blocked'}},chart,'reentry').tone,'red');
 assert.equal(manualVerdict({...base,chain_id:'base'},chart,'general').tone,'gray');
 assert.equal(manualVerdict({...base,mint_disabled:null},chart,'general').tone,'gray');
 assert.equal(manualVerdict(base,chart,'reentry').tone,'yellow');
 assert.equal(manualVerdict(base,chart,'general').tone,'blue');
});
test('a new token outside the radar can be analyzed without any radar mutation or notification',async()=>{
 const writes=[],urls=[];
 const pair={chainId:'solana',baseToken:{address:mint,symbol:'MANUAL',name:'Manual'},pairAddress:pool,priceUsd:'1',liquidity:{usd:30000},marketCap:60000,volume:{m5:1000},txns:{m5:{buys:10,sells:5}},priceChange:{m5:1},pairCreatedAt:(now-1200)*1000};
 const db=async(path,body)=>{if(body)writes.push(path);return [];};
 const get=async(url)=>{urls.push(url);if(url.includes('token-pairs'))return [pair];if(url.includes('ohlcv'))return {data:{attributes:{ohlcv_list:candles()}}};throw Error('report unavailable');};
 const rpc=async()=>[{owner:program,data:{parsed:{type:'mint',info:{isInitialized:true,mintAuthority:null,freezeAuthority:null,supply:'1000000',decimals:6}}}}];
 const report=await analyzeManual({chain:'solana',input:mint,objective:'reentry'},db,get,rpc,()=>now);
 assert.equal(report.snapshot.address,mint);assert.equal(report.chart.status,'available');
 assert.equal(report.verdict.tone,'gray');assert.equal(writes.length,0);
 assert.ok(!urls.some(u=>u.includes('telegram')));
 assert.equal(report.snapshot.risk.status,'pending');
});
test('cross-chain or mismatched token data cannot be analyzed as the requested contract',async()=>{
 const pair={chainId:'base',baseToken:{address:'0x'+'a'.repeat(40)},pairAddress:'0x'+'b'.repeat(40)};
 await assert.rejects(()=>analyzeManual({chain:'solana',input:mint,objective:'general'},async()=>[],async()=>[pair],async()=>[],()=>now));
});

test('cached risk is reassessed with fresh chain accounts without leaking cache metadata or querying candles for risk-only focus',async()=>{
 const lp='6'.repeat(32),holder='4'.repeat(32),creator='8'.repeat(32),urls=[];
 const cached={fetched_at:now,secret:'PRIVATE',report:{mint,creator,risks:[],holders:[{address:holder,owner:holder,pct:2}],
  markets:[{address:pool,lp_mint:lp,locked_pct:100,reserve_supply_raw:'1000000',holders:[],pool_accounts:[],pool_owners:[]}]}};
 const pair={chainId:'solana',baseToken:{address:mint,symbol:'MANUAL'},pairAddress:pool,priceUsd:'1',liquidity:{usd:30000},marketCap:60000,volume:{m5:1000},txns:{m5:{buys:10,sells:5}},priceChange:{m5:1},pairCreatedAt:(now-1200)*1000};
 const get=async url=>{urls.push(url);assert.ok(url.includes('token-pairs'));return [pair];};
 const rpc=async addresses=>addresses.map(a=>a===mint?{owner:program,data:{parsed:{type:'mint',info:{isInitialized:true,mintAuthority:null,freezeAuthority:null,supply:'1000000000',decimals:6}}}}:
  a===lp?{owner:program,data:{parsed:{type:'mint',info:{supply:'0'}}}}:{owner:program,data:{parsed:{type:'account',info:{mint,owner:holder,tokenAmount:{amount:'20000000',decimals:6}}}}});
 const result=await analyzeManual({chain:'solana',input:mint,objective:'risk'},async()=>[{report:cached}],get,rpc,()=>now);
 assert.equal(result.snapshot.risk.status,'reviewed');assert.equal(result.verdict.tone,'blue');
 assert.equal(result.chart.status,'not_requested');assert.equal(urls.length,1);
 assert.ok(!JSON.stringify(result).includes('PRIVATE'));assert.equal(result.snapshot.whales.status,'observing');
});
