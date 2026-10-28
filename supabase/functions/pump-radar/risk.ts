import {validAddress,n} from './core.ts';
import {whaleTargets,observeWhales,isPoolHolder} from './whales.ts';
import {liquidityTrend} from './trends.ts';

export const riskRules={version:'risk-v1',min_lp_locked_pct:90,max_top10_ex_pool_pct:50,
 max_creator_lp_pct:10,max_volume_liquidity_5m:10,report_ttl_seconds:1800,reports_per_cycle:10};
const rawSupply=(x:any)=>typeof x==='string'&&/^\d+$/.test(x)?x:Number.isSafeInteger(x)&&x>=0?String(x):null;
const programs=['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'];
const pct=(x:any)=>{const v=n(x);return v!==null&&v>=0&&v<=100?v:null;};

// Never publish/cache the raw response, foreign metadata, URLs or creator history.
export function cleanReport(raw:any,address:string){
 if(raw?.mint!==address||!Array.isArray(raw.risks)||!Array.isArray(raw.markets)||!Array.isArray(raw.topHolders))throw new Error('invalid_risk_report');
 return {mint:address,creator:validAddress(raw.creator)?raw.creator:null,
  risks:raw.risks.slice(0,30).map((r:any)=>({name:String(r.name||'Risco reportado').slice(0,120),level:r.level})),
  holders:raw.topHolders.slice(0,30).map((h:any)=>({address:h.address,owner:h.owner,pct:pct(h.pct)})),
  markets:raw.markets.slice(0,30).map((m:any)=>({address:m.pubkey,lp_mint:m.lp?.lpMint,
   pool_accounts:[m.liquidityA,m.liquidityB].filter(validAddress),
   pool_owners:[m.liquidityAAccount?.owner,m.liquidityBAccount?.owner].filter(validAddress),
   reserve_supply_raw:rawSupply(m.lp?.reserveSupply),
   locked_pct:pct(m.lp?.lpLockedPct),holders:(m.lp?.holders||[]).slice(0,3).map((h:any)=>({address:h.address,owner:h.owner}))}))};
}

export function lpAccounts(report:any,pair:string){
 const market=report?.markets?.find((m:any)=>m.address===pair);
 return market?[market.lp_mint,...market.holders.map((h:any)=>h.address)].filter(validAddress):[];
}

export function assessRisk(s:any,cached:any,accounts:Map<string,any>,now:number){
 const reasons:string[]=[],pending:string[]=[],warnings:string[]=[];
 const ratio=s.liquidity>0&&n(s.volume_5m)!==null?s.volume_5m/s.liquidity:null;
 const out:any={version:riskRules.version,status:'pending',checked_at:now,
  report_fetched_at:cached?.fetched_at||null,report_source:'RugCheck — resposta pode estar em cache',
  lp_locked_pct:null,creator_lp_pct:null,creator_pool_claim_pct:null,top10_ex_pool_pct:null,volume_liquidity_5m:ratio,
  lp_chain_checked:false,sell_check:'not_simulated',reasons,warnings};
 if(ratio!==null&&ratio>riskRules.max_volume_liquidity_5m)
  reasons.push(`Atividade atípica: volume de 5 min equivale a ${ratio.toFixed(1)}× a liquidez (limite experimental ${riskRules.max_volume_liquidity_5m}×; não comprova manipulação)`);
 else if(ratio!==null&&ratio>5)warnings.push('Giro de volume elevado em relação à liquidez; atividade automatizada não foi auditada');
 if(!cached||now-cached.fetched_at>riskRules.report_ttl_seconds||cached.fetched_at>now+30){
  pending.push('Relatório de risco indisponível ou aguardando atualização');
 }else{
  const r=cached.report,market=r.markets.find((m:any)=>m.address===s.pair_address);
  for(const flag of r.risks){
   if(flag.level==='danger')reasons.push('Alerta crítico do RugCheck: '+flag.name);
   else if(flag.level==='warn')warnings.push('RugCheck: '+flag.name);
  }
  const externalHolders=r.holders.filter((h:any)=>!isPoolHolder(r,h));
  if(!externalHolders.length||externalHolders.some((h:any)=>h.pct===null||!validAddress(h.owner)))pending.push('Concentração por carteira sem dados suficientes');
  else{
   const owners:any={};for(const h of externalHolders)owners[h.owner]=(owners[h.owner]||0)+h.pct;
   const concentration=Object.values<number>(owners).sort((a,b)=>b-a).slice(0,10).reduce((a,b)=>a+b,0);
   out.top10_ex_pool_pct=concentration;
   if(concentration>riskRules.max_top10_ex_pool_pct)reasons.push(`Concentração reportada fora das pools: Top 10 com ${concentration.toFixed(1)}% (limite ${riskRules.max_top10_ex_pool_pct}%)`);
  }
  if(!market||!validAddress(market.lp_mint)||market.locked_pct===null)pending.push('Proteção da LP da pool selecionada não verificada');
  else{
   out.lp_locked_pct=market.locked_pct;
   if(market.locked_pct<riskRules.min_lp_locked_pct)reasons.push(`LP sem proteção suficiente: ${market.locked_pct.toFixed(1)}% reportada como travada/queimada (mínimo ${riskRules.min_lp_locked_pct}%)`);
   const mint=accounts.get(market.lp_mint),info=mint?.data?.parsed?.info;
   if(!programs.includes(mint?.owner)||mint?.data?.parsed?.type!=='mint'||!/^\d+$/.test(info?.supply||''))pending.push('Consulta atual do token de LP indisponível');
   else if(!r.creator)pending.push('Criador do token não identificado no relatório');
   else{
    let owned=0n,complete=true;
    for(const h of market.holders){
     if(!validAddress(h.address)||!accounts.has(h.address)){complete=false;continue;}
     const account=accounts.get(h.address);
     if(account===null)continue; // Closed account: confirmed non-existent on chain.
     const a=account?.data?.parsed?.info;
     if(!programs.includes(account?.owner)||account?.data?.parsed?.type!=='account'||a?.mint!==market.lp_mint||!/^\d+$/.test(a?.tokenAmount?.amount||'')){complete=false;continue;}
     if(a.owner===r.creator)owned+=BigInt(a.tokenAmount.amount);
    }
    const supply=BigInt(info.supply);
    if(!complete||owned>supply||supply>0n&&!market.holders.length)pending.push('Controle atual da LP sem dados suficientes');
    else{
     out.lp_chain_checked=true;
     out.lp_supply_raw=info.supply;
     out.creator_lp_pct=supply?Number(owned*10000n/supply)/100:0;
     const reported=market.reserve_supply_raw?BigInt(market.reserve_supply_raw):null;
     const denominator=reported!==null?(reported>supply?reported:supply):market.locked_pct<=1?supply:null;
     if(supply===0n)out.creator_pool_claim_pct=0;
     else if(denominator&&denominator>0n)out.creator_pool_claim_pct=Number(owned*10000n/denominator)/100;
     else pending.push('Oferta de referência da LP indisponível para estimar participação na pool');
     if(out.creator_pool_claim_pct>riskRules.max_creator_lp_pct)reasons.push(`Criador detém participação estimada de ${out.creator_pool_claim_pct.toFixed(1)}% na oferta de referência da LP; saldo atual verificado na Solana (limite ${riskRules.max_creator_lp_pct}%)`);
    }
   }
  }
 }
 out.status=reasons.length?'blocked':pending.length?'pending':'reviewed';
 out.reasons=[...reasons,...pending];
 return out;
}

export async function enrichRisks(snapshots:any[],state:any,get:any,rpc:any,clock:()=>number,started:number){
 state.risk_reports||={};
 const live=new Set(snapshots.map(s=>s.address));
 for(const a of Object.keys(state.risk_reports))if(!live.has(a))delete state.risk_reports[a];
 // Requests are serialized and bounded to stay conservative on the free API.
 const ordered=[...snapshots].sort((a,b)=>(b.volume_5m||0)-(a.volume_5m||0));
 let attempted=0;
 for(const s of ordered){
  const old=state.risk_reports[s.address];
  const needs=!old||clock()-old.fetched_at>riskRules.report_ttl_seconds||!old.report.markets.some((m:any)=>m.address===s.pair_address);
  if(!needs||attempted>=riskRules.reports_per_cycle||clock()-started>65)continue;
  attempted++;
  try{const report=cleanReport(await get(`https://api.rugcheck.xyz/v1/tokens/${s.address}/report`),s.address);state.risk_reports[s.address]={fetched_at:clock(),report};}catch{/* Remains pending, never becomes a pass on a timeout. */}
  await new Promise(resolve=>setTimeout(resolve,700));
 }
 const addresses=[...new Set(snapshots.flatMap(s=>[...lpAccounts(state.risk_reports[s.address]?.report,s.pair_address),
  ...whaleTargets(state.risk_reports[s.address]?.report).map((h:any)=>h.address)]))];
 const accounts=new Map<string,any>();
 for(let i=0;i<addresses.length;i+=100){
  if(clock()-started>85)break;
  const batch=addresses.slice(i,i+100);
  try{const values=await rpc(batch);if(values.length!==batch.length)throw new Error('rpc_schema');batch.forEach((a,ix)=>accounts.set(a,values[ix]));}catch{/* Independent mint/freeze checks cannot stand in for LP validation. */}
 }
 for(const s of snapshots){
  s.risk=assessRisk(s,state.risk_reports[s.address],accounts,clock());
  s.risk.slow_rug=liquidityTrend(s,s.risk,state,clock());
  if(s.risk.slow_rug.status==='warning'){
   s.risk.status='blocked';
   s.risk.reasons.push('Padrão compatível com retirada gradual de liquidez: redução persistente de LP e das duas reservas em várias consultas. Heurística experimental; não comprova rug pull.');
  }
  s.whales=observeWhales(s,state.risk_reports[s.address]?.report,accounts,state,clock());
 }
 if(state.whale_observations)for(const a of Object.keys(state.whale_observations))if(!live.has(a))delete state.whale_observations[a];
 if(state.liquidity_trends)for(const a of Object.keys(state.liquidity_trends))if(!live.has(a))delete state.liquidity_trends[a];
}
