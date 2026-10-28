import {n,validAddress,event} from './core.ts';
import {riskRules} from './risk.ts';
export const freeRules={profile:'free-market-v1',interval_seconds:60,max_tracked:30,
 min_liquidity:25000,min_valuation:100000,max_valuation:10000000,min_pool_age_minutes:15,
 max_pool_age_minutes:10080,min_volume_5m:5000,min_transactions_5m:10,
 min_buy_sell_count_ratio:1.2,min_change_5m:2,max_change_5m:40,
 confirmation_min_seconds:240,confirmation_max_seconds:1200,liquidity_drop:.20,risk_policy:riskRules.version,risk_limits:riskRules};
export const coverage=['RugCheck pode retornar relatório em cache; concentração reportada não é auditoria completa',
 'Insiders, bundles e wash trading não auditados','Venda não simulada; preço consultado não é cotação de execução',
 'Movimentos de grandes detentores são variações de saldo de uma amostra, não compras/vendas comprovadas'];
const nn=(x:any)=>{const v=n(x);return v!==null&&v>=0?v:null;};
export function mintCheck(account:any){
 const allowedOwners=['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'];
 const parsed=account?.data?.parsed,info=parsed?.info;
 if(!allowedOwners.includes(account?.owner)||parsed?.type!=='mint'||!info||info.isInitialized!==true)
  return {mint_disabled:null,freeze_disabled:null,extensions_review:true};
 const extensions=info.extensions||[];
 const review=!Array.isArray(extensions)||extensions.some((e:any)=>!['metadataPointer','tokenMetadata'].includes(e.extension));
 return {mint_disabled:Object.hasOwn(info,'mintAuthority')?info.mintAuthority===null:null,
 freeze_disabled:Object.hasOwn(info,'freezeAuthority')?info.freezeAuthority===null:null,extensions_review:review};
}
export function fromDex(a:string,p:any,account:any,now:number){
 if(!p||p.chainId!=='solana'||p.baseToken?.address!==a||!validAddress(a)||!validAddress(p.pairAddress))throw new Error('invalid_pair');
 const check=mintCheck(account),price=nn(p.priceUsd),mc=nn(p.marketCap),fdv=nn(p.fdv);
 const created=n(p.pairCreatedAt);
 return {address:a,symbol:String(p.baseToken.symbol||'?').slice(0,30),name:String(p.baseToken.name||'').slice(0,100),
 profile:'free-market-v1',pair_address:p.pairAddress,pair_url:`https://dexscreener.com/solana/${p.pairAddress}`,
 observed_at:now,price:price&&price>0?price:null,liquidity:nn(p.liquidity?.usd),
 market_cap:mc&&mc>0?mc:null,fdv:fdv&&fdv>0?fdv:null,
 valuation:mc&&mc>0?mc:fdv&&fdv>0?fdv:null,valuation_type:mc&&mc>0?'Market cap':'FDV',
 pool_created_at:created!==null?created/1000:null,volume_5m:nn(p.volume?.m5),
 base_reserve:nn(p.liquidity?.base),quote_reserve:nn(p.liquidity?.quote),
 buy_count_5m:nn(p.txns?.m5?.buys),sell_count_5m:nn(p.txns?.m5?.sells),change_5m:n(p.priceChange?.m5),
 supply_raw:account?.data?.parsed?.info?.supply,token_decimals:account?.data?.parsed?.info?.decimals,
 ...check,coverage:[...coverage],sources:{market:'DEX Screener — principal pool por liquidez',
 permissions:account?'Solana RPC público / getMultipleAccounts':'Solana RPC indisponível',discovery:'GeckoTerminal new pools e perfis recentes do DEX Screener'}};
}
export function evaluateFree(s:any,prev:any,now:number){
 const required=['price','liquidity','valuation','pool_created_at','volume_5m','buy_count_5m','sell_count_5m','change_5m','mint_disabled','freeze_disabled'];
 const missing=required.filter(k=>s[k]===null||s[k]===undefined),blocked=[];
 if(s.mint_disabled===false)blocked.push('Permissão de emissão adicional ainda habilitada');
 if(s.freeze_disabled===false)blocked.push('Permissão de congelamento ainda habilitada');
 if(prev?.liquidity>0&&s.liquidity!==null&&s.liquidity<prev.liquidity*(1-freeRules.liquidity_drop))blocked.push('Queda relevante de liquidez entre consultas');
 if(s.risk?.version===riskRules.version&&s.risk.status==='blocked')blocked.push(...s.risk.reasons);
 if(blocked.length)return {status:'blocked',reasons:blocked,missing};
 if(s.risk?.version!==riskRules.version||s.risk.status!=='reviewed'||s.risk.lp_chain_checked!==true||typeof s.risk.checked_at!=='number'||!Number.isFinite(s.risk.checked_at)||now-s.risk.checked_at>1200||s.risk.checked_at>now+30)
  return {status:'incomplete',reasons:s.risk?.reasons?.length?s.risk.reasons:['Camada de risco pendente: LP, concentração e alertas externos ainda não verificados'],missing:[...missing,'risk_review']};
 if(s.extensions_review)missing.push('token_program_or_extensions');
 if(missing.length)return {status:'incomplete',reasons:['Verificação parcial pendente: '+missing.join(', ')],missing};
 const age=(now-s.pool_created_at)/60,reasons=[];
 if(age<0||s.pool_created_at<=0)return {status:'incomplete',reasons:['Data da pool inválida'],missing:['pool_created_at']};
 if(age<freeRules.min_pool_age_minutes||age>freeRules.max_pool_age_minutes)reasons.push('Idade da pool fora da janela');
 if(s.liquidity<freeRules.min_liquidity)reasons.push('Liquidez abaixo do mínimo');
 if(s.valuation<freeRules.min_valuation||s.valuation>freeRules.max_valuation)reasons.push('Avaliação de mercado fora da faixa');
 if(s.volume_5m<freeRules.min_volume_5m)reasons.push('Volume de 5 minutos abaixo do mínimo');
 if(s.buy_count_5m+s.sell_count_5m<freeRules.min_transactions_5m)reasons.push('Poucas transações em 5 minutos');
 if(s.sell_count_5m<=0||s.buy_count_5m/s.sell_count_5m<freeRules.min_buy_sell_count_ratio)reasons.push('Relação de quantidade de compras/vendas insuficiente');
 if(s.change_5m<freeRules.min_change_5m||s.change_5m>freeRules.max_change_5m)reasons.push('Variação de preço fora da faixa');
 return {status:reasons.length?'watch':'qualified',reasons:reasons.length?reasons:['Movimento passou pelos filtros gratuitos; avaliação de risco parcial'],missing:[]};
}
export function applyFree(state:any,t:any,s:any,now:number){
 const changed=t.snapshot&&t.snapshot.pair_address!==s.pair_address;
 if(changed)t.qualified_at=0;
 const v=evaluateFree(s,changed?null:t.snapshot,now),old=t.status,previousCheck=t.last_checked;
 t.snapshot=s;t.last_checked=now;t.reasons=v.reasons;t.missing=v.missing;
 t.history=[...(t.history||[]),{observed_at:now,price:s.price,liquidity:s.liquidity,volume_5m:s.volume_5m}].slice(-60);
 if(v.status==='qualified'){
  // Keep the initial qualifying observation across fast scans; resetting it on
  // every minute would prevent reaching the four-minute confirmation window.
  const gap=previousCheck?now-previousCheck:Infinity;
  if(!t.qualified_at||gap>freeRules.confirmation_max_seconds||now-t.qualified_at>freeRules.confirmation_max_seconds&&old!=='candidate')t.qualified_at=now;
  const dt=now-t.qualified_at;
  t.status=old==='candidate'&&!changed&&gap<=freeRules.confirmation_max_seconds||dt>=freeRules.confirmation_min_seconds&&dt<=freeRules.confirmation_max_seconds?'candidate':'confirming';
  if(t.status==='candidate')t.qualified_at=now;
  if(t.status==='candidate'&&old!=='candidate'){t.last_signal_at=now;event(state,t,'candidate',v.reasons,now);}
 }else{
  t.status=v.status;t.qualified_at=0;
  if(old==='candidate')event(state,t,v.status==='incomplete'?'data_gap':'conditions_lost',v.reasons,now);
 }
}
export function updateOutcomes(state:any,now:number){
 for(const a of state.alerts||[]){
  if(a.kind!=='candidate'||a.snapshot?.profile!=='free-market-v1')continue;
  const current=state.tokens[a.address]?.snapshot;
  if(!current?.price||!a.snapshot.price||now-current.observed_at>600||current.pair_address!==a.snapshot.pair_address)continue;
  a.observations??={};
  for(const [label,seconds] of [['15min',900],['1h',3600]] as const){
   const elapsed=current.observed_at-a.created_at;
   if(!a.observations[label]&&elapsed>=seconds&&elapsed<=seconds+600)
    a.observations[label]={observed_at:current.observed_at,change_percent:(current.price/a.snapshot.price-1)*100};
  }
 }
}
// This feed contains public market data only; private state and delivery details stay private.
export function publicFeed(state:any){
 const run=state.run||{};
 const snapshot=(s:any)=>Object.fromEntries(['address','symbol','name','profile','pair_address','pair_url',
  'observed_at','price','liquidity','market_cap','fdv','valuation','valuation_type','pool_created_at',
  'volume_5m','buy_count_5m','sell_count_5m','change_5m','mint_disabled','freeze_disabled',
  'extensions_review','coverage','sources','risk','whales'].map(k=>[k,s[k]]));
 const tokens:any={};
 for(const [a,t] of Object.entries<any>(state.tokens||{})){
  if(t.snapshot?.profile!=='free-market-v1')continue;
  tokens[a]={address:a,first_seen:t.first_seen,last_checked:t.last_checked,status:t.status,
   snapshot:snapshot(t.snapshot),reasons:t.reasons,missing:t.missing,
   history:(t.history||[]).map((h:any)=>({observed_at:h.observed_at,price:h.price,liquidity:h.liquidity,volume_5m:h.volume_5m}))};
 }
 return {version:2,profile:'free-market-v1',tokens,alerts:(state.alerts||[])
  .filter((a:any)=>a.snapshot?.profile==='free-market-v1').slice(-100)
  .map((a:any)=>({id:a.id,address:a.address,kind:a.kind,created_at:a.created_at,reasons:a.reasons,
    snapshot:snapshot(a.snapshot),observations:a.observations||{},delivery:'panel'})),
  run:{status:run.status,started_at:run.started_at,completed_at:run.completed_at,checked:run.checked,
    errors:run.errors,engine:'supabase-free-market',demo:false,rules:freeRules,
    source_errors:run.source_errors||[],telegram_configured:!!run.telegram_configured},backoff_until:state.backoff_until||0};
}
