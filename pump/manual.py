"""Authenticated, on-demand reports; does not change the shared radar."""
import time
import streamlit as st
from pump.networks import NETWORKS
from pump.radar_cards import usd,stamp
from pump.early_details import render_summary,render_verifications
from pump.criteria import number

OBJECTIVES={'general':'Análise geral','risk':'Riscos do contrato','reentry':'Possível reentrada'}


def price(value):
    value=number(value)
    return 'Indisponível' if value is None else 'US$ '+format(value,'.10g')


def render():
    from pump.account import ensure_session,action,AccountError
    from pump.dashboard_ui import CSS
    if not ensure_session():
        st.warning('Entre novamente para consultar um contrato.')
        return
    st.markdown(CSS,unsafe_allow_html=True)
    st.markdown("<div class='dex-workspace-head'><h1>Analisar contrato</h1><p>Uma consulta pontual, sem alterar seu radar.</p></div>",unsafe_allow_html=True)
    with st.form('manual_contract_form'):
        left,right=st.columns(2)
        chain=left.selectbox('Rede blockchain',list(NETWORKS),format_func=NETWORKS.get,key='manual_chain')
        objective=right.selectbox('O que você quer avaliar?',list(OBJECTIVES),format_func=OBJECTIVES.get,key='manual_objective')
        contract=st.text_input('Contrato do token ou link do DEX Screener',placeholder='Cole o contrato ou o link do par',max_chars=300,key='manual_contract')
        submit=st.form_submit_button('Analisar agora',type='primary',use_container_width=True)
    st.caption('Consultas com intervalo mínimo de 30 segundos. O resultado é uma leitura pontual; não adiciona moedas ao radar nem envia notificações.')
    if submit:
        st.session_state.pop('manual_result',None)
        if not contract.strip():
            st.warning('Cole o contrato ou o link do par para continuar.')
        else:
            try:
                with st.spinner('Consultando mercado, verificações disponíveis e histórico do gráfico…'):
                    result=action('analyze_contract',chain=chain,input=contract.strip(),objective=objective)['analysis']
                st.session_state.manual_result=result
            except AccountError as exc:st.error(str(exc))
    report=st.session_state.get('manual_result')
    if not report:return
    render_report(report)


def render_report(report):
    now=time.time();s=report['snapshot'];verdict=report['verdict'];chart=report['chart']
    st.divider()
    st.subheader(str(s.get('symbol','?'))+' · '+NETWORKS.get(report['chain'],report['chain']))
    st.caption(OBJECTIVES.get(report['objective'],report['objective'])+' · Consulta: '+stamp(report['queried_at'])+' · Brasília')
    if now-report['queried_at']>180:st.warning('Este resultado tem mais de três minutos. Consulte novamente para atualizar os dados.')
    {'red':st.error,'yellow':st.warning,'gray':st.info,'blue':st.info}.get(verdict['tone'],st.info)('**'+verdict['title']+'**\n\n'+verdict['text'])
    for i,(column,(label,value)) in enumerate(zip(st.columns(4),[
        ('Preço',price(s.get('price'))),('Liquidez',usd(s.get('liquidity'))),
        (s.get('valuation_type','Avaliação'),usd(s.get('valuation'))),('Volume · 5 min',usd(s.get('volume_5m')))])):
        with column,st.container(border=True,key='dex_summary_manual_'+str(i)):st.metric(label,value)
    st.caption('Contrato consultado: '+s['address'])
    st.link_button('Abrir gráfico no DEX Screener',s['pair_url'],type='primary',use_container_width=True)
    summary,graph,risk,sources=st.tabs(['📋 Leitura rápida','📈 Gráfico e reentrada','🛡️ Verificações','ℹ️ Fontes e limites'])
    with summary:
        st.write('**O que os dados mostram agora**')
        st.write('Compras / vendas em 5 min: '+str(s.get('buy_count_5m','—'))+' / '+str(s.get('sell_count_5m','—'))+' transações. Quantidade não equivale a volume financeiro ou participantes únicos.')
        change=number(s.get('change_5m'))
        st.write('Variação em 5 min: '+('Não disponível' if change is None else f'{change:+.1f}%'))
        if report['chain']=='solana':render_summary(s,now)
        else:st.info('Nesta rede, a consulta cobre mercado e histórico quando disponíveis. Contrato, LP, concentração e RugCheck não são verificados.')
        if report['objective']=='reentry':st.caption('Veja em Gráfico e reentrada as referências da janela. Queda em relação ao topo, isoladamente, não confirma uma entrada favorável.')
        else:st.caption('Uma consulta não confirma continuidade, preço favorável ou possibilidade de executar sua ordem.')
    with graph:
        if chart['status']=='not_requested':
            st.info('O foco escolhido consulta os riscos. Selecione Análise geral ou Possível reentrada para solicitar também os candles.')
        elif chart['status']!='available':
            st.info('Histórico insuficiente para avaliar reentrada. '+chart['reason'])
        else:
            st.caption(f"{len(chart['candles'])} candles completos de 1 min. Referências calculadas sobre até {chart['window_minutes']:.0f} minutos, em preço USD, sem conversão para market cap.")
            import pandas as pd
            frame=pd.DataFrame(chart['candles'],columns=['Horário','Abertura','Máxima','Mínima','Fechamento','Volume'])
            frame['Horário']=pd.to_datetime(frame['Horário'],unit='s',utc=True).dt.tz_convert('America/Sao_Paulo')
            st.line_chart(frame.set_index('Horário')[['Fechamento']],y_label='Preço de fechamento (USD)')
            st.write('**Referência inferior observada:** '+price(chart['lower_reference']))
            st.write('**Máxima anterior da janela:** '+price(chart['upper_reference']))
            st.caption('As referências excluem os três últimos candles. Não representam suportes, resistências, alvos ou stops confirmados.')
            st.write(('✓' if chart['higher_lows_last3'] else '○')+' As mínimas dos três últimos candles '+('aumentaram.' if chart['higher_lows_last3'] else 'não formam uma sequência ascendente.'))
            st.write(('✓' if chart['close_above_prior_high'] else '○')+' O último fechamento '+('superou' if chart['close_above_prior_high'] else 'não superou')+' a máxima anterior da janela.')
            st.write(f"Distância da máxima observada na janela: {chart['change_from_window_high_pct']:+.1f}%")
            ratio=number(chart.get('volume_last5_vs_prior5'))
            st.write('Volume dos últimos 5 candles / 5 anteriores: '+('Não comparável' if ratio is None else f'{ratio:.2f}×'))
            st.caption('Uma sequência local de melhora ainda pode falhar. Liquidez, taxas, impacto da ordem e execução não estão simulados.')
    with risk:
        if report['chain']=='solana':
            render_verifications({'address':s['address'],'snapshot':s},{'assessment':{}},now)
            whales=s.get('whales') or {}
            if whales.get('items'):
                with st.expander('Amostra de grandes detentores'):
                    st.caption('Saldos de uma única consulta. Sem comparação temporal, não é possível afirmar entrada ou saída de carteiras.')
                    st.dataframe([{'Carteira':w['wallet'],'% da oferta':w['pct_supply'],'Saldo estimado (USD)':w['value_usd']} for w in whales['items']],hide_index=True,use_container_width=True)
        else:st.info('Verificadores de risco ainda não adaptados a esta rede. Dados indisponíveis não recebem aprovação.')
    with sources:
        for issue in report.get('source_errors',[]):st.write('• '+str(issue))
        st.caption('Mercado: DEX Screener · Candles: GeckoTerminal · Solana: RPC público e RugCheck, quando disponíveis.')
        for limitation in report.get('limitations',[]):st.write('• '+str(limitation))
