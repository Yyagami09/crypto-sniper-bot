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
.dex-risk{font-size:12px;line-height:1.5;padding:9px 10px;border:1px solid #6b5835;border-radius:7px;margin:2px 0 12px;color:#e0c692;background:#5d452018}.dex-risk.blocked{color:#ffb0ba;border-color:#9f4252;background:#ac344319}.dex-risk.reviewed{color:#bbcbd4;border-color:#3c535e;background:#1c343e33}.dex-whales{font-size:12px;line-height:1.6;border-top:1px solid #35424b;padding-top:10px;margin-top:10px;color:#becfe0}
[class*="st-key-dex_card_gold_"]{position:relative;isolation:isolate;overflow:hidden;background:radial-gradient(ellipse at 95% 0%,#76501e55,transparent 55%),linear-gradient(145deg,#2d2414,#191a15 60%,#242015)!important;border:1px solid #d5a849!important;box-shadow:0 0 0 1px #f9d76c1a,inset 0 1px 0 #fff1b733,0 8px 30px #d5a34220!important;animation:dex-gold-arrival .85s ease-out both}
[class*="st-key-dex_card_gold_"]:hover{border-color:#ffe29a!important;box-shadow:0 0 0 1px #ffdd7540,0 10px 36px #d5a34230!important}
[class*="st-key-dex_card_gold_"]::before{content:"";position:absolute;pointer-events:none;z-index:0;top:-20%;left:-90%;width:60%;height:140%;background:linear-gradient(90deg,transparent,#fff0b31c,transparent);transform:rotate(18deg);animation:dex-gold-sweep 1.6s .15s ease-out both}
[class*="st-key-dex_card_gold_"]>div{position:relative;z-index:1}
.dex-find{position:relative;display:flex;align-items:center;gap:10px;border-bottom:1px solid #b68b3b55;padding-bottom:14px;margin-bottom:15px}.dex-find-icon{display:grid;place-items:center;flex-shrink:0;width:40px;height:40px;border:1px solid #f9d46d88;border-radius:11px;background:linear-gradient(145deg,#dba94126,#aa702414);box-shadow:inset 0 1px 0 #ffe7a033;font-size:24px;animation:dex-pickaxe .65s .2s ease-out both}.dex-find-title{font-size:11px;line-height:1.5;font-weight:800;letter-spacing:1.5px;color:#ffdc83}.dex-find-subtitle{font-size:11px;line-height:1.5;color:#c9b88e;margin-top:2px}
.dex-gold-sparks{position:absolute;right:23px;top:21px;pointer-events:none}.dex-gold-sparks i{position:absolute;width:4px;height:4px;border-radius:1px;background:#ffda73;opacity:0;animation:dex-gold-sparks 1.35s .3s ease-out both}.dex-gold-sparks i:nth-child(1){--sx:19px;--sy:-21px}.dex-gold-sparks i:nth-child(2){--sx:-17px;--sy:-27px;animation-delay:.4s;background:#fff4c1}.dex-gold-sparks i:nth-child(3){--sx:29px;--sy:4px;width:3px;height:3px}.dex-gold-sparks i:nth-child(4){--sx:-27px;--sy:9px;animation-delay:.35s}.dex-gold-sparks i:nth-child(5){--sx:10px;--sy:22px;width:3px;height:3px;background:#fff4c1}
[class*="st-key-dex_card_gold_"] .dex-symbol{color:#ffe9ad}[class*="st-key-dex_card_gold_"] .dex-name,[class*="st-key-dex_card_gold_"] .dex-caption,[class*="st-key-dex_card_gold_"] .dex-score-label,[class*="st-key-dex_card_gold_"] .dex-fact-label,[class*="st-key-dex_card_gold_"] .dex-timestamp{color:#c9bb9a}[class*="st-key-dex_card_gold_"] .dex-status.candidate{background:#d8aa3c22;border:1px solid #d8aa3c66;color:#ffe5a4}[class*="st-key-dex_card_gold_"] .dex-score{color:#ffdf8a;text-shadow:0 0 20px #efbc4933}[class*="st-key-dex_card_gold_"] .dex-score small{color:#bdab7c}[class*="st-key-dex_card_gold_"] .dex-fact-value{color:#fff6dc}[class*="st-key-dex_card_gold_"] .dex-bar{background:#66532766}[class*="st-key-dex_card_gold_"] .dex-bar span{background:linear-gradient(90deg,#bb852e,#ffe49a,#dbaf4e)}[class*="st-key-dex_card_gold_"] .dex-facts,[class*="st-key-dex_card_gold_"] .dex-missing{border-color:#ae893d44}[class*="st-key-dex_card_gold_"] .dex-missing{color:#ead6a7}
@keyframes dex-gold-arrival{from{opacity:.4;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
@keyframes dex-gold-sweep{from{transform:translateX(0) rotate(18deg)}to{transform:translateX(420%) rotate(18deg)}}
@keyframes dex-pickaxe{0%{transform:rotate(-15deg)}55%{transform:rotate(9deg)}100%{transform:rotate(0)}}
@keyframes dex-gold-sparks{0%{opacity:0;transform:translate(0,0) rotate(45deg)}20%{opacity:.85}100%{opacity:0;transform:translate(var(--sx),var(--sy)) rotate(135deg)}}
@media(prefers-reduced-motion:reduce){[class*="st-key-dex_card_gold_"],[class*="st-key-dex_card_gold_"]::before,.dex-find-icon,.dex-gold-sparks i{animation:none!important}.dex-gold-sparks{display:none}[class*="st-key-dex_card_gold_"]::before{display:none}}
[class*="st-key-dex_card_gold_history_"],[class*="st-key-dex_card_gold_history_"] .dex-find-icon{animation:none!important}[class*="st-key-dex_card_gold_history_"]::before,[class*="st-key-dex_card_gold_history_"] .dex-gold-sparks{display:none}
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


def confirmed_find(token, model):
    return token.get('status')=='candidate' and model['score']==100 and not model['issue'] and not model['stale']


def card_markup(token, model, historical=False):
    s = token.get('snapshot') or {}
    status = token.get('status', 'queued')
    status = status if status in GROUPS else 'queued'
    label = 'Achado registrado · risco parcial' if historical else 'Consulta antiga' if model['stale'] else CARD_STATUS[status]
    symbol = html.escape(str(s.get('symbol') or token['address'][:8]))
    name = html.escape(str(s.get('name') or 'Nome indisponível'))
    badge_class = 'incomplete' if model['stale'] else status
    subtitle = html.escape('Solana · '+age_label(model['age_minutes']))
    risk = s.get('risk') or {}
    risk_status = risk.get('status') if risk.get('status') in ('blocked','reviewed') else 'pending'
    risk_label = {'blocked':'⛔ Risco crítico ou atividade atípica · sinal bloqueado','pending':'⏳ Camada de risco pendente · sinal retido',
                  'reviewed':'Triagem de risco parcial concluída · venda não simulada'}[risk_status]
    if risk.get('slow_rug',{}).get('status')=='warning':
        risk_label='⛔ Possível retirada gradual de liquidez · sinal retido'
    if historical and not risk:
        risk_label = 'Confirmação anterior à camada de risco · dados históricos'
    risk_markup = f'<div class="dex-risk {risk_status}">{html.escape(risk_label)}</div>'
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
    if historical:
        note = 'Dados preservados da confirmação. A situação atual pode ter mudado.'
    whales = s.get('whales') or {}
    whale_text = {'observing':'Grandes carteiras: coletando comparação de saldos','unchanged':'Grandes carteiras: saldos estáveis na amostra',
                  'unavailable':'Grandes carteiras: dados indisponíveis'}.get(whales.get('status'),'Grandes carteiras: dados indisponíveis')
    if whales.get('status')=='changes':
        whale_text = f'Grandes carteiras: {int(whales.get("increases",0))} aumentando · {int(whales.get("decreases",0))} reduzindo saldo'
    if whales.get('gradual_reductions'):
        whale_text += f' · redução gradual em {int(whales["gradual_reductions"])} carteira(s)'
    whale_markup = f'<div class="dex-whales">{html.escape(whale_text)}<div class="dex-caption">Indicador complementar · não altera a nota</div></div>'
    score_label = 'Aderência na confirmação' if historical else 'Aderência aos critérios'
    time_label = 'Dados na confirmação' if historical else 'Consulta'
    celebration = '<div class="dex-find"><span class="dex-find-icon" aria-hidden="true">⛏️</span><div><div class="dex-find-title">ACHADO NO GARIMPO</div><div class="dex-find-subtitle">7/7 critérios · duas consultas válidas</div></div><span class="dex-gold-sparks" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span></div>' if confirmed_find(token,model) else ''
    return f'{celebration}<div class="dex-head"><div><div class="dex-symbol">{symbol}</div><div class="dex-name">{name}</div></div></div><div class="dex-status {badge_class}">{html.escape(label)}</div>{risk_markup}<div class="dex-caption">{subtitle}</div><div class="dex-score-row"><span class="dex-score-label">{score_label}</span>{score}</div>{progress}<div class="dex-facts">{grid}</div><div class="dex-missing">{html.escape(note)}</div>{whale_markup}<div class="dex-timestamp">{time_label}: {stamp(s.get("observed_at"))} · Brasília</div>'


def details(token, model):
    s = token.get('snapshot') or {}
    with st.expander('Ver detalhes', expanded=False):
        st.caption('Cada critério vale 1/7 da nota. Pontuação arredondada; não estima lucro ou segurança.')
        for check in model['checks']:
            mark = '✅' if check['passed'] is True else '❌' if check['passed'] is False else '➖'
            st.text(f'{mark} {check["label"]}: {check["value"]} · {check["target"]}')
        st.markdown('**Verificações e situação registrada**')
        risk = s.get('risk') or {}
        st.caption('Venda não simulada. Triagem parcial; não comprova ausência de honeypot ou manipulação.')
        if risk:
            st.caption('Consulta do relatório: '+stamp(risk.get('report_fetched_at'))+' · pode estar em cache na origem. LP na cadeia: '+(stamp(risk.get('checked_at')) if risk.get('lp_chain_checked') else 'consulta indisponível'))
            for label,field in [('LP reportada travada/queimada','lp_locked_pct'),('Tokens de LP circulantes na carteira do criador (amostra)','creator_lp_pct'),('Participação estimada do criador na oferta de referência da LP','creator_pool_claim_pct'),('Top 10 fora das pools, reportado','top10_ex_pool_pct')]:
                value = number(risk.get(field))
                st.text(label+': '+('Indisponível' if value is None else f'{value:.2f}%'))
            for reason in risk.get('reasons',[])+risk.get('warnings',[]):
                st.text('• '+str(reason))
            trend = risk.get('slow_rug') or {}
            st.caption('Retirada gradual: '+{'collecting':'coletando observações','no_pattern':'sem padrão detectado na janela','warning':'padrão atípico detectado'}.get(trend.get('status'),'dados indisponíveis'))
            if trend.get('observations'):
                st.caption(f"{trend['observations']} observações · janela de {trend.get('window_minutes',0):.0f} min. Ausência de padrão não comprova ausência de slow rug.")
        st.markdown('**Movimentação de grandes carteiras**')
        whales = s.get('whales') or {}
        st.caption('Até 5 contas de detentores fora das pools. Destaque para ≥1% da oferta ou saldo estimado de ≥US$ 10 mil. Variação de saldo pode ser transferência; não comprova compra/venda e não altera os sete critérios.')
        items = whales.get('items',[])
        if items:
            rows = []
            for item in items:
                delta = number(item.get('delta_usd'))
                rows.append({'Carteira':item['wallet'],'Contas monitoradas':item.get('account_count'),
                    '% da oferta na amostra':item.get('pct_supply'),'Saldo estimado (USD)':item.get('value_usd'),
                    'Variação de saldo (tokens)':item.get('delta_tokens'),'Variação estimada ao preço atual (USD)':delta,
                    'Leitura':{'baseline':'Aguardando comparação','increase':'Saldo aumentou','decrease':'Saldo diminuiu','unchanged':'Saldo estável'}.get(item.get('direction'),'Indisponível'),
                    'Redução gradual na janela':bool(item.get('gradual_reduction'))})
            st.dataframe(rows,hide_index=True,use_container_width=True)
        else:
            st.caption('Sem comparação disponível nesta consulta. Ausência de dados não significa ausência de grandes carteiras.')
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
                variant = 'gold' if confirmed_find(token,model) else group
                with column, st.container(border=True,key='dex_card_'+variant+'_'+token['address']):
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
