import html
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from pump.alerts import LABELS
from pump.config import ROOT, load_rules, settings
from pump.storage import make_store, PublicMarketStore, StorageError

def stamp(value):
    return datetime.fromtimestamp(value, ZoneInfo('America/Sao_Paulo')).strftime('%d/%m %H:%M:%S') if value else '—'


def render():
    load_dotenv(ROOT / '.env')
    st.markdown("<div class='breadcrumb'>🚀 Dex Trade / <span>Radar gratuito</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Seu radar de memecoins</h1><p class='sub-title'>Descoberta automática com fontes públicas. Sem depósito, sem chave GMGN e sem ordens de compra.</p>", unsafe_allow_html=True)
    demo = st.toggle('Visualizar demonstração com dados simulados', key='pump_demo')
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    config = settings(secrets)
    try:
        rules = load_rules()
        store = make_store(config, True) if demo else PublicMarketStore(config.get('SUPABASE_URL', ''), config.get('SUPABASE_KEY') or config.get('PUMP_SUPABASE_KEY', ''), st.session_state.get('sniper_session', {}).get('access_token'))
    except (StorageError, ValueError) as exc:
        st.info(str(exc))
        st.write('O modo gratuito usa as configurações Supabase já existentes no painel. Não requer chave de dados, carteira ou depósito. Consulte RADAR_GRATUITO.md no repositório.')
        st.caption('Você pode ativar a demonstração acima para conhecer o painel sem conectar suas contas.')
        return
    if demo:
        st.warning('DEMONSTRAÇÃO: moedas, histórico e alertas abaixo são simulados.')
        if st.button('Carregar exemplos de alertas', key='pump_seed'):
            from pump.demo import seed_demo
            if not seed_demo(store, rules):
                st.info('Aguarde a varredura de demonstração terminar.')
    st.caption('O painel atualiza a cada 15 segundos. A coleta automática ocorre a cada 5 minutos, mesmo com a aba fechada.')
    _body(store, rules, demo, bool(config.get('TELEGRAM_BOT_TOKEN') and config.get('TELEGRAM_CHAT_ID')))


@st.fragment(run_every='15s')
def _body(store, rules, demo, telegram_configured):
    from pump.account import ensure_session
    if not ensure_session():
        st.warning('Entre novamente para continuar acompanhando o radar.')
        return
    if not demo:
        store.access_token = st.session_state.sniper_session['access_token']
    try:
        state = store.read()
    except StorageError:
        st.warning('O feed gratuito está temporariamente indisponível.')
        st.info('O feed de mercado admite somente leitura com a chave Supabase já configurada. As tabelas privadas e o Vault continuam protegidos.')
        st.link_button('Ver instruções de ativação', 'https://github.com/Yyagami09/crypto-sniper-bot/blob/main/RADAR_GRATUITO.md')
        return
    now = time.time()
    run = state.get('run', {})
    latest = run.get('completed_at', run.get('started_at', 0))
    if demo:
        st.info('Modo demonstração. Nenhuma consulta ou mensagem externa é enviada.')
    elif run.get('status') == 'missing_key':
        st.warning('A versão anterior aguardava uma chave. Aguarde a atualização do coletor gratuito.')
    elif not latest:
        st.warning('O coletor gratuito ainda não publicou a primeira varredura. Aguarde o próximo ciclo.')
    elif run.get('status') == 'error':
        st.error(f"Varredura interrompida ({run.get('error', 'erro')}). Nova tentativa após {stamp(state.get('backoff_until'))}.")
    elif now-latest > max(900, run.get('rules', {}).get('interval_seconds', 300)*3):
        st.warning('Sem atualização recente do radar. Confira o processo antes de usar os dados.')
    else:
        st.success('Varredura em andamento' if run.get('status') == 'running' else 'Radar atualizou recentemente')
    if not demo:
        st.info('Modo gratuito: sinais de atividade com avaliação parcial de risco. Não verifica concentração por carteira, insiders, bundles ou wash trading.')
        for issue in run.get('source_errors', []):
            st.warning(str(issue))
    st.caption(f"Último ciclo: {stamp(latest)} · Tokens consultados no ciclo: {run.get('checked', 0)} · Falhas: {run.get('errors', 0)} · Horários de Brasília")
    tokens = list(state.get('tokens', {}).values())
    a,b,c,d = st.columns(4)
    a.metric('Em acompanhamento', len(tokens))
    b.metric('Sinais de mercado recentes', sum(t.get('status') == 'candidate' and now-t.get('last_checked',0) <= run.get('rules', {}).get('confirmation_max_seconds', 1200) for t in tokens))
    c.metric('Rejeitadas pelos filtros', sum(t.get('status') == 'blocked' for t in tokens))
    d.metric('Alertas nas últimas 24h', sum(now-x['created_at'] <= 86400 for x in state['alerts']))
    from pump.browser_alerts import render_browser_alerts
    render_browser_alerts(state['alerts'], demo)
    radar_tab, alerts_tab, config_tab = st.tabs(['📡 Radar', '🔔 Alertas', '⚙️ Critérios e operação'])
    with alerts_tab:
        if not run.get('telegram_configured', telegram_configured) and not demo:
            st.info('Para receber avisos com o painel fechado, conecte seu bot pessoal no menu Notificações.')
        alerts = sorted(state['alerts'], key=lambda a:a['created_at'], reverse=True)[:50]
        if not alerts:
            st.info('Nenhum sinal confirmado ainda. O radar exige duas consultas, espaçadas por pelo menos 4 minutos, antes de registrar um sinal de mercado.')
        for alert in alerts:
            symbol = html.escape(str(alert['snapshot'].get('symbol', '?')))
            label = 'SINAL DE MERCADO — RISCO PARCIAL' if not demo and alert['kind'] == 'candidate' else LABELS[alert['kind']]
            st.markdown(f'<div class="sniper-card"><p class="game-name">{symbol} · {label}</p><div class="meta-line">{stamp(alert["created_at"])} · Consulta registrada</div></div>', unsafe_allow_html=True)
            for reason in alert['reasons']:
                st.text('• ' + str(reason))
            st.code(alert['address'], language=None)
            if not demo:
                st.link_button('Abrir gráfico', alert['snapshot'].get('pair_url') or 'https://dexscreener.com/solana/' + alert['address'])
            delivery = {'sent':'Enviado ao Telegram','pending':'Pendente de envio ao Telegram',
                        'demo':'Simulação','panel':'Registrado no feed de mercado','failed':'Envio falhou','expired':'Alerta expirou para envio'}
            st.caption(delivery.get(alert.get('delivery'), 'Registrado no painel'))
            for horizon, observation in alert.get('observations', {}).items():
                st.caption(f"Variação do preço observado após {horizon}: {observation['change_percent']:+.2f}% — não representa lucro de uma operação.")
            with st.expander('Dados no momento do alerta'):
                st.json(alert['snapshot'])
    with radar_tab:
        from pump.radar_cards import render_radar
        render_radar(tokens, run.get('rules') or {}, now, demo)
    with config_tab:
        st.write('Os limites iniciais são hipóteses de triagem. Ainda não foram calibrados para demonstrar rentabilidade.')
        from dataclasses import asdict
        st.json(run.get('rules') or asdict(rules))
        st.write('Aderência aos critérios: cada um dos sete filtros de mercado vale 1/7 da nota. Dados essenciais ausentes, consultas antigas ou restrições deixam a pontuação pendente. A nota não estima lucro ou segurança e não altera o motor de alertas.')
        st.write('Duas consultas confirmam o sinal. A janela móvel de 5 minutos pode se sobrepor; isso não representa duas evidências independentes.')
        st.write('Fontes: DEX Screener, GeckoTerminal e RPC público da Solana. Ciclos de 5 minutos, até 30 moedas em acompanhamento. APIs gratuitas podem atrasar, limitar ou interromper respostas.')
        st.write('Os filtros usam volume em USD, quantidade de compras/vendas, variação, liquidez, idade da pool e permissões básicas do token. A relação de contagem de compras/vendas não é uma relação de valores financeiros. Extensões não reconhecidas ficam pendentes. FDV é identificado e não tratado como market cap.')
        st.write('As variações após 15 minutos e 1 hora comparam preços observados na mesma pool. Não simulam execução, taxas, slippage ou lucro realizável. Não há promessa de retorno, análise de narrativas por IA ou execução de ordens.')
        st.caption('O feed compartilhado contém somente dados e sinais públicos de mercado. Carteiras pessoais, anotações, configurações e credenciais não fazem parte desse feed. Dados: DEX Screener e GeckoTerminal/CoinGecko.')
