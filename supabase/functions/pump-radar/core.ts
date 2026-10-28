// Read-only screening. Numbers below are experimental criteria, not probabilities.
export const rules = {min_liquidity:25000,min_market_cap:100000,max_market_cap:10000000,
 min_age_minutes:15,max_age_minutes:10080,min_holders:150,max_top10:.30,max_rug:.30,
 max_bundler:.20,max_insider:.20,min_volume_5m:10000,min_buy_sell_ratio:1.2,
 min_change_5m:2,max_change_5m:40,liquidity_drop:.20,cooldown_seconds:1800,
 confirmation_min_seconds:30,confirmation_max_seconds:600,interval_seconds:60,
 batch_size:6,max_tracked:30,retention_hours:24};
export const n=(v:any):number|null=>v===null||v===undefined||v===''||typeof v==='boolean'||typeof v==='object'||!Number.isFinite(Number(v))?null:Number(v);
export const flag=(v:any)=>[true,1,'1','true','yes'].includes(v)?true:[false,0,'0','false','no'].includes(v)?false:null;
export const ratio=(v:any)=>{const x=n(v);return x!==null&&x>=0&&x<=1?x:null;};
export const validAddress=(a:any)=>typeof a==='string'&&/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(a);
export function normalize(a:string,i:any,s:any,d:any,now:number) {
 if(i?.address!==a||!i.price||typeof i.price!=='object')throw new Error('schema_changed');
 const p=n(i.price.price),p5=n(i.price.price_5m),supply=n(i.circulating_supply);
 const stat=i.stat||{},sources:any={market:'token/info',permissions:'token/security'};
 const risk=(field:string,statField:string,rankField:string)=>{
   const sec=ratio(s[field]);if(sec!==null)return sec;
   const st=ratio(stat[statField]);if(st!==null){sources[field]='token/info.stat';return st;}
   const rk=d&&now-d.observed_at<=120&&now>=d.observed_at?ratio(d[rankField]):null;
   if(rk!==null)sources[field]={route:'market discovery',observed_at:d.observed_at};
   return rk;
 };
 const nonneg=(x:any)=>{const v=n(x);return v!==null&&v>=0?v:null;};
 const wash=flag(s.is_wash_trading);
 return {address:a,symbol:String(i.symbol||'?').slice(0,30),name:String(i.name||'').slice(0,100),
 observed_at:now,price:p&&p>0?p:null,market_cap:p&&supply&&p>0&&supply>0?p*supply:null,
 liquidity:nonneg(i.liquidity),holders:nonneg(i.holder_count),created_at:n(i.creation_timestamp),
 launchpad_status:n(i.launchpad_status),volume_5m:nonneg(i.price.volume_5m),
 buy_volume_5m:nonneg(i.price.buy_volume_5m),sell_volume_5m:nonneg(i.price.sell_volume_5m),
 change_5m:p&&p5&&p>0&&p5>0?(p/p5-1)*100:null,
 top10:ratio(s.top_10_holder_rate),rug:risk('rug_ratio','','rug_ratio'),
 bundler:risk('bundler_trader_amount_rate','top_bundler_trader_percentage','bundler_rate'),
 insider:risk('rat_trader_amount_rate','top_rat_trader_percentage','rat_trader_amount_rate'),
 mint_disabled:flag(s.renounced_mint),freeze_disabled:flag(s.renounced_freeze_account),
 wash_trading:wash!==null?wash:(d&&now-d.observed_at<=120&&now>=d.observed_at?flag(d.is_wash_trading):null),
 burn_status:s.burn_status||'não informado',smart_wallets:n(i.wallet_tags_stat?.smart_wallets),sources};
}
export function evaluate(s:any,previous:any,now:number) {
 const required=['price','market_cap','liquidity','holders','created_at','volume_5m','buy_volume_5m',
 'sell_volume_5m','change_5m','top10','rug','bundler','insider','mint_disabled','freeze_disabled','wash_trading'];
 const missing=required.filter(k=>s[k]===null||s[k]===undefined),blocked=[];
 if(s.mint_disabled===false)blocked.push('Emissão adicional habilitada');
 if(s.freeze_disabled===false)blocked.push('Congelamento habilitado');
 if(s.wash_trading===true)blocked.push('Negociação artificial sinalizada pelo provedor');
 for(const [key,limit] of Object.entries({top10:rules.max_top10,rug:rules.max_rug,bundler:rules.max_bundler,insider:rules.max_insider}))
  if(s[key]!==null&&s[key]>limit)blocked.push(`${key}: acima do limite`);
 if(previous?.liquidity>0&&s.liquidity!==null&&s.liquidity<previous.liquidity*(1-rules.liquidity_drop))blocked.push('Queda relevante de liquidez entre consultas');
 if(blocked.length)return {status:'blocked',reasons:blocked,missing};
 if(missing.length)return {status:'incomplete',reasons:['Dados obrigatórios ausentes: '+missing.join(', ')],missing};
 const age=(now-s.created_at)/60,reasons=[];
 if(s.created_at<=0||age<0)return {status:'incomplete',reasons:['Data de criação inválida'],missing:['created_at']};
 if(age<rules.min_age_minutes||age>rules.max_age_minutes)reasons.push('Idade fora da janela');
 if([0,1].includes(s.launchpad_status))reasons.push('Lançamento ainda não migrado');
 if(s.liquidity<rules.min_liquidity)reasons.push('Liquidez abaixo do mínimo');
 if(s.market_cap<rules.min_market_cap||s.market_cap>rules.max_market_cap)reasons.push('Valor de mercado fora da faixa');
 if(s.holders<rules.min_holders)reasons.push('Holders abaixo do mínimo');
 if(s.volume_5m<rules.min_volume_5m)reasons.push('Volume de 5 minutos abaixo do mínimo');
 if(s.sell_volume_5m<=0||s.buy_volume_5m/s.sell_volume_5m<rules.min_buy_sell_ratio)reasons.push('Relação de volumes insuficiente ou sem vendas observadas');
 if(s.change_5m<rules.min_change_5m||s.change_5m>rules.max_change_5m)reasons.push('Variação de 5 minutos fora da faixa');
 return {status:reasons.length?'watch':'qualified',reasons:reasons.length?reasons:['Passou pelos filtros configurados; sinal experimental'],missing:[]};
}
export function event(state:any,t:any,kind:string,reasons:string[],now:number) {
 t.last_alert??={};if(now-(t.last_alert[kind]||0)<rules.cooldown_seconds)return;
 t.last_alert[kind]=now;
 state.alerts.push({id:crypto.randomUUID(),address:t.address,kind,created_at:now,reasons,
 snapshot:t.snapshot||{},demo:false,delivery:'pending',attempts:0});
}
export function apply(state:any,t:any,s:any,now:number) {
 const v=evaluate(s,t.snapshot,now),old=t.status;
 t.snapshot=s;t.last_checked=now;t.reasons=v.reasons;t.missing=v.missing;
 t.history=[...(t.history||[]),{observed_at:now,price:s.price,liquidity:s.liquidity,holders:s.holders,volume_5m:s.volume_5m,top10:s.top10}].slice(-30);
 if(v.status==='qualified'){
  const dt=now-(t.qualified_at||0);
  t.status=t.qualified_at&&dt>=rules.confirmation_min_seconds&&dt<=rules.confirmation_max_seconds?'candidate':'confirming';
  t.qualified_at=now;
  if(t.status==='candidate'&&old!=='candidate'){t.last_signal_at=now;event(state,t,'candidate',v.reasons,now);}
 }else{
  t.status=v.status;t.qualified_at=0;
  if(old==='candidate')event(state,t,v.status==='incomplete'?'data_gap':'conditions_lost',v.reasons,now);
 }
}
