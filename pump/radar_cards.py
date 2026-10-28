import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from pump.criteria import adherence, number

GROUPS = {'candidate':'Sinais confirmados', 'confirming':'Aguardando confirmação',
          'watch':'Em observação', 'incomplete':'Dados insuficientes',
          'blocked':'Rejeitadas', 'queued':'Na fila'}
CARD_STATUS = {**GROUPS,'candidate':'Sinal confirmado · risco parcial','blocked':'Rejeitada'}
CSS = '''<style>
[class*="st-key-dex_card_"]{background:linear-gradient(145deg,#141d25,#10161c);border:1px solid #26343f!important;border-radius:14px!important;padding:17px!important;height:100%}
[class*="st-key-dex_card_"]:hover{border-color:#426575!important}
.dex-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.dex-symbol{font-size:23px;font-weight:750;letter-spacing:-.5px;color:#f5f8fa;overflow-wrap:anywhere}.dex-name{font-size:12px;color:#92a5b6;margin:2px 0 12px;overflow-wrap:anywhere}
.dex-status{display:inline-block;font-size:11px;line-height:1.4;padding:5px 8px;border-radius:6px;background:#172e40;color:#a1ceee;margin-bottom:12px}.dex-status.candidate{background:#0c3429;color:#83ebbc}.dex-status.confirming{background:#352e16;color:#efd581}.dex-status.blocked{background:#381f25;color:#f3a5b2}.dex-status.incomplete,.dex-status.queued{background:#252b32;color:#aab6c3}
.dex-score-row{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-top:4px}.dex-score-label{font-size:12px;color:#a2b3c0}.dex-score{font-size:24px;font-weight:750;color:#eaf5f3}.dex-score small{font-size:12px;color:#91a5b5;font-weight:400}.dex-score-pending{font-size:13px;color:#d3b88b}
.dex-bar{height:5px;border-radius:4px;overflow:hidden;background:#273540;margin:8px 0 5px}.dex-bar span{display:block;height:100%;background:#38c8b0}.dex-caption{font-size:11px;color:#8fa4b4;line-height:1.5}
.dex-facts{display:grid;grid-template-columns:1fr 1fr;gap:13px 12px;border-top:1px solid #293541;margin-top:14px;padding-top:14px}.dex-fact-label{font-size:11px;color:#93a8b8}.dex-fact-value{font-size:16px;color:#edf4f9;font-weight:650;margin-top:3px;overflow-wrap:anywhere}.dex-missing{border-top:1px solid #293541;margin-top:14px;padding-top:12px;font-size:12px;color:#c9d5df;min-height:44px;line-height:1.6}.dex-timestamp{font-size:11px;color:#8b9faf;margin:10px 0 4px}
</style>'''


def usd(value):
    value = number(value)
    return '—' if value is None else f'US$ {value:,.0f}'


def stamp(value):
    value = number(value)
    return datetime.fromtimestamp(value, ZoneInfo('America/Sao_Paulo')).strftime('%d/%m %H:%M:%S') if value and value>0 else '—'


def age_label(age):
    if age is None:
        return 'Idade indisponível'
    if age<60:
        return f'{int(age)} min de pool'
    if age<1440:
        return f'{age/60:.1f} h de pool'
    return f'{age/1440:.1f} dias de pool'


def chart_url(token):
    s = token.get('snapshot') or {}
    for address in (s.get('pair_address'), token.get('address')):
        if isinstance(address, str) and re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', address):
            return 'https://dexscreener.com/solana/'+address
    return None


def card_markup(token, model):
    s = token.get('snapshot') or {}
    status = token.get('status', 'queued')
    status = status if status in GROUPS else 'queued'
    label = 'Consulta antiga' if model['stale'] else CARD_STATUS[status]
    symbol = html.escape(str(s.get('symbol') or token['address'][:8]))
    name = html.escape(str(s.get('name') or 'Nome indisponível'))
    badge_class = 'incomplete' if model['stale'] else status
    subtitle = html.escape('Solana · '+age_label(model['age_minutes']))
    if model['score'] is None:
        score = f'<div class="dex-score-pending">{html.escape(model["issue"])}</div>'
        progress = '<div class="dex-caption">A nota depende de dados completos e verificações válidas.</div>'
    else:
        score = f'<div class="dex-score">{model["score"]}<small> / 100</small></div>'
        progress = f'<div class="dex-bar" role="meter" aria-label="Aderência aos critérios" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{model["score"]}"><span style="width:{model["score"]}%"></span></div><div class="dex-caption">{model["passed"]} de 7 critérios atendidos · pesos iguais</div>'
    change = number(s.get('change_5m'))
    buys, sells = number(s.get('buy_count_5m')), number(s.get('sell_count_5m'))
    count = '—' if buys is None or sells is None else f'{buys:,.0f} / {sells:,.0f}'
    permissions = ('Restrição detectada' if s.get('mint_disabled') is False or s.get('freeze_disabled') is False else
                   'Pendentes' if s.get('mint_disabled') is not True or s.get('freeze_disabled') is not True or s.get('extensions_review') is not False else 'Sem restrição detectada')
    facts = [('Liquidez',usd(s.get('liquidity'))),('Volume · 5 min',usd(s.get('volume_5m'))),
             ('Variação · 5 min','—' if change is None else f'{change:+.2f}%'),
             (s.get('valuation_type') or 'Avaliação',usd(s.get('valuation'))),
             ('Compras / vendas · qtd.',count),('Permissões básicas',permissions)]
    grid = ''.join(f'<div><div class="dex-fact-label">{html.escape(str(k))}</div><div class="dex-fact-value">{html.escape(v)}</div></div>' for k,v in facts)
    missing = [c['label'] for c in model['checks'] if c['passed'] is False]
    if model['issue']:
        note = '; '.join(str(r) for r in token.get('reasons', [])[:2]) or model['issue']
        if model['stale']:
            note = 'Consulta antiga. Aguarde nova avaliação para comparar os critérios.'
    elif status=='confirming':
        note = '7/7 atendidos. Falta a segunda consulta válida para confirmar o sinal.'
    elif status=='candidate':
        note = 'Confirmado em duas consultas. Avaliação de risco parcial.'
    else:
        note = 'Falta atender: '+', '.join(missing) if missing else 'Confira as verificações nos detalhes.'
    return f'<div class="dex-head"><div><div class="dex-symbol">{symbol}</div><div class="dex-name">{name}</div></div></div><div class="dex-status {badge_class}">{html.escape(label)}</div><div class="dex-caption">{subtitle}</div><div class="dex-score-row"><span class="dex-score-label">Aderência aos critérios</span>{score}</div>{progress}<div class="dex-facts">{grid}</div><div class="dex-missing">{html.escape(note)}</div><div class="dex-timestamp">Consulta: {stamp(s.get("observed_at"))} · Brasília</div>'


def details(token, model):
    s = token.get('snapshot') or {}
    with st.expander('Ver detalhes', expanded=False):
        st.caption('Cada critério vale 1/7 da nota. Pontuação arredondada; não estima lucro ou segurança.')
        for check in model['checks']:
            mark = '✅' if check['passed'] is True else '❌' if check['passed'] is False else '➖'
            st.text(f'{mark} {check["label"]}: {check["value"]} · {check["target"]}')
        st.markdown('**Verificações e situação registrada**')
        for reason in token.get('reasons', []):
            st.text('• '+str(reason))
        st.caption('Descoberta: '+stamp(token.get('first_seen')))
        st.code(token['address'], language=None)
        history = token.get('history', [])
        if len(history)>1:
            import pandas as pd
            frame = pd.DataFrame(history)
            if 'price' in frame and 'observed_at' in frame:
                frame['Consulta'] = pd.to_datetime(frame['observed_at'], unit='s', utc=True).dt.tz_convert('America/Sao_Paulo')
                st.line_chart(frame.set_index('Consulta')[['price']], y_label='Preço consultado (USD)')
        st.json(s, expanded=False)


def render_radar(tokens, rules, now, demo=False):
    st.markdown(CSS, unsafe_allow_html=True)
    entries = [(t,adherence(t,rules,now)) for t in tokens]
    # A stale candidate is not presented as a current confirmed opportunity.
    def category(entry):
        return 'incomplete' if entry[1]['stale'] else entry[0].get('status', 'queued')
    a,b,c = st.columns([2,2,1.5])
    with a:
        chosen = st.selectbox('Situação', ['Todas', *GROUPS.values()], key='dex_group_filter')
    with b:
        order = st.selectbox('Ordenar por', ['Maior aderência','Maior liquidez','Maior volume em 5 min','Consulta mais recente'], key='dex_order')
    with c:
        view = st.radio('Visualização', ['Cards','Tabela'], horizontal=True, key='dex_view')
    query = st.text_input('Buscar moeda ou contrato', placeholder='Nome, ticker ou endereço', key='dex_search').strip().casefold()
    st.caption('Aderência = critérios atendidos ÷ 7 × 100. Não representa probabilidade de lucro ou nota de segurança. 100/100 ainda exige confirmação em duas consultas.')
    if query:
        entries = [e for e in entries if query in ' '.join(str((e[0].get('snapshot') or {}).get(k,'')) for k in ('symbol','name')).casefold() or query in e[0]['address'].casefold()]
    entries = [e for e in entries if chosen=='Todas' or GROUPS.get(category(e))==chosen]
    def sort_key(entry):
        t,m = entry
        s = t.get('snapshot') or {}
        if order=='Maior aderência':
            value = m['score'] if m['score'] is not None else -1
        else:
            field = {'Maior liquidez':'liquidity','Maior volume em 5 min':'volume_5m','Consulta mais recente':'observed_at'}[order]
            value = number(s.get(field))
            value = -1 if value is None else value
        return (-value,-(number(t.get('last_checked')) or 0),t['address'])
    entries.sort(key=sort_key)
    if not entries:
        st.info('Nenhuma moeda nesta seleção. A descoberta gratuita cobre uma amostra de pools novas e perfis recentes, que podem ser promocionais.')
        return
    if view=='Tabela':
        rows = []
        for token,model in entries:
            s = token.get('snapshot') or {}
            rows.append({'Moeda':s.get('symbol','?'),'Situação':GROUPS.get(category((token,model))),
                'Aderência (/100)':model['score'],'Critérios':f'{model["passed"]}/7' if model['score'] is not None else model['issue'],
                'Liquidez (USD)':s.get('liquidity'),'Volume 5min (USD)':s.get('volume_5m'),
                'Variação 5min (%)':s.get('change_5m'),'Tipo de avaliação':s.get('valuation_type'),
                'Avaliação (USD)':s.get('valuation'),'Consulta':stamp(s.get('observed_at'))})
        st.dataframe(rows, hide_index=True, use_container_width=True)
        for token,model in entries:
            with st.container(border=True):
                st.write(str((token.get('snapshot') or {}).get('symbol') or token['address'][:8]))
                url = chart_url(token)
                if url and not demo:
                    st.link_button('Abrir gráfico', url)
                details(token,model)
        return
    def grid(items, group):
        for start in range(0,len(items),3):
            columns = st.columns(3)
            for column,(token,model) in zip(columns,items[start:start+3]):
                with column, st.container(border=True,key='dex_card_'+group+'_'+token['address']):
                    st.markdown(card_markup(token,model), unsafe_allow_html=True)
                    url = chart_url(token)
                    if url and not demo:
                        st.link_button('Abrir gráfico', url, use_container_width=True)
                    details(token,model)
    for group,title in GROUPS.items():
        items = [e for e in entries if category(e)==group]
        if not items:
            continue
        if group in ('blocked','incomplete','queued'):
            with st.expander(f'{title} · {len(items)}', expanded=chosen!='Todas'):
                grid(items,group)
        else:
            st.subheader(f'{title} · {len(items)}')
            grid(items,group)
