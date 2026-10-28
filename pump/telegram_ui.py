import streamlit as st
from pump.account import AccountError, action, password_form


def render_telegram_connection():
    st.subheader('Telegram pessoal')
    st.write('Receba os próximos alertas mesmo com o painel fechado. Cada usuário conecta seu próprio bot gratuito.')
    st.caption('Não precisamos do seu número, senha ou código de login do Telegram. A chave do bot fica protegida no servidor.')
    try:
        result = action('telegram_status')
    except AccountError as exc:
        st.info(str(exc))
        return
    connection = result.get('connection')
    if connection and connection['connected']:
        st.success(f"Conectado ao bot @{connection['bot_username']}")
        st.caption('Os avisos seguem a coleta de 1 minuto. Deixe as notificações do Telegram habilitadas no celular ou Windows. Bloquear ou silenciar o bot impede os avisos.')
        a,b = st.columns(2)
        if a.button('Enviar teste ao meu Telegram', key='telegram_test'):
            try:
                action('telegram_test')
                st.success('Mensagem de teste enviada. Confira seu Telegram.')
            except AccountError as exc:
                st.error(str(exc))
        if b.button('Desconectar meu Telegram', key='telegram_disconnect'):
            try:
                action('telegram_disconnect')
                st.rerun()
            except AccountError as exc:
                st.error(str(exc))
        delivery = result.get('last_delivery')
        if delivery:
            label = {'sent':'Enviado','pending':'Nova tentativa pendente','failed':'Falhou após as tentativas'}
            st.caption('Último envio automático: '+label.get(delivery['status'],delivery['status']))
    else:
        st.markdown('**1. Crie seu bot uma única vez**')
        st.link_button('Abrir BotFather oficial', 'https://t.me/BotFather')
        st.write('Envie /newbot, escolha um nome e um usuário terminado em bot. Copie a chave que o BotFather entregar. Use um bot novo, dedicado a este painel.')
        with st.form('telegram_prepare', clear_on_submit=True):
            token = st.text_input('2. Cole a chave do bot', type='password', help='É a chave do bot enviada pelo BotFather. Não é código de login da sua conta.')
            submit = st.form_submit_button('Preparar conexão')
        if submit:
            try:
                connection = action('telegram_prepare', token=token.strip())['connection']
            except AccountError as exc:
                st.error(str(exc))
        if connection and connection.get('link'):
            st.markdown('**3. Abra o bot e toque em Iniciar**')
            st.link_button('Abrir meu bot no Telegram', connection['link'])
            st.caption('O link vale por 15 minutos. Depois de tocar em Iniciar, volte e confirme abaixo.')
            if st.button('Já toquei em Iniciar — confirmar conexão', key='telegram_confirm'):
                try:
                    action('telegram_confirm')
                    st.rerun()
                except AccountError as exc:
                    st.error(str(exc))
            if st.button('Cancelar conexão pendente', key='telegram_cancel'):
                try:
                    action('telegram_disconnect')
                    st.rerun()
                except AccountError as exc:
                    st.error(str(exc))
    password_form()
