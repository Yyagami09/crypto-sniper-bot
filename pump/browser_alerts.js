export function unseenAlerts(state, alerts, now) {
  const ids = alerts.map(a => a.id);
  if (!state.ready) { state.ready = true; state.seen = new Set(ids); return []; }
  const fresh = alerts.filter(a => !state.seen.has(a.id) && now-a.created_at <= 900 &&
    now >= a.created_at && ['candidate','conditions_lost','data_gap','early_watch','early_changed'].includes(a.kind));
  state.seen = new Set([...state.seen, ...ids].slice(-500));
  return fresh;
}

export default function(component) {
  const {parentElement: root, data} = component;
  const all = window.__sniperAlerts || (window.__sniperAlerts = {});
  const state = all[data.scope] || (all[data.scope] = {sound:false, desktop:false, ready:false});
  const sound = root.querySelector('[data-sound]'), desktop = root.querySelector('[data-desktop]');
  const status = root.querySelector('[data-status]');
  const message = text => { status.textContent = text; };
  async function chime(kind='candidate') {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) throw new Error('audio_unsupported');
    state.audio ||= new AC();
    await state.audio.resume();
    if (state.audio.state !== 'running') throw new Error('audio_suspended');
    const start = state.audio.currentTime;
    for (let i=0;i<2;i++) {
      const osc = state.audio.createOscillator(), gain=state.audio.createGain();
      osc.frequency.value = kind === 'candidate' ? (i ? 1046 : 784) : (i ? 440 : 523);
      gain.gain.setValueAtTime(0,start+i*.24);
      gain.gain.linearRampToValueAtTime(.12,start+i*.24+.02);
      gain.gain.exponentialRampToValueAtTime(.001,start+i*.24+.19);
      osc.connect(gain);gain.connect(state.audio.destination);
      osc.start(start+i*.24);osc.stop(start+i*.24+.2);
    }
  }
  function toast(title, body, id) {
    const n = new Notification(title, {body,tag:'sniper-'+id});
    n.onclick = () => {window.focus();n.close();};
  }
  function labels() {
    sound.textContent = state.sound ? '🔇 Desativar som' : '🔊 Ativar e testar som';
    desktop.textContent = state.desktop ? 'Desativar notificações do navegador' : 'Ativar notificações do navegador';
  }
  sound.onclick = async () => {
    if (state.sound) {state.sound=false;message('Som desativado.');labels();return;}
    try {await chime();state.sound=true;message('Som ativado e testado nesta página.');}
    catch {state.sound=false;message('O navegador bloqueou o áudio. Confira o volume e tente novamente.');}
    labels();
  };
  desktop.onclick = async () => {
    if (state.desktop) {state.desktop=false;labels();message('Avisos do navegador desativados nesta página.');return;}
    if (!('Notification' in window)) {message('Notificações indisponíveis neste navegador. Use o Telegram.');return;}
    try {
      const permission = Notification.permission==='default' ? await Notification.requestPermission() : Notification.permission;
      if (permission!=='granted') {message('Permissão não concedida. Confira as configurações do site ou use o Telegram.');return;}
      toast('Crypto Sniper — teste','Notificações do navegador ativadas. Este aviso é apenas um teste.','test');
      state.desktop=true;message('Teste enviado ao sistema. Confira se o Windows permite notificações do navegador.');
    } catch {message('O navegador não permitiu a notificação neste ambiente. Use o Telegram.');}
    labels();
  };
  const fresh = unseenAlerts(state,data.alerts||[],Date.now()/1000);
  if (fresh.length) {
    const last=fresh.at(-1),label=last.kind==='early_watch'?'Vale abrir o gráfico · experimental':last.kind==='early_changed'?'Experimental: triagem alterada':last.kind==='candidate'?'Novo sinal de mercado':last.kind==='conditions_lost'?'Condições perdidas':'Dados indisponíveis';
    const text = `${last.symbol||'?'} · ${label} · Risco parcial${fresh.length>1?` (+${fresh.length-1} avisos)`:''}`;
    if (state.sound) chime(last.kind).catch(()=>{state.sound=false;labels();message('Áudio suspenso pelo navegador. Ative o som novamente.');});
    if (state.desktop && 'Notification' in window && Notification.permission==='granted') {
      try {toast('Crypto Sniper',text,last.id);} catch {state.desktop=false;labels();message('Falha no aviso do navegador. Use o Telegram.');}
    }
  }
  labels();
  message(state.sound||state.desktop ? 'Ativo nesta página. Aba suspensa, fechada ou computador em repouso podem interromper os avisos.' : 'Ative as opções desejadas. Alertas antigos não disparam ao abrir a página.');
}
