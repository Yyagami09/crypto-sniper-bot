"""Early discovery experiment; classic screening stays independently available."""
import html
import time
import streamlit as st
from pump.storage import StorageError
from pump.radar_cards import chart_url, usd, stamp
from pump.criteria import number

MODES={'early-v1':'Antecipado · experimental','classic':'Clássico'}
STATUS={'pending':'Faltam dados','blocked':'Restrição identificada','observing':'Em observação',
        'reviewed':'Vale abrir o gráfico','extended':'Movimento avançado'}
COLORS={'reviewed':'#49dbaa','observing':'#67adf3','pending':'#94a3b4','extended':'#e8b95e','blocked':'#ed8497'}
EARLY_CSS='''<style>
[class*="st-key-early_card_"]{border:1px solid #34414d!important;border-radius:14px!important;padding:18px!important;background:#141b23}
[class*="st-key-early_card_reviewed_"]{border-color:#36b387!important;background:linear-gradient(140deg,#173b3055,#121f20)!important;box-shadow:0 5px 24px #27b38315}
[class*="st-key-early_card_observing_"]{border-color:#416a92!important;background:linear-gradient(140deg,#1b334d55,#141c25)!important}
[class*="st-key-early_card_pending_"]{border-color:#3b4652!important}
[class*="st-key-early_card_extended_"]{border-color:#8b6b38!important;background:linear-gradient(140deg,#54402044,#201c16)!important}
[class*="st-key-early_card_blocked_"]{border-color:#854650!important;background:linear-gradient(140deg,#51252e44,#21181c)!important}
.early-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#a7b3c0;margin:8px 0 18px}.early-legend span{display:flex;align-items:center;gap:6px}.early-legend i{width:7px;height:7px;border-radius:100%;display:inline-block}.early-badge{font-size:11px;font-weight:750;letter-spacing:.3px;line-height:1.5;margin-bottom:8px}.early-why{font-size:12px;line-height:1.7;color:#b5d1c6;margin:6px 0 14px}
</style>'''



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
        if now-record.get('last_at',0)>120 or now<record.get('last_at',0) or record.get('tracking_stopped_at'):status='pending'
        entries.append((t,record,status))
    return sorted(entries,key=lambda e:({'reviewed':0,'observing':1,'pending':2,'extended':3,'blocked':4}.get(e[2],5),-e[1].get('first_at',0)))


def render_experiment(store,state,now):
    from pump.dashboard_ui import status_line,operation_details
    status_line(state.get('run',{}),now,stamp,mode='Antecipado · experimental · Solana')
    entries=experiment_tokens(state,now)
    for i,(column,(label,value)) in enumerate(zip(st.columns(4),[
        ('Em acompanhamento',len(entries)),('Vale abrir o gráfico',sum(s=='reviewed' for _,_,s in entries)),
        ('Dados pendentes',sum(s=='pending' for _,_,s in entries)),('Restrições identificadas',sum(s=='blocked' for _,_,s in entries))])):
        with column,st.container(border=True,key='dex_summary_early_'+str(i)):st.metric(label,value)
    radar,comparison,alerts,operation=st.tabs(['📡 Descobertas','🧪 Comparação','🔔 Alertas','⚙️ Operação'])
    experimental_alerts=[a for a in state.get('alerts',[]) if a['kind'] in ('early_watch','early_changed')]
    with radar:
        st.markdown(EARLY_CSS,unsafe_allow_html=True)
        legend=''.join(f'<span><i style="background:{COLORS[k]}"></i>{html.escape(STATUS[k])}</span>' for k in ('reviewed','observing','pending','extended','blocked'))
        st.markdown('<div class="early-legend">'+legend+'</div>',unsafe_allow_html=True)
        left,right=st.columns([2,1])
        search=left.text_input('Buscar moeda ou contrato',key='early_search').strip().casefold()
        group=right.selectbox('Situação',['Todas',*STATUS.values()],key='early_filter')
        chosen=[e for e in entries if (group=='Todas' or STATUS.get(e[2])==group) and (not search or search in (str(e[0]['snapshot'].get('symbol',''))+' '+e[0]['address']).casefold())]
        def grid(items):
            for start in range(0,len(items),3):
                for column,(token,r,status) in zip(st.columns(3),items[start:start+3]):
                    s=token['snapshot'];assessment=r.get('assessment') or {}
                    with column,st.container(border=True,key='early_card_'+status+'_'+r['id']):
                        badge='POSSÍVEL OPORTUNIDADE · REVISAR GRÁFICO' if status=='reviewed' else STATUS.get(status,status).upper()
                        st.markdown(f'<div class="early-badge" style="color:{COLORS.get(status,"#94a3b4")}">{html.escape(badge)}</div>',unsafe_allow_html=True)
                        st.markdown('### '+html.escape(str(s.get('symbol','?'))))
                        if status=='reviewed':
                            st.markdown('<div class="early-why">Verificações disponíveis atendidas em duas consultas.<br>Liquidez presente e sem os alertas que retêm a seleção inicial.</div>',unsafe_allow_html=True)
                        st.write('**Liquidez:** '+usd(s.get('liquidity')))
                        st.write('**'+str(s.get('valuation_type','Avaliação'))+':** '+usd(s.get('valuation')))
                        delta=number(assessment.get('price_since_first_pct'))
                        st.write('**Desde que apareceu no teste:** '+('—' if delta is None else f'{delta:+.1f}%'))
                        if status=='extended':st.caption('Já avançou na janela observada. Aviso de oportunidade retido.')
                        elif status=='blocked':st.caption('Fora dos destaques por uma restrição identificada. Confira os detalhes.')
                        elif status=='pending':st.caption('Sem dados suficientes para destacar. Aguarde outra consulta.')
                        elif status=='observing':st.caption('Ainda não passou pelas duas consultas necessárias para o destaque.')
                        url=chart_url(token)
                        if url:st.link_button('👀 Analisar gráfico' if status=='reviewed' else 'Abrir gráfico',url,type='primary' if status=='reviewed' else 'secondary',use_container_width=True)
                        st.caption('Revisão manual · não é indicação de compra' if status=='reviewed' else 'Experimental · sem indicação de compra')
                        with st.expander('Por que recebeu esta cor?'):
                            st.caption('Primeira leitura: '+stamp(r.get('first_at'))+f" · {r.get('observations',0)} observações")
                            for check in assessment.get('checks',[]):
                                st.text({'met':'✓','unknown':'?','waiting':'○','blocked':'⛔'}.get(check['state'],'?')+' '+check['label'])
                            whales=s.get('whales') or {}
                            if whales.get('status')=='changes':
                                st.caption(f"Amostra de carteiras: {whales.get('increases',0)} aumentando e {whales.get('decreases',0)} reduzindo saldo. Pode ser transferência.")
                            if whales.get('gradual_reductions'):
                                st.caption('Redução gradual observada em grandes detentores da amostra; indicador complementar.')
                            st.caption('Participantes únicos, volume orgânico e vínculos entre carteiras não auditados. Venda não simulada. O gráfico pode ter subido antes da descoberta.')
                            st.caption('Última leitura: '+stamp(r.get('last_at')))
                            st.code(token['address'],language=None)
        focus=[e for e in chosen if e[2]=='reviewed']
        if group in ('Todas',STATUS['reviewed']):
            st.subheader('👀 Vale abrir o gráfico'+(f' · {len(focus)}' if focus else ''))
            st.caption('Possíveis oportunidades para análise manual, selecionadas pelas verificações disponíveis. Verde não significa moeda segura ou entrada confirmada.')
            if focus:grid(focus)
            else:st.info('Nenhuma moeda está pronta para destaque agora. Os próximos avisos aparecerão aqui automaticamente, sem promover moedas com dados pendentes.')
        for status in ('observing','pending','extended','blocked'):
            items=[e for e in chosen if e[2]==status]
            if items:
                with st.expander(STATUS[status]+f' · {len(items)}',expanded=group!='Todas'):
                    grid(items)
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
                st.write(str(a['snapshot'].get('symbol','?'))+' · '+('👀 Vale abrir o gráfico' if a['kind']=='early_watch' else 'Triagem alterada'))
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
