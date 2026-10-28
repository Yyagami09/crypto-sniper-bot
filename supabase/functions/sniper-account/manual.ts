import {ApiError} from './core.ts';
import {validAddress,n} from '../pump-radar/core.ts';
import {fromDex} from '../pump-radar/free-core.ts';
import {networkCatalog,evmAddress,evmPool,networkSnapshot} from '../pump-radar/networks.ts';
import {cleanReport,lpAccounts,assessRisk} from '../pump-radar/risk.ts';
import {whaleTargets,observeWhales} from '../pump-radar/whales.ts';

export const manualNetworks=[{id:'solana',gecko:'solana',name:'Solana'},...networkCatalog];
export function parseManualInput(chain:any,input:any){
 if(!manualNetworks.some(c=>c.id===chain)||typeof input!=='string'||input.length>300)throw new ApiError('invalid_contract');
 let address=input.trim(),type='token';
 if(address.startsWith('http')){
  let url:URL;try{url=new URL(address);}catch{throw new ApiError('invalid_contract');}
  const parts=url.pathname.split('/').filter(Boolean);
  if(url.protocol!=='https:'||!['dexscreener.com','www.dexscreener.com'].includes(url.hostname)||url.username||url.password||parts.length!==2||parts[0]!==chain)throw new ApiError('invalid_contract');
  address=parts[1];type='pair';
 }
 const valid=chain==='solana'?validAddress(address):type==='pair'?evmPool(address):evmAddress(address);
 if(!valid)throw new ApiError('invalid_contract');
 return {chain,address:chain==='solana'?address:address.toLowerCase(),type};
}

export function parseCandles(raw:any,now:number){
 const list=raw?.data?.attributes?.ohlcv_list;
 if(!Array.isArray(list))return [];
 const byTime=new Map<number,number[]>(),lastClosed=Math.floor(now/60)*60-60;
 for(const row of list.slice(0,100)){
  if(!Array.isArray(row)||row.length<6||row.slice(0,6).some(x=>typeof x!=='number'||!Number.isFinite(x)))continue;
  const [at,o,h,l,c,v]=row;
  if(!Number.isInteger(at)||at%60||at>lastClosed||now-at>7200||Math.min(o,h,l,c)<=0||h<Math.max(o,l,c)||l>Math.min(o,h,c)||v<0)continue;
  byTime.set(at,[at,o,h,l,c,v]);
 }
 return [...byTime.values()].sort((a,b)=>a[0]-b[0]).slice(-60);
}

export function chartEvidence(candles:number[][],now:number){
 if(candles.length<20)return {status:'insufficient',candles,reason:'Menos de 20 candles completos de um minuto disponíveis.'};
 if(now-candles.at(-1)![0]>180)return {status:'stale',candles,reason:'O histórico de candles está sem leitura recente.'};
 if(candles.slice(1).some((r,i)=>r[0]-candles[i][0]>180))return {status:'gaps',candles,reason:'O histórico apresenta lacunas maiores que três minutos.'};
 const window=candles.slice(-30),prior=window.slice(0,-3),last=window.at(-1)!;
 const lower=Math.min(...prior.map(r=>r[3])),upper=Math.max(...prior.map(r=>r[2])),peak=Math.max(...window.map(r=>r[2]));
 const recent=window.slice(-3),higherLows=recent[1][3]>recent[0][3]&&recent[2][3]>recent[1][3];
 const previousVolume=window.slice(-10,-5).reduce((sum,r)=>sum+r[5],0),recentVolume=window.slice(-5).reduce((sum,r)=>sum+r[5],0);
 return {status:'available',candles,window_minutes:(last[0]-window[0][0])/60+1,last_close:last[4],
  lower_reference:lower,upper_reference:upper,higher_lows_last3:higherLows,close_above_prior_high:last[4]>upper,
  change_from_window_high_pct:(last[4]/peak-1)*100,volume_last5_vs_prior5:previousVolume>0?recentVolume/previousVolume:null,
  reason:'Referências descritivas dos candles consultados; não confirmam suporte, resistência ou execução favorável.'};
}

export function manualVerdict(s:any,chart:any,objective:string){
 if(s.mint_disabled===false||s.freeze_disabled===false||s.risk?.status==='blocked')return {tone:'red',title:'Restrição identificada',text:'Há um impedimento nas verificações disponíveis. Confira os riscos antes de considerar uma operação.'};
 if(n(s.price)===null||s.price<=0||n(s.liquidity)===null)return {tone:'gray',title:'Dados de mercado incompletos',text:'Preço ou liquidez não estão disponíveis nesta consulta. Não é possível concluir a análise pontual.'};
 if(objective==='reentry'&&chart.status!=='available')return {tone:'gray',title:'Faltam dados para avaliar reentrada',text:chart.reason+' A foto atual de preço e volume não substitui o histórico do gráfico.'};
 if(s.chain_id!=='solana')return {tone:'gray',title:'Análise de mercado · risco não coberto',text:'Esta rede ainda não tem os verificadores de contrato, LP e concentração adaptados. Os dados de mercado não representam aprovação de risco.'};
 if(s.risk?.status!=='reviewed'||s.risk.lp_chain_checked!==true||s.mint_disabled!==true||s.freeze_disabled!==true||s.extensions_review!==false)return {tone:'gray',title:'Análise incompleta',text:'Ainda faltam verificações de contrato ou liquidez. Dados ausentes não são tratados como aprovação.'};
 if(s.liquidity<25000)return {tone:'yellow',title:'Liquidez abaixo do filtro do radar',text:'A liquidez é inferior a US$ 25 mil. Esta consulta não confirma condições favoráveis de execução.'};
 if(objective==='reentry')return {tone:'yellow',title:chart.higher_lows_last3||chart.close_above_prior_high?'Há sinais locais de recuperação para investigar':'Retomada ainda sem confirmação na amostra',text:chart.higher_lows_last3||chart.close_above_prior_high?'Os candles mostram uma melhora local. Ainda é necessário avaliar continuidade, volume e o risco da operação.':'A amostra não mostra três mínimas ascendentes nem fechamento acima da máxima anterior da janela. Isso não prevê o próximo movimento.'};
 return {tone:'blue',title:'Dados disponíveis para revisão manual',text:'Não foram identificadas restrições nos verificadores que concluíram a consulta. É uma triagem pontual, sem confirmação em duas leituras ou garantia de segurança.'};
}

export async function analyzeManual(request:any,db:any,get:any,rpc:any,clock=()=>Date.now()/1000){
 const parsed=parseManualInput(request.chain,request.input),network=manualNetworks.find(c=>c.id===parsed.chain)!;
 const objective=request.objective;
 if(!['general','risk','reentry'].includes(objective))throw new ApiError('invalid_request');
 const equal=(a:any,b:string)=>typeof a==='string'&&(parsed.chain==='solana'?a===b:a.toLowerCase()===b.toLowerCase());
 const response=await get(parsed.type==='pair'?`https://api.dexscreener.com/latest/dex/pairs/${parsed.chain}/${parsed.address}`:`https://api.dexscreener.com/token-pairs/v1/${parsed.chain}/${parsed.address}`,6000);
 const pairs=parsed.type==='pair'?response?.pairs:response;
 if(!Array.isArray(pairs))throw new ApiError('market_unavailable');
 const matching=pairs.filter((p:any)=>p.chainId===parsed.chain&&(parsed.type==='pair'?equal(p.pairAddress,parsed.address):equal(p.baseToken?.address,parsed.address)))
  .sort((a:any,b:any)=>(n(b.liquidity?.usd)||0)-(n(a.liquidity?.usd)||0));
 if(!matching.length)throw new ApiError('token_not_found');
 const pair=matching[0],address=pair.baseToken?.address;
 if(!(parsed.chain==='solana'?validAddress(address)&&validAddress(pair.pairAddress):evmAddress(address)&&evmPool(pair.pairAddress)))throw new ApiError('market_unavailable');
 const issues:string[]=[];let mint:any=null,cached:any=null;
 const chartPromise=objective==='risk'?Promise.resolve(null):get(`https://api.geckoterminal.com/api/v2/networks/${network.gecko}/pools/${pair.pairAddress}/ohlcv/minute?aggregate=1&limit=60&currency=usd&token=${address}`,6000).catch(()=>{issues.push('Histórico de candles indisponível na fonte gratuita.');return null;});
 if(parsed.chain==='solana'){
  await Promise.all([
   (async()=>{try{mint=(await rpc([address]))[0];}catch{issues.push('Permissões do token não puderam ser consultadas na Solana.');}})(),
   (async()=>{
    try{cached=(await db(`pump_radar_state?id=eq.main&select=report:payload->risk_reports->${address}`))[0]?.report;}catch{/* Optional shared public-data cache only. */}
    if(cached?.report?.mint!==address||typeof cached.fetched_at!=='number'||!Number.isFinite(cached.fetched_at)||cached.fetched_at>clock()+30||clock()-cached.fetched_at>1800||!cached.report.markets?.some((m:any)=>m.address===pair.pairAddress)){
     cached=null;
     try{cached={fetched_at:clock(),report:cleanReport(await get(`https://api.rugcheck.xyz/v1/tokens/${address}/report`,4000),address)};}catch{issues.push('Relatório RugCheck indisponível; risco permanece pendente.');}
    }
   })()]);
 }
 let snapshot:any;
 if(parsed.chain==='solana'){
  snapshot=fromDex(address,pair,mint,clock());snapshot.sources.discovery='Consulta manual — não adicionada ao radar';
  const targets=[...new Set<string>([...lpAccounts(cached?.report,pair.pairAddress),...whaleTargets(cached?.report).map((h:any)=>h.address)])];
  const accounts=new Map<string,any>();
  if(targets.length)try{const values=await rpc(targets);if(values.length!==targets.length)throw Error('schema');targets.forEach((a,i)=>accounts.set(a,values[i]));}catch{issues.push('Consulta atual de LP e detentores indisponível.');}
  snapshot.risk=assessRisk(snapshot,cached,accounts,clock());
  snapshot.whales=observeWhales(snapshot,cached?.report,accounts,{},clock());
 }else snapshot=networkSnapshot(parsed.chain,address,pair,clock());
 const chart=objective==='risk'?{status:'not_requested',candles:[],reason:'Histórico não solicitado no foco de riscos do contrato.'}:chartEvidence(parseCandles(await chartPromise,clock()),clock());
 const verdict=manualVerdict(snapshot,chart,objective);
 return {version:'manual-v1',chain:parsed.chain,objective,queried_at:clock(),snapshot,
  chart,verdict,source_errors:issues,limitations:[
   'Consulta pontual: não confirma duas leituras, mudança de saldo de carteiras ou slow rug ao longo do tempo.',
   'Venda não simulada; participantes únicos, insiders, bundles e atividade orgânica não auditados.',
   'Relatórios e preços podem estar em cache. Não há execução de ordens ou indicação de compra/venda.']};
}
