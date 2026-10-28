// Experimental observations, separate from the unchanged classic market rules.
export const earlyRules={version:'early-v1',min_liquidity:25000,min_spacing_seconds:45,max_gap_seconds:180,
 max_since_first_pct:50,max_change_5m:40,extra_tracked:10};
const num=(v:any)=>typeof v==='number'&&Number.isFinite(v)?v:null;
const change=(a:number,b:number)=>num(a)!==null&&num(b)!==null&&b>0?(a/b-1)*100:null;

export function earlyAssessment(s:any,record:any,now:number){
 const risk=s.risk||{},fresh=num(s.observed_at)!==null&&now-s.observed_at>=0&&now-s.observed_at<=120;
 const checks=[
  {label:'Permissões básicas',state:s.mint_disabled===false||s.freeze_disabled===false?'blocked':s.mint_disabled===true&&s.freeze_disabled===true&&s.extensions_review===false?'met':'unknown'},
  {label:'Liquidez mínima de US$ 25 mil',state:num(s.liquidity)===null?'unknown':s.liquidity>=earlyRules.min_liquidity?'met':'waiting'},
  {label:'Estabilidade observada da liquidez',state:num(s.liquidity)===null?'unknown':record.first_liquidity>0&&s.liquidity<record.first_liquidity*.8||record.last_liquidity>0&&s.liquidity<record.last_liquidity*.8?'blocked':'met'},
  {label:'LP e concentração — triagem parcial',state:risk.status==='blocked'?'blocked':risk.version==='risk-v1'&&risk.status==='reviewed'&&risk.lp_chain_checked===true&&num(risk.checked_at)!==null&&now-risk.checked_at>=0&&now-risk.checked_at<=120?'met':'unknown'},
  {label:'Vendas registradas pelo provedor',state:num(s.sell_count_5m)===null?'unknown':s.sell_count_5m>0?'met':'waiting'}];
 const since=change(s.price,record.first_price),recent=num(s.change_5m);
 const advanced=since!==null&&since>earlyRules.max_since_first_pct||recent!==null&&recent>earlyRules.max_change_5m;
 let status='observing';
 if(checks.some(c=>c.state==='blocked'))status='blocked';
 else if(!fresh||checks.some(c=>c.state==='unknown')||num(s.price)===null||s.price<=0)status='pending';
 else if(advanced)status='extended';
 else if(checks.every(c=>c.state==='met'))status='eligible';
 return {version:earlyRules.version,status,checks,price_since_first_pct:since,
  liquidity_since_first_pct:change(s.liquidity,record.first_liquidity),
  limitation:'Triagem parcial, sem simulação de venda, auditoria de participantes únicos, insiders ou bundles. Não estima segurança, lucro ou ponto de entrada.'};
}

export function observeEarly(state:any,t:any,s:any,now:number){
 state.early_cohorts||={};
 if(s.chain_id!=='solana'||num(s.price)===null||s.price<=0)return null;
 const key=s.address+':'+s.pair_address;
 let record=state.early_cohorts[key];
 if(!record){
  record={id:crypto.randomUUID(),version:earlyRules.version,address:s.address,pair_address:s.pair_address,
   symbol:s.symbol,classic_active_at_start:t.status==='candidate',first_at:now,first_price:s.price,first_liquidity:s.liquidity,first_valuation:s.valuation,
   valuation_type:s.valuation_type,min_price:s.price,max_price:s.price,observations:0,quality_streak:0};
  state.early_cohorts[key]=record;
 }
 const previousAt=record.last_at,previousStatus=record.status;
 const comparable=previousAt&&now-previousAt>=earlyRules.min_spacing_seconds&&now-previousAt<=earlyRules.max_gap_seconds;
 const assessment=earlyAssessment(s,record,now);
 const counted=!previousAt||now-previousAt>=earlyRules.min_spacing_seconds;
 if(counted){
  record.observations++;record.last_at=now;record.last_price=s.price;record.last_liquidity=s.liquidity;
  record.last_valuation=s.valuation;record.min_price=Math.min(record.min_price,s.price);record.max_price=Math.max(record.max_price,s.price);
  record.quality_streak=assessment.status==='eligible'?(comparable?record.quality_streak+1:1):0;
 }
 if(assessment.status!=='eligible')record.quality_streak=0;
 record.status=assessment.status==='eligible'?(record.quality_streak>=2?'reviewed':'observing'):assessment.status;
 record.assessment={...assessment,status:record.status};record.tracking_stopped_at=null;
 if(!record.early_at&&record.status==='reviewed'){
  record.early_at=now;record.early_price=s.price;
  state.alerts.push({id:crypto.randomUUID(),kind:'early_watch',address:s.address,created_at:now,
   reasons:['EXPERIMENTAL — triagem inicial atendida em duas consultas; não é sinal de compra',
    `Variação desde a primeira leitura do teste: ${assessment.price_since_first_pct?.toFixed(1)}%`,
    'Participantes únicos e atividade orgânica não verificados; venda não simulada'],
   snapshot:{...s,early:{id:record.id,first_at:record.first_at,first_price:record.first_price,
    price_since_first_pct:assessment.price_since_first_pct,status:'reviewed'}},delivery:'panel'});
 }
 if(record.early_at&&previousStatus==='reviewed'&&['blocked','pending','extended'].includes(record.status)&&(!record.last_changed_at||now-record.last_changed_at>=600)){
  record.last_changed_at=now;
  state.alerts.push({id:crypto.randomUUID(),kind:'early_changed',address:s.address,created_at:now,
   reasons:['EXPERIMENTAL — a triagem inicial mudou: '+record.status,'Confira os dados atuais; não é instrução de venda'],
   snapshot:{...s,early:{id:record.id,status:record.status}},delivery:'panel'});
 }
 if(!record.classic_at&&t.status==='candidate'&&(!t.last_signal_at||t.last_signal_at>=record.first_at)){
  record.classic_at=now;record.classic_price=s.price;record.classic_since_first_pct=change(s.price,record.first_price);
 }
 for(const [label,seconds] of [['change_15m',900],['change_1h',3600]] as const){
  const age=now-record.first_at;
  if(record[label]===undefined&&age>=seconds&&age<=seconds+180)record[label]={at:now,pct:change(s.price,record.first_price)};
 }
 record.max_rise_pct=change(record.max_price,record.first_price);record.max_drop_pct=change(record.min_price,record.first_price);
 t.early={...record};return record;
}

export function finishEarly(state:any,live:Set<string>,now:number){
 const changed:any[]=[];
 for(const [key,r] of Object.entries<any>(state.early_cohorts||{})){
  if(!live.has(key)&&!r.tracking_stopped_at){r.tracking_stopped_at=now;changed.push(r);}
  if(now-r.first_at>86400)delete state.early_cohorts[key];
 }
 const oldest=Object.entries<any>(state.early_cohorts||{}).sort((a,b)=>a[1].last_at-b[1].last_at);
 for(const [key] of oldest.slice(0,Math.max(0,oldest.length-300)))delete state.early_cohorts[key];
 return changed;
}

export function publicEarly(t:any){
 const r=t.early;if(!r)return null;
 return Object.fromEntries(['id','version','address','pair_address','symbol','first_at','first_price','first_liquidity',
  'first_valuation','valuation_type','classic_active_at_start','last_at','last_price','last_liquidity','last_valuation','observations',
  'status','assessment','early_at','early_price','classic_at','classic_price','classic_since_first_pct',
  'max_rise_pct','max_drop_pct','change_15m','change_1h','tracking_stopped_at'].map(k=>[k,r[k]]));
}
