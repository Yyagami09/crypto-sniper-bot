"""Early discovery experiment; classic screening stays independently available."""
import html
import time
import streamlit as st
from pump.storage import StorageError
from pump.radar_cards import chart_url, usd, stamp
from pump.criteria import number

MODES={'early-v1':'Antecipado · experimental','classic':'Clássico'}
STATUS={'pending':'Dados pendentes','blocked':'Restrição identificada','observing':'Em observação',
        'reviewed':'Triagem inicial atendida','extended':'Movimento avançado'}


def save_mode(mode):
    from pump.account import action,AccountError
    try:
        profile=action('radar_mode',mode=mode)['profile']
        st.session_state.sniper_profile=profile
        st.session_state.pop('dex_mode_choice',None)
        return True
    except (AccountError,KeyError):
        st.error('Não foi possível salvar o modo. A configuração anterior foi mantida.')
        return False


def mode_options():
    current=st.session_state.get('sniper_profile',{}).get('radar_mode','classic')
    if st.session_state.get('dex_mode_saved')!=current:
        st.session_state.dex_mode_choice=current
        st.session_state.dex_mode_saved=current
    chosen=st.selectbox('Modo do radar',list(MODES),index=list(MODES).index(current),format_func=MODES.get,key='dex_mode_choice')
    if st.button('Aplicar modo',key='dex_apply_mode',disabled=chosen==current):
        if save_mode(chosen):st.rerun()
    st.caption('Clássico restaura a visualização e os avisos anteriores para sua conta. O teste não altera seus sete critérios.')


def experiment_tokens(state,now):
    combined={**state.get('tokens',{}),**(state.get('early_tokens') or {})}
    entries=[]
    for t in combined.values():
        record=t.get('early')
        if not record:continue
        status=record.get('status','pending')
        if now-record.get('last_at',0)>180 or record.get('tracking_stopped_at'):status='pending'
        entries.append((t,record,status))
    return sorted(entries,key=lambda e:({'reviewed':0,'observing':1,'pending':2,'extended':3,'blocked':4}.get(e[2],5),-e[1].get('first_at',0)))


def render_experiment(store,state,now):
    from pump.dashboard_ui import status_line,operation_details
    status_line(state.get('run',{}),now,stamp,mode='Antecipado · experimental · Solana')
    entries=experiment_tokens(state,now)
    for i,(column,(label,value)) in enumerate(zip(st.columns(4),[
        ('Em acompanhamento',len(entries)),('Triagem inicial atendida',sum(s=='reviewed' for _,_,s in entries)),
        ('Dados pendentes',sum(s=='pending' for _,_,s in entries)),('Restrições identificadas',sum(s=='blocked' for _,_,s in entries))])):
        with column,st.container(border=True,key='dex_summary_early_'+str(i)):st.metric(label,value)
    radar,comparison,alerts,operation=st.tabs(['📡 Descobertas','🧪 Comparação','🔔 Alertas','⚙️ Operação'])
    experimental_alerts=[a for a in state.get('alerts',[]) if a['kind'] in ('early_watch','early_changed')]
    with radar:
        st.caption('Sem meta de market cap ou alta obrigatória. Triagem parcial; não identifica um ponto de compra. Preço medido desde a primeira leitura do teste, não desde o lançamento.')
        search=st.text_input('Buscar moeda ou contrato',key='early_search').strip().casefold()
        group=st.selectbox('Situação',['Todas',*STATUS.values()],key='early_filter')
        chosen=[e for e in entries if (group=='Todas' or STATUS.get(e[2])==group) and (not search or search in (str(e[0]['snapshot'].get('symbol',''))+' '+e[0]['address']).casefold())]
        if not chosen:st.info('Aguardando descobertas nesta seleção. O teste começa a registrar a partir da ativação; não reconstrói o passado.')
        for start in range(0,len(chosen),3):
            for column,(token,r,status) in zip(st.columns(3),chosen[start:start+3]):
                s=token['snapshot'];assessment=r.get('assessment') or {}
                with column,st.container(border=True,key='early_card_'+r['id']):
                    st.markdown('### '+html.escape(str(s.get('symbol','?'))))
                    st.caption(STATUS.get(status,status)+' · experimental')
                    st.write('**Liquidez:** '+usd(s.get('liquidity')))
                    st.write('**'+str(s.get('valuation_type','Avaliação'))+':** '+usd(s.get('valuation')))
                    delta=number(assessment.get('price_since_first_pct'))
                    st.write('**Desde a primeira leitura:** '+('—' if delta is None else f'{delta:+.1f}%'))
                    st.caption('Primeira leitura: '+stamp(r.get('first_at'))+f" · {r.get('observations',0)} observações")
                    if status=='extended':st.warning('Movimento já avançou na janela observada. Alerta inicial retido.')
                    elif status=='blocked':st.error('Uma restrição foi identificada nas verificações disponíveis.')
                    elif status=='reviewed':st.caption('Duas consultas com a triagem inicial atendida. Não significa moeda segura ou atividade orgânica comprovada.')
                    url=chart_url(token)
                    if url:st.link_button('Abrir gráfico',url,use_container_width=True)
                    with st.expander('Evidências e cobertura'):
                        for check in assessment.get('checks',[]):
                            st.text({'met':'✓','unknown':'?','waiting':'○','blocked':'⛔'}.get(check['state'],'?')+' '+check['label'])
                        whales=s.get('whales') or {}
                        if whales.get('status')=='changes':
                            st.caption(f"Amostra de carteiras: {whales.get('increases',0)} aumentando e {whales.get('decreases',0)} reduzindo saldo. Pode ser transferência.")
                        if whales.get('gradual_reductions'):
                            st.caption('Redução gradual observada em grandes detentores da amostra; indicador complementar.')
                        st.caption('Participantes únicos, volume orgânico e vínculos entre carteiras não auditados. Venda não simulada.')
                        st.caption('Última leitura: '+stamp(r.get('last_at')))
                        st.code(token['address'],language=None)
    with comparison:
        st.caption('Últimos 100 registros de até 7 dias, incluindo pendentes, bloqueados e moedas que saíram do radar. Ausência de acompanhamento não é tratada como queda ou sucesso. Variações observadas não simulam execução ou lucro.')
        try:rows=store.read_trials()
        except StorageError:rows=[];st.warning('Histórico do experimento indisponível agora.')
        if not rows:st.info('A comparação começa com a primeira coleta do teste. As observações de 15 min e 1 h aparecerão conforme houver novas consultas.')
        data=[]
        for row in rows:
            r=row['payload']
            lead=(r['classic_at']-r['early_at'])/60 if r.get('classic_at') and r.get('early_at') else None
            data.append({'Moeda':r.get('symbol'),'Primeira leitura':stamp(r.get('first_at')),
                'Estado':STATUS.get(r.get('status'),r.get('status')),'Aviso antecipado':stamp(r.get('early_at')),
                'Sinal clássico':stamp(r.get('classic_at')),'Antecedência observada (min)':lead,
                'Variação 15 min (%)':(r.get('change_15m') or {}).get('pct'),
                'Variação 1 h (%)':(r.get('change_1h') or {}).get('pct'),
                'Menor variação observada (%)':r.get('max_drop_pct'),
                'Cobertura':'Interrompida / fora do radar' if r.get('tracking_stopped_at') else 'Última leitura: '+stamp(r.get('last_at'))})
        if data:st.dataframe(data,hide_index=True,use_container_width=True)
    with alerts:
        with st.expander('Som e notificações do navegador'):
            from pump.browser_alerts import render_browser_alerts
            render_browser_alerts(experimental_alerts,False,'early-v1')
        st.caption('O Telegram segue o modo salvo em sua conta. Avisos experimentais são identificados e começam após a ativação do modo. Não são ordens de compra ou venda.')
        for a in sorted(experimental_alerts,key=lambda a:a['created_at'],reverse=True)[:30]:
            with st.container(border=True):
                st.write(str(a['snapshot'].get('symbol','?'))+' · '+('Triagem inicial atendida' if a['kind']=='early_watch' else 'Triagem alterada'))
                st.caption(stamp(a['created_at']))
                for reason in a.get('reasons',[]):st.text(str(reason))
        if not experimental_alerts:st.info('Nenhum aviso experimental ainda. Dados ausentes não liberam a triagem.')
    with operation:
        operation_details(state.get('run',{}),stamp)
        st.write('O teste mantém os filtros de risco e a liquidez mínima de US$ 25 mil. Não exige market cap mínimo, alta positiva, volume de US$ 5 mil ou idade mínima de 15 minutos para iniciar a observação. O aviso inicial exige duas consultas válidas, separadas por ao menos 45 segundos, normalmente um minuto.')
        st.write('Avisos são retidos se a alta superar 50% desde a primeira leitura do teste ou 40% em 5 minutos. São limites experimentais, sem validação de rentabilidade. Uma moeda pode já estar esticada antes de ser descoberta.')
        st.write('A descoberta continua limitada às fontes públicas. Até 10 posições adicionais recebem descobertas novas, além das 30 acompanhadas pelo clássico. Falta de dados, limites de API e saída do radar deixam lacunas na comparação.')
        if st.button('Voltar ao Clássico',key='early_rollback'):
            if save_mode('classic'):st.rerun()
