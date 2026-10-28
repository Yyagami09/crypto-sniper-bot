"""Network labels and the observation-only view for chains without risk adapters."""
import time
import streamlit as st
from pump.criteria import adherence
from pump.storage import StorageError

NETWORKS = {'solana':'Solana', 'robinhood':'Robinhood Chain', 'ethereum':'Ethereum',
            'base':'Base', 'bsc':'BNB Chain', 'arbitrum':'Arbitrum', 'polygon':'Polygon',
            'avalanche':'Avalanche', 'optimism':'Optimism'}


def network_tokens(state, chain):
    return [t for t in state.get('tokens',{}).values()
            if t.get('snapshot',{}).get('chain_id')==chain]


def render_observation(store, chain):
    from pump.radar_cards import CSS, card_markup, chart_url, stamp
    now = time.time()
    st.subheader(NETWORKS[chain]+' · Observação de mercado')
    st.info('Esta rede acompanha preço, volume, liquidez e os sete critérios de mercado. LP, permissões do contrato, carteiras e slow rug ainda não são verificados nesta rede. Não gera confirmação dourada nem alertas automáticos.')
    st.caption('A coleta das redes adicionais ocorre no servidor após a publicação e o envio dos alertas da Solana, inclusive com a aba fechada. A seleção muda sua visualização; não desliga as demais redes nem altera os alertas do Telegram da Solana.')
    try:
        state = store.read_network(chain)
    except StorageError:
        st.warning('Não foi possível carregar esta rede agora. Tente novamente no próximo ciclo.')
        return
    if not state:
        st.info('Primeira coleta desta rede ainda não publicada. Aguarde o próximo ciclo.')
        return
    run = state.get('run',{})
    for issue in run.get('source_errors',[]):
        st.warning(str(issue))
    tokens = network_tokens(state,chain)
    a,b,c = st.columns(3)
    a.metric('Moedas nesta rede',len(tokens))
    b.metric('Consultadas no ciclo',run.get('checked',0))
    c.metric('Frequência prevista','1 min')
    st.caption('Última coleta: '+stamp(run.get('completed_at'))+' · Horários de Brasília. Fontes gratuitas podem atrasar ou limitar respostas.')
    if not run.get('completed_at') or now-run['completed_at']>180:
        st.warning('Esta rede está sem coleta recente. Os valores abaixo podem estar desatualizados.')
    if not tokens:
        st.info('Nenhuma moeda disponível na amostra desta rede. Isso não significa que a rede não tenha negociações.')
        st.link_button('Ver rede no DEX Screener','https://dexscreener.com/'+chain)
        return
    left,right = st.columns([2,1])
    query = left.text_input('Buscar moeda ou contrato',key='network_search_'+chain).strip().casefold()
    order = right.selectbox('Ordenar por',['Critérios de mercado','Liquidez','Volume 5 min','Consulta recente'],key='network_sort_'+chain)
    entries=[]
    for token in tokens:
        snapshot=token['snapshot']
        if query and query not in ' '.join(str(snapshot.get(k,'')) for k in ('symbol','name','address')).casefold():
            continue
        model=adherence(token,run.get('rules',{}),now)
        model['score']=None
        model['issue']='Consulta antiga' if model['stale'] else 'Sem triagem de risco nesta rede'
        entries.append((token,model))
    field={'Liquidez':'liquidity','Volume 5 min':'volume_5m','Consulta recente':'observed_at'}.get(order)
    entries.sort(key=lambda e:e[0]['snapshot'].get(field) or 0 if field else e[1]['passed'],reverse=True)
    st.caption('Critérios de mercado são contagens de condições atendidas, sem nota de segurança. Os limites iniciais são os mesmos da Solana e ainda não foram calibrados para esta rede.')
    st.markdown(CSS,unsafe_allow_html=True)
    for start in range(0,len(entries),3):
        for column,(token,model) in zip(st.columns(3),entries[start:start+3]):
            with column,st.container(border=True,key='dex_card_network_'+chain+'_'+token['address']):
                st.markdown(card_markup(token,model),unsafe_allow_html=True)
                valid = all(c['passed'] is not None for c in model['checks']) and not model['stale'] and token.get('status')=='watch'
                st.caption(f"Mercado: {model['passed']} de 7 critérios atendidos" if valid else 'Critérios aguardando dados completos e atuais')
                url=chart_url(token)
                if url:
                    st.link_button('Abrir gráfico',url,use_container_width=True)
                with st.expander('Dados e critérios'):
                    st.dataframe(model['checks'],hide_index=True,use_container_width=True)
                    for reason in token.get('reasons',[]):
                        st.text('• '+str(reason))
                    st.code(token['address'],language=None)
                    st.json(token['snapshot'],expanded=False)
    if not entries:
        st.info('Nenhuma moeda corresponde à busca nesta rede.')
