const change=(current:number,previous:number)=>previous>0?(current/previous-1)*100:null;

export function liquidityTrend(s:any,risk:any,state:any,now:number){
 const out:any={status:'collecting',observations:0,window_minutes:0,lp_supply_change_pct:null,
  base_reserve_change_pct:null,quote_reserve_change_pct:null,
  limitation:'Padrão compatível com retirada gradual de liquidez; não comprova rug pull ou intenção.'};
 if(!risk.lp_chain_checked||!/^\d+$/.test(risk.lp_supply_raw||'')||!Number.isFinite(s.base_reserve)||!Number.isFinite(s.quote_reserve)||s.base_reserve<=0||s.quote_reserve<=0)return out;
 state.liquidity_trends||={};
 const old=state.liquidity_trends[s.address];
 let rows=old?.pair===s.pair_address?old.rows.filter((r:any)=>now-r.at<=3600):[];
 const point={at:now,supply:Number(BigInt(risk.lp_supply_raw)),base:s.base_reserve,quote:s.quote_reserve};
 if(!rows.length||now-rows.at(-1).at>=240)rows=[...rows,point].slice(-13);
 state.liquidity_trends[s.address]={pair:s.pair_address,rows};
 const recent=rows.slice(-4);
 out.observations=recent.length;
 if(recent.length){
  out.window_minutes=(point.at-recent[0].at)/60;
  out.lp_supply_change_pct=change(point.supply,recent[0].supply);
  out.base_reserve_change_pct=change(point.base,recent[0].base);
  out.quote_reserve_change_pct=change(point.quote,recent[0].quote);
 }
 if(recent.length<4||out.window_minutes<12||out.window_minutes>30)return out;
 const consecutive=recent.slice(1).every((r:any,i:number)=>r.at-recent[i].at<=1200&&r.supply<recent[i].supply);
 const flagged=consecutive&&out.lp_supply_change_pct<=-5&&out.base_reserve_change_pct<=-10&&out.quote_reserve_change_pct<=-10;
 out.status=flagged?'warning':'no_pattern';
 return out;
}
