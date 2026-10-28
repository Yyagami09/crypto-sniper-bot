import {validAddress} from './core.ts';

export function whaleTargets(report:any){
 return (report?.holders||[]).filter((h:any)=>validAddress(h.address)&&validAddress(h.owner)&&
  !isPoolHolder(report,h)).sort((a:any,b:any)=>(b.pct||0)-(a.pct||0)).slice(0,5);
}

export function isPoolHolder(report:any,h:any){
 return report.markets.some((m:any)=>m.address===h.owner||(m.pool_accounts||[]).includes(h.address)||(m.pool_owners||[]).includes(h.owner));
}

export function observeWhales(s:any,report:any,accounts:Map<string,any>,state:any,now:number){
 const out:any={version:'whales-v1',status:'unavailable',checked_at:now,items:[],increases:0,decreases:0,gradual_reductions:0,
  coverage:'Amostra de até 5 contas de grandes detentores, fora das pools; não cobre todas as carteiras',
  limitation:'Variações de saldo podem ser transferências. Não comprovam compras, vendas ou intenção. USD estimado ao preço consultado.'};
 const targets=whaleTargets(report);
 if(!targets.length||!/^\d+$/.test(s.supply_raw||'')||!Number.isInteger(s.token_decimals)||s.token_decimals<0||s.token_decimals>18)return out;
 const supply=BigInt(s.supply_raw);if(supply<=0n)return out;
 state.whale_observations||={};
 const before=state.whale_observations[s.address]||{},next:any={},wallets:any={};
 for(const t of targets){
  if(!accounts.has(t.address))continue;
  const account=accounts.get(t.address);
  let amount='0';
  if(account!==null){
   const info=account?.data?.parsed?.info;
   if(!['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'].includes(account?.owner)||account?.data?.parsed?.type!=='account'||info?.mint!==s.address||info?.owner!==t.owner||info?.tokenAmount?.decimals!==s.token_decimals||!/^\d+$/.test(info?.tokenAmount?.amount||''))continue;
   amount=info.tokenAmount.amount;
  }
  const w=wallets[t.owner]||(wallets[t.owner]={amount:0n,addresses:[]});
  w.amount+=BigInt(amount);w.addresses.push(t.address);
 }
 for(const [wallet,w] of Object.entries<any>(wallets)){
  const account_key=w.addresses.sort().join(','),previous=before[wallet];
  const tokens=Number(w.amount)/10**s.token_decimals;
  const usd=s.price>0?tokens*s.price:null;
  const percentage=Number(w.amount*1000000n/supply)/10000;
  next[wallet]={amount:w.amount.toString(),account_key,observed_at:now};
  const comparable=previous&&previous.account_key===account_key&&now-previous.observed_at>=30&&now-previous.observed_at<=1200;
  const delta=comparable?w.amount-BigInt(previous.amount):null;
  // Retain a just-exited holder in this cycle instead of hiding the decrease.
  const previousUsd=previous?s.price*Number(BigInt(previous.amount))/10**s.token_decimals:0;
  if(percentage<1&&(usd||0)<10000&&previousUsd<10000&&(!previous||Number(BigInt(previous.amount)*1000000n/supply)/10000<1))continue;
  const deltaTokens=delta===null?null:Number(delta)/10**s.token_decimals;
  const direction=delta===null?'baseline':delta>0n?'increase':delta<0n?'decrease':'unchanged';
  let streak=direction==='decrease'?(previous.decrease_streak||0)+1:0;
  let startAmount=streak>1?previous.decrease_start_amount:previous?.amount||w.amount.toString();
  let startAt=streak>1?previous.decrease_start_at:previous?.observed_at||now;
  if(now-startAt>3600){streak=direction==='decrease'?1:0;startAmount=previous?.amount||w.amount.toString();startAt=previous?.observed_at||now;}
  const initial=BigInt(startAmount),windowPct=initial>0n?(Number(w.amount)/Number(initial)-1)*100:0;
  const supplyPct=Number((w.amount-initial)*1000000n/supply)/10000;
  const gradual=streak>=3&&now-startAt>=720&&windowPct<=-10&&supplyPct<=-.5;
  Object.assign(next[wallet],{decrease_streak:streak,decrease_start_amount:startAmount,decrease_start_at:startAt});
  if(previous&&previous.account_key===account_key&&now-previous.observed_at<30)next[wallet]=previous;
  if(gradual)out.gradual_reductions++;
  if(direction==='increase')out.increases++;if(direction==='decrease')out.decreases++;
  out.items.push({wallet,account_count:w.addresses.length,balance_tokens:tokens,value_usd:usd,pct_supply:percentage,
   delta_tokens:deltaTokens,delta_usd:deltaTokens===null||!s.price?null:deltaTokens*s.price,direction,
   previous_at:comparable?previous.observed_at:null,observed_at:now,
   gradual_reduction:gradual,reduction_window_minutes:(now-startAt)/60,balance_change_window_pct:windowPct});
 }
 if(Object.keys(wallets).length)state.whale_observations[s.address]=next;
 out.status=out.items.length?(out.increases||out.decreases?'changes':out.items.some((w:any)=>w.direction==='baseline')?'observing':'unchanged'):'unavailable';
 return out;
}
