import streamlit as st
from pump.criteria import adherence, number
from pump.radar_cards import CSS, CARD_STATUS, card_markup, chart_url, details, stamp
from pump.storage import StorageError


def recent_confirmations(rows, now):
    """An immutable event is retained by confirmation time, never by last scan."""
    unique = {}
    for row in rows:
        a = row.get('payload') or {}
        created = number(a.get('created_at'))
        if (a.get('kind')=='candidate' and created is not None and 0<=now-created<86400
                and a.get('id') and a.get('address') and a.get('snapshot')):
            unique.setdefault(a['id'],row)
    return sorted(unique.values(),key=lambda r:r['payload']['created_at'],reverse=True)


def current_situation(token, now):
    if not token:
        return 'Fora do radar atual · sem nova consulta disponível'
    checked = number(token.get('last_checked')) or 0
    if now-checked>1200:
        return 'Sem consulta recente · última situação: '+CARD_STATUS.get(token.get('status'),'Indisponível')
    return CARD_STATUS.get(token.get('status'),'Indisponível')+' · '+stamp(checked)


def render_history(store, state, now, demo=False):
    st.markdown(CSS, unsafe_allow_html=True)
    st.subheader('⛏️ Achados nas últimas 24 horas')
    st.caption('Cada confirmação fica guardada por 24 horas a partir do sinal, mesmo se a moeda perder os critérios ou sair do radar. Novas varreduras não apagam nem renovam esse prazo. Horários de Brasília.')
    page = st.session_state.get('dex_history_page',0)
    size = 30
    try:
        if demo:
            rows = [{'payload':a,'rules':state.get('run',{}).get('rules',{})} for a in state.get('alerts',[])]
            rows = recent_confirmations(rows,now)[page*size:page*size+size+1]
        else:
            rows = store.read_history(now,page,size)
    except StorageError:
        st.warning('Não foi possível carregar o histórico agora. Os achados já gravados continuam no servidor; tente novamente.')
        return
    has_more = len(rows)>size
    rows = recent_confirmations(rows[:size],now)
    if not rows:
        st.info('Nenhum achado nesta página das últimas 24 horas.' if page else 'Nenhuma confirmação registrada nas últimas 24 horas. Os próximos sinais aparecerão aqui automaticamente.')
    for start in range(0,len(rows),3):
        columns = st.columns(3)
        for column,row in zip(columns,rows[start:start+3]):
            a = row['payload']
            # This represents the recorded event, not a new live classification.
            t = {'address':a['address'],'status':'candidate','snapshot':a['snapshot'],
                 'reasons':a.get('reasons',[]),'first_seen':a['created_at']}
            model = adherence(t,row.get('rules') or {},a['created_at'])
            with column, st.container(border=True,key='dex_card_gold_history_'+a['id']):
                st.markdown(card_markup(t,model,historical=True),unsafe_allow_html=True)
                st.caption('Confirmado: '+stamp(a['created_at']))
                remaining = max(0,86400-(now-a['created_at']))
                st.caption(f'No histórico por mais {int(remaining//3600)}h {int(remaining%3600//60):02d}min')
                current = state.get('tokens',{}).get(a['address'])
                st.info('Situação atual: '+current_situation(current,now))
                if current and current.get('status')!='candidate':
                    for reason in current.get('reasons',[])[:2]:
                        st.text('• '+str(reason))
                url = chart_url(t)
                if url and not demo:
                    st.link_button('Abrir gráfico',url,key='history_chart_'+a['id'],use_container_width=True)
                details(t,model)
    left,middle,right = st.columns([1,2,1])
    if left.button('← Mais recentes',key='history_previous',disabled=page==0):
        st.session_state.dex_history_page=page-1
        st.rerun(scope='fragment')
    middle.caption(f'Página {page+1} · até 30 registros por página')
    if right.button('Mais antigos →',key='history_next',disabled=not has_more):
        st.session_state.dex_history_page=page+1
        st.rerun(scope='fragment')
