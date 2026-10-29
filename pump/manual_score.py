"""Transparent presentation score. Missing evidence never earns points."""
import html
import streamlit as st
from pump.criteria import number
from pump.early_details import rugcheck_summary
from pump.radar_cards import usd


def evaluate(report, now):
    s=report.get('snapshot') or {};r=s.get('risk') or {};chart=report.get('chart') or {}
    queried=number(report.get('queried_at'))
    fresh=queried is not None and 0<=now-queried<=180
    sol=report.get('chain')=='solana';rows=[]
    report_ok=sol and fresh and rugcheck_summary(s,now)['available']
    lp_at=number(r.get('checked_at'))
    lp_ok=report_ok and r.get('lp_chain_checked') is True and lp_at is not None and 0<=now-lp_at<=120
    def add(label,weight,state,value,target):
        state=state if fresh else 'unknown'
        rows.append(dict(label=label,weight=weight,state=state,value=value if fresh else 'Consulta desatualizada',target=target,points=weight if state=='pass' else 0))
    def boolean(label,field,weight,desired=True):
        v=s.get(field) if sol else None
        state='unknown' if not isinstance(v,bool) else 'pass' if v is desired else 'fail'
        add(label,weight,state,'Verificado' if state=='pass' else 'Não atende' if state=='fail' else 'Não verificado',
            'Permissão desabilitada' if field!='extensions_review' else 'Programa e extensões sem revisão pendente')
    boolean('Emissão de novos tokens', 'mint_disabled',10)
    boolean('Congelamento de contas', 'freeze_disabled',10)
    boolean('Programa e extensões', 'extensions_review',5,False)
    rc=rugcheck_summary(s,now)
    state='unknown' if not report_ok else 'fail' if rc['critical'] else 'attention' if rc['warnings'] or rc['other'] else 'pass'
    add('RugCheck',10,state,rc['text'] if sol else 'Sem cobertura nesta rede','Relatório recente sem alertas listados')
    def percent(label,key,weight,limit,minimum=False,available=False):
        v=number(r.get(key)) if available else None
        valid=v is not None and 0<=v<=100
        state='unknown' if not valid else 'pass' if (v>=limit if minimum else v<=limit) else 'fail'
        add(label,weight,state,'Não verificado' if not valid else f'{v:.1f}%',('Mínimo ' if minimum else 'Máximo ')+str(limit)+'%')
    percent('LP protegida, reportada','lp_locked_pct',15,90,True,lp_ok)
    percent('Top 10 fora das pools','top10_ex_pool_pct',10,50,available=report_ok)
    percent('Participação do criador na LP de referência','creator_pool_claim_pct',10,10,available=lp_ok)
    liquidity=number(s.get('liquidity'));price=number(s.get('price'))
    add('Liquidez disponível',10,'unknown' if liquidity is None or liquidity<0 or price is None or price<=0 else 'pass' if liquidity>=25000 else 'fail',usd(liquidity),'Mínimo US$ 25.000')
    sells=number(s.get('sell_count_5m'))
    add('Vendas registradas em 5 min',5,'unknown' if sells is None or sells<0 else 'pass' if sells>0 else 'attention',str(int(sells)) if sells is not None and sells>=0 else 'Não disponível','Pelo menos uma venda reportada; sua venda não foi simulada')
    volume=number(s.get('volume_5m'))
    ratio=volume/liquidity if volume is not None and volume>=0 and liquidity is not None and liquidity>0 else None
    add('Giro de volume / liquidez · 5 min',5,'unknown' if ratio is None else 'fail' if ratio>10 else 'attention' if ratio>5 else 'pass','Não disponível' if ratio is None else f'{ratio:.2f}×','Até 5× atende; acima de 10× é restrição experimental, sem comprovar manipulação')
    if report.get('objective')!='risk':
        candles=chart.get('candles') or []
        last=number(candles[-1][0]) if candles and isinstance(candles[-1],list) and candles[-1] else None
        chart_ok=chart.get('status')=='available' and last is not None and 0<=now-last<=180
        higher=chart.get('higher_lows_last3')
        add('Recuperação nas mínimas do gráfico',5,'unknown' if not chart_ok or not isinstance(higher,bool) else 'pass' if higher else 'attention','Três mínimas ascendentes' if chart_ok and higher is True else 'Sem sequência ascendente' if chart_ok and higher is False else 'Histórico insuficiente ou antigo','Três mínimas consecutivas ascendentes; não confirma reversão')
        v=number(chart.get('volume_last5_vs_prior5')) if chart_ok else None
        add('Volume recente do gráfico',5,'unknown' if v is None or v<0 else 'pass' if v>=1 else 'attention','Não comparável' if v is None else f'{v:.2f}×','Últimos 5 candles com volume igual ou maior que os 5 anteriores')
    total=sum(x['weight'] for x in rows);score=round(100*sum(x['points'] for x in rows)/total)
    missing=[x['label'] for x in rows if x['state']=='unknown']
    failed=[x['label'] for x in rows if x['state']=='fail']
    attention=[x['label'] for x in rows if x['state']=='attention']
    backend_blocked=fresh and (r.get('status')=='blocked' or (report.get('verdict') or {}).get('tone')=='red')
    if not fresh:title,tone,reason='Consulta desatualizada','gray','Consulte novamente para recalcular a leitura.'
    elif failed or backend_blocked:
        title,tone='Desfavorável na triagem','red'
        reason='Não atende: '+', '.join(failed)+'.' if failed else 'O verificador identificou uma restrição. Veja os detalhes técnicos.'
    elif missing or not sol or r.get('status')!='reviewed' or price is None or price<=0:
        title,tone='Dados insuficientes para concluir','gray'
        reason='Falta verificar: '+', '.join(missing)+'.' if missing else 'A verificação completa de risco ou o preço ainda está pendente.'
    elif attention:
        title,tone='Atenção · ainda sem leitura favorável','yellow'
        reason='Precisa de atenção: '+', '.join(attention)+'.'
    else:
        title,tone='Favorável na triagem de risco' if report.get('objective')=='risk' else 'Favorável para observar','green'
        reason='Os itens desta consulta atenderam aos filtros. '+('O momento de entrada não foi avaliado neste foco.' if report.get('objective')=='risk' else 'Abra o gráfico para avaliar continuidade e execução.')
    return dict(rows=rows,score=score,total=total,title=title,tone=tone,reason=reason,missing=len(missing),checked=sum(x['state']!='unknown' for x in rows),partial=bool(missing) or not fresh)


def render_card(report, now):
    model=evaluate(report,now);s=report['snapshot']
    color={'green':'#4bd3a4','red':'#f18b99','yellow':'#ebc06a','gray':'#a5b4c7'}[model['tone']]
    esc=lambda value:html.escape(str(value))
    st.markdown('''<style>[class*="st-key-manual_verdict_card"]{background:#141c25;border:1px solid #354452!important;border-radius:16px!important;padding:22px!important}.manual-score-head{display:flex;justify-content:space-between;gap:20px;align-items:center}.manual-score-title{font-size:22px;font-weight:750}.manual-score-number{font-size:36px;font-weight:800;white-space:nowrap}.manual-score-number small{font-size:15px;color:#9aaabc}</style>''',unsafe_allow_html=True)
    with st.container(border=True,key='manual_verdict_card'):
        st.caption('RESUMO DA MOEDA · '+str(s.get('symbol','?')))
        st.markdown(f'<div class="manual-score-head"><div class="manual-score-title" style="color:{color}">{esc(model["title"])}</div><div class="manual-score-number" style="color:{color}">{model["score"]}<small>/100</small></div></div>',unsafe_allow_html=True)
        st.write(model['reason'])
        st.caption(('Pontuação parcial' if model['partial'] else 'Aderência aos filtros')+f' · {model["checked"]}/{len(model["rows"])} itens verificados · {model["missing"]} pendentes')
        st.progress(model['score']/100)
        left,right=st.columns(2)
        with left:
            st.write('**Liquidez:** '+usd(s.get('liquidity')))
            st.write('**'+str(s.get('valuation_type','Avaliação'))+':** '+usd(s.get('valuation')))
        with right:
            st.write('**Compras / vendas · 5 min:** '+str(s.get('buy_count_5m','—'))+' / '+str(s.get('sell_count_5m','—')))
            change=number(s.get('change_5m'))
            st.write('**Variação · 5 min:** '+('Não disponível' if change is None else f'{change:+.1f}%'))
        st.caption('Nota de critérios atendidos, não probabilidade de lucro ou segurança. Uma restrição prevalece sobre a nota. Dados ausentes valem zero; não são prova de risco. Não é indicação de compra.')
        with st.expander('Itens checados e composição da pontuação',expanded=True):
            icons={'pass':'✅','fail':'⛔','unknown':'❔','attention':'⚠️'}
            st.dataframe([{'Item':icons[x['state']]+' '+x['label'],'Resultado':x['value'],'Critério':x['target'],'Pontos':f'{x["points"]}/{x["weight"]}'} for x in model['rows']],hide_index=True,use_container_width=True)
            st.caption(f'Soma dos pesos: {model["total"]}. Nota = pontos atendidos ÷ soma dos pesos × 100. Avisos e pendências não pontuam. No foco de risco, os candles não entram na nota. Limites experimentais, sem validação de rentabilidade.')
    return model
