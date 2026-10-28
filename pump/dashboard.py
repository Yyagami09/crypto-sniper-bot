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
    from pump.dashboard_ui import CSS
    from pump.networks import NETWORKS
    st.markdown(CSS,unsafe_allow_html=True)
    title,network,options = st.columns([3,1.4,.8],vertical_alignment='center')
    with title:
        st.markdown("<div class='dex-workspace-head'><h1>Dex Sniper</h1><p>Seu radar de memecoins, em um só lugar.</p></div>",unsafe_allow_html=True)
    with options,st.popover('Opções',use_container_width=True):
        demo = st.toggle('Visualizar demonstração com dados simulados',key='pump_demo')
        st.caption('A demonstração usa exemplos fictícios. Não envia mensagens nem executa ordens.')
        from pump.early import mode_options
        mode_options()
    with network:
        chain = st.selectbox('Rede blockchain',list(NETWORKS),format_func=NETWORKS.get,key='dex_network',disabled=demo,label_visibility='collapsed')
    if demo:
        chain='solana'
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
    _body(store, rules, demo, bool(config.get('TELEGRAM_BOT_TOKEN') and config.get('TELEGRAM_CHAT_ID')), chain)


@st.fragment(run_every='15s')
def _body(store, rules, demo, telegram_configured, chain='solana'):
    from pump.account import ensure_session
    if not ensure_session():
        st.warning('Entre novamente para continuar acompanhando o radar.')
        return
    if not demo:
        store.access_token = st.session_state.sniper_session['access_token']
    if not demo and chain!='solana':
        from pump.networks import render_observation
        render_observation(store,chain)
        return
    try:
        state = store.read()
    except StorageError:
        st.warning('O feed gratuito está temporariamente indisponível.')
        st.info('O feed de mercado admite somente leitura com a chave Supabase já configurada. As tabelas privadas e o Vault continuam protegidos.')
        st.link_button('Ver instruções de ativação', 'https://github.com/Yyagami09/crypto-sniper-bot/blob/main/RADAR_GRATUITO.md')
        return
    now = time.time()
    if not demo and st.session_state.get('sniper_profile',{}).get('radar_mode','classic')=='early-v1':
        from pump.early import render_experiment
        render_experiment(store,state,now)
        return
    state['alerts']=[a for a in state.get('alerts',[]) if not a['kind'].startswith('early_')]
    run = state.get('run', {})
    from pump.dashboard_ui import status_line,operation_details
    status_line(run,now,stamp,demo)
    tokens = list(state.get('tokens', {}).values())
    metrics=[('Em acompanhamento',len(tokens)),
        ('Sinais de mercado recentes',sum(t.get('status')=='candidate' and now-t.get('last_checked',0)<=run.get('rules',{}).get('confirmation_max_seconds',1200) for t in tokens)),
        ('Rejeitadas pelos filtros',sum(t.get('status')=='blocked' for t in tokens)),
        ('Alertas nas últimas 24h',sum(now-x['created_at']<=86400 for x in state['alerts']))]
    for i,(column,(label,value)) in enumerate(zip(st.columns(4),metrics)):
        with column,st.container(border=True,key='dex_summary_'+str(i)):
            st.metric(label,value)
    radar_tab, history_tab, alerts_tab, config_tab = st.tabs(['📡 Radar', '⛏️ Achados · 24h', '🔔 Alertas', '⚙️ Critérios e operação'])
    with history_tab:
        from pump.signal_history import render_history
        render_history(store,state,now,demo)
    with alerts_tab:
        with st.expander('Som e notificações do navegador'):
            from pump.browser_alerts import render_browser_alerts
            render_browser_alerts(state['alerts'], demo)
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
        st.subheader('Operação do radar')
        operation_details(run,stamp)
        with st.expander('Cobertura e limites da análise'):
            st.write('Triagem parcial: LP e concentração reportada passam por filtros de risco. A venda não é simulada; insiders, bundles e wash trading não são auditados. Movimentos de grandes carteiras são variações de saldo de uma amostra.')
        st.subheader('Critérios de análise')
        st.write('Os limites iniciais são hipóteses de triagem. Ainda não foram calibrados para demonstrar rentabilidade.')
        from dataclasses import asdict
        st.json(run.get('rules') or asdict(rules))
        st.write('Aderência aos critérios: cada um dos sete filtros de mercado vale 1/7 da nota. Dados essenciais ausentes, consultas antigas ou restrições deixam a pontuação pendente. A nota não estima lucro ou segurança e não altera o motor de alertas.')
        st.write('Duas consultas confirmam o sinal. A janela móvel de 5 minutos pode se sobrepor; isso não representa duas evidências independentes.')
        st.write('Fontes: DEX Screener, GeckoTerminal e RPC público da Solana. Ciclos de 1 minuto, até 30 moedas em acompanhamento. APIs gratuitas podem atrasar, limitar ou interromper respostas.')
        st.write('Os sete critérios de mercado usam volume em USD, quantidade de compras/vendas, variação, liquidez, idade da pool e faixa de avaliação. Uma camada separada retém sinais por risco: LP, concentração fora das pools, alertas críticos externos e giro de volume atípico. Relatórios indisponíveis deixam a avaliação pendente. FDV é identificado e não tratado como market cap.')
        st.write('Grandes carteiras: uma amostra de até cinco contas de grandes detentores é consultada na Solana. O indicador mostra variações de saldo, não ordens de compra/venda comprovadas, e não adiciona pontos nem bloqueia sinais por si só.')
        st.write('As variações após 15 minutos e 1 hora comparam preços observados na mesma pool. Não simulam execução, taxas, slippage ou lucro realizável. Não há promessa de retorno, análise de narrativas por IA ou execução de ordens.')
        st.caption('O feed compartilhado contém somente dados e sinais públicos de mercado. Carteiras pessoais, anotações, configurações e credenciais não fazem parte desse feed. Dados: DEX Screener e GeckoTerminal/CoinGecko.')
