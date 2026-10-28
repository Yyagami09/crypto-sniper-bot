import {n} from './core.ts';

// Explicit DEX Screener / GeckoTerminal IDs; no user-controlled request hosts.
export const networkCatalog=[
 {id:'robinhood',gecko:'robinhood',name:'Robinhood Chain'},
 {id:'ethereum',gecko:'eth',name:'Ethereum'}, {id:'base',gecko:'base',name:'Base'},
 {id:'bsc',gecko:'bsc',name:'BNB Chain'}, {id:'arbitrum',gecko:'arbitrum',name:'Arbitrum'},
 {id:'polygon',gecko:'polygon_pos',name:'Polygon'}, {id:'avalanche',gecko:'avax',name:'Avalanche'},
 {id:'optimism',gecko:'optimism',name:'Optimism'}];
export const evmAddress=(a:any)=>typeof a==='string'&&/^0x[0-9a-fA-F]{40}$/.test(a);
export const evmPool=(a:any)=>typeof a==='string'&&/^0x(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$/.test(a);
const nonneg=(v:any)=>{const value=n(v);return value!==null&&value>=0?value:null;};

export function networkSnapshot(chain:string,address:string,p:any,now:number){
 if(!networkCatalog.some(c=>c.id===chain)||p?.chainId!==chain||!evmAddress(address)||
  !evmAddress(p?.baseToken?.address)||p.baseToken.address.toLowerCase()!==address.toLowerCase()||!evmPool(p.pairAddress))throw Error('invalid_network_pair');
 const marketCap=nonneg(p.marketCap),fdv=nonneg(p.fdv);
 return {chain_id:chain,address:address.toLowerCase(),profile:'dex-market-observation-v1',
  symbol:String(p.baseToken.symbol||'?').slice(0,30),name:String(p.baseToken.name||'').slice(0,100),
  pair_address:p.pairAddress.toLowerCase(),pair_url:`https://dexscreener.com/${chain}/${p.pairAddress.toLowerCase()}`,
  observed_at:now,price:nonneg(p.priceUsd),liquidity:nonneg(p.liquidity?.usd),
  market_cap:marketCap&&marketCap>0?marketCap:null,fdv:fdv&&fdv>0?fdv:null,
  valuation:marketCap&&marketCap>0?marketCap:fdv&&fdv>0?fdv:null,valuation_type:marketCap&&marketCap>0?'Market cap':'FDV',
  volume_5m:nonneg(p.volume?.m5),buy_count_5m:nonneg(p.txns?.m5?.buys),sell_count_5m:nonneg(p.txns?.m5?.sells),
  change_5m:n(p.priceChange?.m5),pool_created_at:n(p.pairCreatedAt)===null?null:n(p.pairCreatedAt)!/1000,
  mint_disabled:null,freeze_disabled:null,extensions_review:true,
  risk:{status:'unsupported',reasons:['Triagem de risco ainda não adaptada a esta rede. Apenas observação de mercado.']},
  sources:{market:'DEX Screener — principal pool por liquidez',discovery:'GeckoTerminal new pools e perfis recentes do DEX Screener'},
  coverage:['Sem verificações de LP, permissões, grandes carteiras, honeypot ou slow rug nesta rede','Sem confirmação dourada ou alertas automáticos nesta rede']};
}

export async function scanNetwork(network:any,previous:any,get:any,profiles:any[],clock:()=>number,rules:any){
 const started=clock(),issues:string[]=[];
 let tokens:any=Object.fromEntries(Object.entries<any>(previous?.tokens||{}).filter(([a,t])=>evmAddress(a)&&t.snapshot?.chain_id===network.id&&started-t.first_seen<86400));
 const discovered:any[]=[];
 try{
  const response=await get(`https://api.geckoterminal.com/api/v2/networks/${network.gecko}/new_pools`,3000);
  if(!Array.isArray(response.data))throw Error('schema');
  for(const row of response.data){
   const id=row.relationships?.base_token?.data?.id,prefix=network.gecko+'_';
   if(typeof id==='string'&&id.startsWith(prefix)&&evmAddress(id.slice(prefix.length))&&(nonneg(row.attributes?.reserve_in_usd)||0)>=2000)discovered.push(id.slice(prefix.length));
  }
 }catch{issues.push('GeckoTerminal: descoberta indisponível nesta rede');}
 for(const row of profiles)if(row.chainId===network.id&&evmAddress(row.tokenAddress))discovered.push(row.tokenAddress);
 for(const value of discovered){
  const address=value.toLowerCase();if(tokens[address])continue;
  if(Object.keys(tokens).length>=15){
   const oldest=Object.values<any>(tokens).filter(t=>started-t.first_seen>1800).sort((a,b)=>a.first_seen-b.first_seen)[0];
   if(!oldest)continue;delete tokens[oldest.address];
  }
  tokens[address]={address,chain_id:network.id,first_seen:started,last_checked:0,status:'queued',snapshot:null,history:[],reasons:[]};
 }
 const addresses=Object.keys(tokens).slice(0,15);let checked=0;
 if(addresses.length){
  try{
   const pairs=await get(`https://api.dexscreener.com/tokens/v1/${network.id}/${addresses.join(',')}`,3000);
   if(!Array.isArray(pairs))throw Error('schema');
   const byToken:any={};
   for(const pair of pairs){
    const a=pair.baseToken?.address?.toLowerCase();
    if(pair.chainId!==network.id||!addresses.includes(a))continue;
    if(!byToken[a]||(nonneg(pair.liquidity?.usd)||0)>(nonneg(byToken[a].liquidity?.usd)||0))byToken[a]=pair;
   }
   for(const a of addresses){
    const token=tokens[a];
    try{
     const snapshot=networkSnapshot(network.id,a,byToken[a],clock());
     const changed=token.snapshot&&token.snapshot.pair_address!==snapshot.pair_address;
     token.history=[...(changed?[]:token.history||[]),{observed_at:snapshot.observed_at,price:snapshot.price}].slice(-30);
     token.snapshot=snapshot;token.last_checked=snapshot.observed_at;token.status='watch';
     token.reasons=['Observação de mercado; triagem de risco indisponível nesta rede'];checked++;
    }catch{token.status='incomplete';token.reasons=['Pool indisponível nesta consulta; valores anteriores não são uma leitura nova'];}
   }
  }catch{issues.push('DEX Screener: dados de mercado indisponíveis nesta rede');for(const t of Object.values<any>(tokens))t.status='incomplete';}
 }
 tokens=Object.fromEntries(Object.entries<any>(tokens).filter(([,t])=>t.snapshot));
 return {chain_id:network.id,tokens,alerts:[],backoff_until:0,run:{started_at:started,completed_at:clock(),checked,
  status:issues.length?'partial':'ok',source_errors:issues,engine:'dex-market-observation',demo:false,
  rules:{...rules,profile:'dex-market-observation-v1',max_tracked:15,risk_policy:'unavailable'}}};
}

export async function collectNetworks(state:any,get:any,profiles:any[],clock:()=>number,started:number,rules:any){
 state.networks||={};
 const ordered=[...networkCatalog].sort((a,b)=>(state.networks[a.id]?.run?.completed_at||0)-(state.networks[b.id]?.run?.completed_at||0));
 // Small batches keep free endpoints bounded. Primary Solana alerts are already sent.
 for(let i=0;i<ordered.length;i+=2){
  if(clock()-started>85)break;
  const batch=ordered.slice(i,i+2);
  const results=await Promise.allSettled(batch.map(c=>scanNetwork(c,state.networks[c.id],get,profiles,clock,rules)));
  results.forEach((result,index)=>{if(result.status==='fulfilled')state.networks[batch[index].id]=result.value;});
 }
}

export function publicNetworks(state:any,rules:any){
 const feeds:any={};
 for(const c of networkCatalog){
  const source=state.networks?.[c.id];if(!source)continue;
  const tokens:any={};
  for(const [a,t] of Object.entries<any>(source.tokens||{}).slice(0,15)){
   if(!evmAddress(a)||t.snapshot?.chain_id!==c.id||t.snapshot?.profile!=='dex-market-observation-v1')continue;
   // Rebuild from known fields only; never forward cached metadata or raw reports.
   const s=t.snapshot;
   tokens[a]={address:a,chain_id:c.id,first_seen:t.first_seen,last_checked:t.last_checked,
    status:t.status==='watch'?'watch':'incomplete',reasons:t.reasons,
    history:(t.history||[]).slice(-30).map((h:any)=>({observed_at:h.observed_at,price:h.price})),
    snapshot:{...Object.fromEntries(['chain_id','address','profile','symbol','name','pair_address','pair_url',
     'observed_at','price','liquidity','market_cap','fdv','valuation','valuation_type','volume_5m',
     'buy_count_5m','sell_count_5m','change_5m','pool_created_at'].map(k=>[k,s[k]])),
     mint_disabled:null,freeze_disabled:null,extensions_review:true,
     risk:{status:'unsupported',reasons:['Triagem de risco ainda não adaptada a esta rede. Apenas observação de mercado.']}}};
  }
  const r=source.run||{};
  feeds[c.id]={chain_id:c.id,tokens,alerts:[],run:{status:r.status,started_at:r.started_at,completed_at:r.completed_at,
   checked:r.checked,source_errors:r.source_errors||[],engine:'dex-market-observation',demo:false,
   rules:{...rules,profile:'dex-market-observation-v1',max_tracked:15,risk_policy:'unavailable'}}};
 }
 return feeds;
}
