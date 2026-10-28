import html
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from pump.alerts import LABELS, alert_text
from pump.config import ROOT, load_rules, settings
from pump.storage import make_store, PublicMarketStore, StorageError

STATUS = {'candidate': 'Sinal de mercado • risco parcial', 'confirming': 'Aguardando confirmação',
          'blocked': 'Rejeitada pelos critérios', 'watch': 'Em observação',
          'incomplete': 'Dados insuficientes', 'queued': 'Na fila'}


def stamp(value):
    return datetime.fromtimestamp(value, ZoneInfo('America/Sao_Paulo')).strftime('%d/%m %H:%M:%S') if value else '—'


def money(n):
    return '—' if n is None else f'US$ {n:,.0f}'


def render():
    load_dotenv(ROOT / '.env')
    st.markdown("<div class='breadcrumb'>⚡ Pump Trader / <span>Radar gratuito</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Seu radar de memecoins</h1><p class='sub-title'>Descoberta automática com fontes públicas. Sem depósito, sem chave GMGN e sem ordens de compra.</p>", unsafe_allow_html=True)
    demo = st.toggle('Visualizar demonstração com dados simulados', key='pump_demo')
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    config = settings(secrets)
    try:
        rules = load_rules()
        store = make_store(config, True) if demo else PublicMarketStore(config.get('SUPABASE_URL', ''), config.get('SUPABASE_KEY') or config.get('PUMP_SUPABASE_KEY', ''))
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
    try:
        state = store.read()
    except StorageError as exc:
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
    radar_tab, alerts_tab, config_tab = st.tabs(['📡 Radar', '🔔 Alertas', '⚙️ Critérios e operação'])
    with alerts_tab:
        if not run.get('telegram_configured', telegram_configured) and not demo:
            st.info('Alertas no painel. Para receber notificações com a aba fechada, configure seu bot pessoal do Telegram no Vault; ele é opcional e não exige depósito.')
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
        status_filter = st.selectbox('Exibir', ['Todos', *STATUS.values()], key='pump_filter')
        selected = [t for t in tokens if status_filter == 'Todos' or STATUS.get(t.get('status')) == status_filter]
        priority = {'candidate':0,'confirming':1,'watch':2,'blocked':3,'incomplete':4,'queued':5}
        selected.sort(key=lambda t:(priority.get(t.get('status'), 6), -t.get('last_checked', 0)))
        if not selected:
            st.info('Nenhuma moeda nesta seleção. A descoberta gratuita cobre uma amostra de pools novas e perfis recentes, que podem ser promocionais.')
        if selected:
            rows = []
            for token in selected:
                snap = token.get('snapshot') or {}
                rows.append({'Moeda':snap.get('symbol', '?'), 'Situação':STATUS.get(token.get('status'), 'Na fila'),
                    'Liquidez (USD)':snap.get('liquidity'), 'Volume 5min (USD)':snap.get('volume_5m'),
                    'Variação 5min (%)':snap.get('change_5m'), 'Consulta':stamp(snap.get('observed_at'))})
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption('Abra os detalhes abaixo para ver os critérios, a origem e as verificações pendentes.')
        for token in selected[:60]:
            s = token.get('snapshot') or {}
            with st.expander(f"{s.get('symbol', token['address'][:8])} · {STATUS.get(token.get('status'), 'Na fila')}"):
                st.caption(f"Consulta: {stamp(s.get('observed_at'))} · Descoberta: {stamp(token['first_seen'])}")
                if s.get('observed_at') and now-s['observed_at'] > run.get('rules', {}).get('confirmation_max_seconds', 1200):
                    st.warning('Consulta antiga. Aguarde nova avaliação.')
                m1,m2,m3 = st.columns(3)
                m1.metric('Liquidez', money(s.get('liquidity')))
                m2.metric(s.get('valuation_type', 'Market cap'), money(s.get('valuation', s.get('market_cap'))))
                m3.metric('Volume em 5 min', money(s.get('volume_5m')))
                for reason in token.get('reasons', []):
                    st.text('• ' + reason)
                st.code(token['address'], language=None)
                if not demo:
                    st.link_button('Abrir gráfico', s.get('pair_url') or 'https://dexscreener.com/solana/' + token['address'], key='open_'+token['address'])
                history = token.get('history', [])
                if len(history) > 1:
                    import pandas as pd
                    frame = pd.DataFrame(history)
                    frame['Consulta'] = pd.to_datetime(frame['observed_at'], unit='s', utc=True).dt.tz_convert('America/Sao_Paulo')
                    st.line_chart(frame.set_index('Consulta')[['price']], y_label='Preço consultado (USD)')
                st.json(s, expanded=False)
    with config_tab:
        st.write('Os limites iniciais são hipóteses de triagem. Ainda não foram calibrados para demonstrar rentabilidade.')
        from dataclasses import asdict
        st.json(run.get('rules') or asdict(rules))
        st.write('Duas consultas confirmam o sinal. A janela móvel de 5 minutos pode se sobrepor; isso não representa duas evidências independentes.')
        st.write('Fontes: DEX Screener, GeckoTerminal e RPC público da Solana. Ciclos de 5 minutos, até 30 moedas em acompanhamento. APIs gratuitas podem atrasar, limitar ou interromper respostas.')
        st.write('Os filtros usam volume em USD, quantidade de compras/vendas, variação, liquidez, idade da pool e permissões básicas do token. A relação de contagem de compras/vendas não é uma relação de valores financeiros. Extensões não reconhecidas ficam pendentes. FDV é identificado e não tratado como market cap.')
        st.write('As variações após 15 minutos e 1 hora comparam preços observados na mesma pool. Não simulam execução, taxas, slippage ou lucro realizável. Não há promessa de retorno, análise de narrativas por IA ou execução de ordens.')
        st.caption('O feed compartilhado contém somente dados e sinais públicos de mercado. Carteiras pessoais, anotações, configurações e credenciais não fazem parte desse feed. Dados: DEX Screener e GeckoTerminal/CoinGecko.')
