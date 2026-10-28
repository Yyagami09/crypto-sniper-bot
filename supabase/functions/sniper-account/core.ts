export class ApiError extends Error {
 code:string;status:number;
 constructor(code:string,status=400){super(code);this.code=code;this.status=status;}
}
export function validUsername(x:any){return typeof x==='string'&&/^[a-z0-9_]{3,32}$/.test(x);}
export function validPassword(x:any){return typeof x==='string'&&x.length>=12&&x.length<=128;}
export function matchingStart(updates:any[],challenge:string,since:number){
 return updates.map(u=>u.message).find(m=>m?.chat?.type==='private'&&m.from?.id===m.chat.id&&
  m.text===`/start ${challenge}`&&m.date>=since&&m.date<=Date.now()/1000+30);
}
export function publicConnection(t:any){
 return t?.bot_username?{connected:!!t.enabled,bot_username:t.bot_username,
  connected_at:t.connected_at,challenge_at:t.challenge_at,
  link:!t.enabled?`https://t.me/${t.bot_username}?start=${t.challenge}`:null}:null;
}
