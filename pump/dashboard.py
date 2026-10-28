import html
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from pump.alerts import LABELS, alert_text
from pump.config import ROOT, load_rules, settings
from pump.storage import make_store, StorageError

STATUS = {'candidate': 'Candidata a acompanhar', 'confirming': 'Aguardando confirmação',
          'blocked': 'Rejeitada pelos critérios', 'watch': 'Em observação',
          'incomplete': 'Dados insuficientes', 'queued': 'Na fila'}


def stamp(value):
    return datetime.fromtimestamp(value, ZoneInfo('America/Sao_Paulo')).strftime('%d/%m %H:%M:%S') if value else '—'


def money(n):
    return '—' if n is None else f'US$ {n:,.0f}'


def render():
    load_dotenv(ROOT / '.env')
    st.markdown("<div class='breadcrumb'>⚡ Pump Trader / <span>Radar GMGN</span></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Seu radar de memecoins</h1><p class='sub-title'>Descoberta automática, critérios visíveis e alertas para acompanhar.</p>", unsafe_allow_html=True)
    demo = st.toggle('Visualizar demonstração com dados simulados', key='pump_demo')
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    config = settings(secrets)
    try:
        rules = load_rules()
        store = make_store(config, demo)
    except (StorageError, ValueError) as exc:
        st.info(str(exc))
        st.write('Infraestrutura do radar instalada no Supabase. Configure a chave de consulta da GMGN no Vault e o acesso do painel nos Secrets do Streamlit. Consulte ATIVAR_RADAR.md no repositório.')
        st.caption('Você pode ativar a demonstração acima para conhecer o painel sem conectar suas contas.')
        return
    if demo:
        st.warning('DEMONSTRAÇÃO: moedas, histórico e alertas abaixo são simulados.')
        if st.button('Carregar exemplos de alertas', key='pump_seed'):
            from pump.demo import seed_demo
            if not seed_demo(store, rules):
                st.info('Aguarde a varredura de demonstração terminar.')
    st.caption('O painel atualiza a cada 15 segundos enquanto aberto. O radar roda no Supabase, independente da aba.')
    _body(store, rules, demo, bool(config.get('TELEGRAM_BOT_TOKEN') and config.get('TELEGRAM_CHAT_ID')))


@st.fragment(run_every='15s')
def _body(store, rules, demo, telegram_configured):
    try:
        state = store.read()
    except StorageError as exc:
        st.error(str(exc))
        st.info('Se SUPABASE_KEY for uma chave pública, adicione PUMP_SUPABASE_KEY com a chave service_role nos Secrets do Streamlit. Essa chave fica somente no servidor.')
        return
    now = time.time()
    run = state.get('run', {})
    latest = run.get('completed_at', run.get('started_at', 0))
    if demo:
        st.info('Modo demonstração. Nenhuma consulta ou mensagem externa é enviada.')
    elif run.get('status') == 'missing_key':
        st.warning('Infraestrutura instalada. Adicione sua API Key de consulta da GMGN no Vault do Supabase com o nome gmgn_api_key para ativar as varreduras.')
    elif not latest:
        st.warning('O radar ainda não executou. Confira a chave gmgn_api_key no Vault e o agendamento do Supabase.')
    elif run.get('status') == 'error':
        st.error(f"Varredura interrompida ({run.get('error', 'erro')}). Nova tentativa após {stamp(state.get('backoff_until'))}.")
    elif now-latest > max(180, rules.interval_seconds*3):
        st.warning('Sem atualização recente do radar. Confira o processo antes de usar os dados.')
    else:
        st.success('Varredura em andamento' if run.get('status') == 'running' else 'Radar atualizou recentemente')
    st.caption(f"Último ciclo: {stamp(latest)} · Tokens consultados no ciclo: {run.get('checked', 0)} · Falhas: {run.get('errors', 0)} · Horários de Brasília")
    tokens = list(state.get('tokens', {}).values())
    a,b,c,d = st.columns(4)
    a.metric('Em acompanhamento', len(tokens))
    b.metric('Candidatas recentes', sum(t.get('status') == 'candidate' and now-t.get('last_checked',0) <= rules.confirmation_max_seconds for t in tokens))
    c.metric('Rejeitadas pelos filtros', sum(t.get('status') == 'blocked' for t in tokens))
    d.metric('Alertas nas últimas 24h', sum(now-x['created_at'] <= 86400 for x in state['alerts']))
    alerts_tab, radar_tab, config_tab = st.tabs(['🔔 Alertas', '📡 Radar', '⚙️ Critérios e operação'])
    with alerts_tab:
        if not telegram_configured and not demo:
            st.info('Os alertas estão sendo registrados no painel. Configure Telegram no servidor para recebê-los com a aba fechada.')
        alerts = sorted(state['alerts'], key=lambda a:a['created_at'], reverse=True)[:50]
        if not alerts:
            st.info('Nenhum alerta registrado. O radar precisa confirmar os critérios em duas consultas antes de sinalizar uma candidata.')
        for alert in alerts:
            symbol = html.escape(str(alert['snapshot'].get('symbol', '?')))
            label = LABELS[alert['kind']]
            st.markdown(f'<div class="sniper-card"><p class="game-name">{symbol} · {label}</p><div class="meta-line">{stamp(alert["created_at"])} · Consulta registrada</div></div>', unsafe_allow_html=True)
            for reason in alert['reasons']:
                st.text('• ' + str(reason))
            st.code(alert['address'], language=None)
            if not demo:
                st.link_button('Abrir na GMGN', 'https://gmgn.ai/sol/token/' + alert['address'])
            delivery = {'sent':'Enviado ao Telegram','pending':'Pendente de envio ao Telegram',
                        'demo':'Simulação','failed':'Envio falhou','expired':'Alerta expirou para envio'}
            st.caption(delivery.get(alert.get('delivery'), 'Registrado no painel'))
            with st.expander('Dados no momento do alerta'):
                st.json(alert['snapshot'])
    with radar_tab:
        status_filter = st.selectbox('Exibir', ['Todos', *STATUS.values()], key='pump_filter')
        selected = [t for t in tokens if status_filter == 'Todos' or STATUS.get(t.get('status')) == status_filter]
        selected.sort(key=lambda t:(t.get('status') != 'candidate', -t.get('last_checked', 0)))
        if not selected:
            st.info('Nenhuma moeda nesta seleção. As listas de descoberta da GMGN cobrem uma amostra do mercado.')
        for token in selected[:60]:
            s = token.get('snapshot') or {}
            with st.expander(f"{s.get('symbol', token['address'][:8])} · {STATUS.get(token.get('status'), 'Na fila')}"):
                st.caption(f"Consulta: {stamp(s.get('observed_at'))} · Descoberta: {stamp(token['first_seen'])}")
                if s.get('observed_at') and now-s['observed_at'] > rules.confirmation_max_seconds:
                    st.warning('Consulta antiga. Aguarde nova avaliação.')
                m1,m2,m3 = st.columns(3)
                m1.metric('Liquidez', money(s.get('liquidity')))
                m2.metric('Valor de mercado', money(s.get('market_cap')))
                m3.metric('Volume em 5 min', money(s.get('volume_5m')))
                for reason in token.get('reasons', []):
                    st.text('• ' + reason)
                st.code(token['address'], language=None)
                if not demo:
                    st.link_button('Analisar na GMGN', 'https://gmgn.ai/sol/token/' + token['address'], key='open_'+token['address'])
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
        st.write('No Supabase: ciclos a cada 60 segundos, até 6 tokens por ciclo e até 30 em acompanhamento, com limite de duração por execução. Cada token pode levar vários ciclos para ser revisto, além da duração das consultas.')
        st.write('Alertas: candidata aos critérios, perda das condições observadas e indisponibilidade de dados. Um alerta de perda de condições não é uma ordem de venda nem acompanha sua carteira pessoal.')
        st.write('Esta versão realiza triagem determinística. Não inclui análise de narrativas por IA, execução de ordens ou cálculo de rentabilidade de operações simuladas.')
        st.caption('MVP pessoal: hospede com acesso restrito. A separação de contas e permissões para um SaaS público é uma etapa adicional.')
