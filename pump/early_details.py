"""Explain observed evidence without turning partial checks into a safety verdict."""
import re
import streamlit as st
from pump.criteria import number
from pump.radar_cards import stamp,usd


def pct(value):
    value=number(value)
    return 'Não verificado' if value is None else f'{value:.1f}%'


def rugcheck_summary(snapshot,now):
    risk=snapshot.get('risk') or {};report=risk.get('rugcheck') or {}
    at=number(risk.get('report_fetched_at'))
    available=report.get('status')=='reported' and at is not None and 0<=now-at<=1800
    critical=report.get('critical') or [];warnings=report.get('warnings') or [];other=report.get('other') or []
    if not available:
        return {'icon':'❔','text':'Aguardando relatório atual','available':False,'critical':[],'warnings':[],'other':[]}
    if critical:icon,text='⛔',f'{len(critical)} alerta(s) crítico(s) listado(s)'
    elif warnings or other:icon,text='⚠️',f'{len(warnings)+len(other)} aviso(s) · sem alertas críticos listados'
    else:icon,text='✓','Sem alertas listados no relatório'
    return {'icon':icon,'text':text,'available':True,'critical':critical,'warnings':warnings,'other':other}


def explanation(token,record,status,now):
    s=token.get('snapshot') or {};risk=s.get('risk') or {};checks=(record.get('assessment') or {}).get('checks') or []
    if record.get('tracking_stopped_at') or now-record.get('last_at',0)>120 or now<record.get('last_at',0):
        return 'A leitura está desatualizada. Aguarde nova consulta antes de usar os valores.'
    if status=='blocked':
        if s.get('mint_disabled') is False:return 'O contrato ainda permite emitir mais unidades do token.'
        if s.get('freeze_disabled') is False:return 'O contrato ainda permite congelar contas de tokens.'
        report=rugcheck_summary(s,now)
        if report['critical']:return 'Alerta crítico do RugCheck: '+str(report['critical'][0])
        lp=number(risk.get('lp_locked_pct'));top=number(risk.get('top10_ex_pool_pct'));creator=number(risk.get('creator_pool_claim_pct'))
        if lp is not None and lp<90:return f'A LP foi reportada com {pct(lp)} de proteção, abaixo do mínimo de 90% do filtro.'
        if top is not None and top>50:return f'As 10 maiores carteiras fora das pools somam {pct(top)}, acima do limite de 50% do filtro.'
        if creator is not None and creator>10:return f'O criador detém participação estimada de {pct(creator)} na oferta de referência da LP, acima do limite de 10%.'
        for c in checks:
            if c.get('state')=='blocked' and 'Estabilidade' in c.get('label',''):return 'A liquidez caiu mais de 20% em relação à primeira leitura ou à consulta anterior.'
        reasons=risk.get('reasons') or token.get('reasons') or []
        return str(reasons[0]) if reasons else 'Uma verificação identificou uma restrição. Veja os resultados abaixo.'
    if status=='extended':
        delta=number((record.get('assessment') or {}).get('price_since_first_pct'));recent=number(s.get('change_5m'))
        if delta is not None and delta>50:return f'O preço já subiu {delta:.1f}% desde a primeira leitura do teste; o limite para destaque é 50%.'
        if recent is not None and recent>40:return f'O preço subiu {recent:.1f}% em 5 minutos; o limite para destaque é 40%.'
        return 'O movimento avançou além dos limites da janela observada.'
    if status=='reviewed':return 'As verificações disponíveis foram atendidas em duas consultas. Abra o gráfico para avaliar o momento.'
    liquidity=number(s.get('liquidity'))
    if liquidity is not None and liquidity<25000:return f'A liquidez de {usd(liquidity)} está abaixo do mínimo de US$ 25.000 do filtro.'
    if s.get('mint_disabled') is None or s.get('freeze_disabled') is None:return 'Não foi possível verificar as permissões do contrato nesta leitura.'
    if s.get('extensions_review') is not False:return 'O programa ou as extensões do token ainda precisam de revisão.'
    if not rugcheck_summary(s,now)['available']:return 'O relatório de risco está indisponível ou aguardando atualização.'
    if risk.get('lp_chain_checked') is not True:return 'Não foi possível validar a LP desta pool com os dados disponíveis nesta consulta.'
    missing=[c for c in checks if c.get('state')=='unknown']
    if missing:return 'Falta verificar: '+', '.join(c['label'] for c in missing)+'.'
    sells=number(s.get('sell_count_5m'))
    if sells is None:return 'A quantidade de vendas dos últimos 5 minutos não está disponível.'
    if sells<=0:return 'Ainda não há vendas registradas pelo provedor nos últimos 5 minutos.'
    waiting=[c['label'] for c in checks if c.get('state')=='waiting']
    if waiting:return 'Ainda falta atender: '+', '.join(waiting)+'.'
    if status=='pending':return 'Há dados pendentes nesta consulta. Aguarde a próxima leitura.'
    return 'Aguardando duas consultas seguidas com todas as verificações iniciais atendidas; o total de observações não equivale a consultas válidas.'


def evidence_rows(snapshot,record):
    risk=snapshot.get('risk') or {};rows=[]
    def row(icon,label,value,meaning):rows.append((icon,label,value,meaning))
    lp=number(risk.get('lp_locked_pct'));top=number(risk.get('top10_ex_pool_pct'));creator=number(risk.get('creator_pool_claim_pct'))
    row('❔' if lp is None else '✓' if lp>=90 else '⛔','LP protegida, reportada',pct(lp),'Percentual informado como travado ou queimado para a pool selecionada. Não garante ausência de rug pull.')
    row('❔' if top is None else '✓' if top<=50 else '⛔','10 maiores carteiras fora das pools',pct(top),'Participação reportada por proprietário, excluindo contas identificadas como pools. Carteiras diferentes podem ter o mesmo controlador. Limite do filtro: 50%.')
    row('❔' if creator is None else '✓' if creator<=10 else '⛔','Participação estimada do criador na LP',pct(creator),'Participação na oferta de referência da LP. É diferente de deter 100% dos poucos tokens de LP que restaram após queimas. Limite do filtro: 10%.')
    for field,label,meaning in [('mint_disabled','Emissão de novos tokens','A permissão de criar mais unidades está desabilitada quando este item informa Desabilitada.'),('freeze_disabled','Permissão de congelar contas','A permissão de congelar contas de tokens está desabilitada quando este item informa Desabilitado.')]:
        value=snapshot.get(field)
        row('✓' if value is True else '⛔' if value is False else '❔',label,'Desabilitada' if value is True else 'Habilitada' if value is False else 'Não verificado',meaning)
    delta=number((record.get('assessment') or {}).get('liquidity_since_first_pct'))
    row('❔' if delta is None else '⛔' if delta < -20 else '✓','Liquidez desde a primeira leitura','Não disponível' if delta is None else f'{delta:+.1f}%','Compara liquidez em dólares. Queda pode acompanhar o preço e não comprova retirada de reservas. O filtro também verifica queda entre consultas.')
    sells=number(snapshot.get('sell_count_5m'))
    row('❔' if sells is None else '✓' if sells>0 else '○','Vendas registradas em 5 min','Não disponível' if sells is None else f'{sells:,.0f}','Quantidade reportada pelo provedor. Não simula a sua venda nem garante que ela seria executada.')
    return rows


def render_summary(snapshot,now):
    risk=snapshot.get('risk') or {};lp=number(risk.get('lp_locked_pct'));top=number(risk.get('top10_ex_pool_pct'))
    st.caption(('❔' if lp is None else '🔒')+' LP protegida, reportada: '+pct(lp))
    st.caption('👥 Top 10 fora das pools: '+pct(top))
    report=rugcheck_summary(snapshot,now)
    st.caption('🛡️ RugCheck · '+report['icon']+' '+report['text'])


def render_verifications(token,record,now):
    snapshot=token['snapshot'];risk=snapshot.get('risk') or {}
    for icon,label,value,meaning in evidence_rows(snapshot,record):
        st.write(f'{icon} **{label}: {value}**')
        st.caption(meaning)
    st.markdown('**🛡️ Relatório RugCheck**')
    report=rugcheck_summary(snapshot,now)
    st.write(report['icon']+' '+report['text'])
    for label,items in [('⛔ Crítico',report['critical']),('⚠️ Aviso',report['warnings']),('ℹ️ Outro aviso',report['other'])]:
        for item in items:st.text(label+': '+str(item))
    st.caption('Relatório consultado: '+stamp(risk.get('report_fetched_at'))+' · o provedor pode servir cache. Ausência de alertas não comprova segurança.')
    st.caption('LP consultada na Solana: '+(stamp(risk.get('checked_at')) if risk.get('lp_chain_checked') is True else 'consulta atual indisponível'))
    address=snapshot.get('address') or token.get('address')
    if isinstance(address,str) and re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}',address):
        st.link_button('Abrir relatório no RugCheck','https://rugcheck.xyz/tokens/'+address,use_container_width=True)
    reasons=list(dict.fromkeys((risk.get('reasons') or [])+(risk.get('warnings') or [])))
    if reasons:
        st.markdown('**Outras ocorrências da análise**')
        for reason in reasons:st.text('• '+str(reason))
