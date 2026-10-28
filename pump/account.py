"""Per-session authentication. No shared cached Auth client or browser tokens."""
import time
import requests
import streamlit as st
from pump.config import settings


class AccountError(RuntimeError):
    pass


ERRORS = {
    'unauthorized': 'Sua sessão expirou. Entre novamente.',
    'access_denied': 'Esta conta está desativada ou não tem acesso.',
    'admin_required': 'Somente o administrador pode fazer isso.',
    'invalid_user': 'Use um usuário de 3 a 32 letras minúsculas, números ou _ e senha com pelo menos 12 caracteres.',
    'weak_password': 'A senha deve ter entre 12 e 128 caracteres.',
    'invalid_bot_token': 'Confira a chave enviada pelo BotFather.',
    'telegram_unavailable': 'Não foi possível acessar o bot. Confira a chave e tente novamente.',
    'bot_has_webhook': 'Esse bot já está integrado a outro serviço. Crie um bot dedicado ao Crypto Sniper.',
    'bot_in_use': 'Outro serviço está lendo as mensagens desse bot. Use um bot dedicado.',
    'start_not_received': 'Ainda não chegou a confirmação. Abra o link e toque em Iniciar no Telegram.',
    'connection_expired': 'O link de conexão expirou. Informe a chave novamente para gerar outro.',
    'wait_before_retry': 'Aguarde um pouco antes de repetir o teste ou a conexão.',
    'own_account_protected': 'Sua própria conta não pode ser desativada aqui.',
    'operation_failed': 'Não foi possível concluir. Confira os dados; o nome de usuário ou o bot pode já estar em uso.',
}


def config():
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    return settings(secrets)


def auth_request(path, data=None, token=None, method='POST'):
    cfg = config()
    try:
        r = requests.request(method, cfg['SUPABASE_URL'].rstrip('/')+'/auth/v1/'+path,
            headers={'apikey': cfg['SUPABASE_KEY'], **({'Authorization': 'Bearer '+token} if token else {})},
            json=data, timeout=15)
        if not r.ok:
            raise AccountError('Usuário ou senha inválidos, ou acesso temporariamente indisponível.')
        return r.json() if r.content else {}
    except (requests.RequestException, ValueError):
        raise AccountError('Não foi possível acessar o login. Tente novamente em instantes.') from None


def action(name, **payload):
    cfg = config()
    session = st.session_state.get('sniper_session', {})
    try:
        r = requests.post(cfg['SUPABASE_URL'].rstrip('/')+'/functions/v1/sniper-account',
            headers={'Authorization': 'Bearer '+session.get('access_token', '')},
            json={'action': name, **payload}, timeout=25)
        result = r.json()
        if not r.ok:
            raise AccountError(ERRORS.get(result.get('error'), 'Não foi possível concluir a operação. Tente novamente.'))
        return result
    except (requests.RequestException, ValueError):
        raise AccountError('Serviço temporariamente indisponível. Tente novamente.') from None


def sign_in(username, password):
    username = username.strip().lower()
    if not username or any(x not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for x in username):
        raise AccountError('Informe seu nome de usuário, por exemplo: admin.')
    session = auth_request('token?grant_type=password', {'email': username+'@crypto-sniper.invalid', 'password': password})
    session['expires_at'] = time.time()+session.get('expires_in', 3600)
    st.session_state.sniper_session = session
    try:
        st.session_state.sniper_profile = action('session')['profile']
        st.session_state.sniper_verified_at = time.time()
    except AccountError:
        st.session_state.pop('sniper_session', None)
        raise


def ensure_session():
    session = st.session_state.get('sniper_session')
    if not session:
        return False
    try:
        if session.get('expires_at', 0)-time.time() < 120:
            session = auth_request('token?grant_type=refresh_token', {'refresh_token': session['refresh_token']})
            session['expires_at'] = time.time()+session.get('expires_in', 3600)
            st.session_state.sniper_session = session
        if time.time()-st.session_state.get('sniper_verified_at', 0) > 30:
            st.session_state.sniper_profile = action('session')['profile']
            st.session_state.sniper_verified_at = time.time()
        return True
    except (AccountError, KeyError):
        st.session_state.pop('sniper_session', None)
        st.session_state.pop('sniper_profile', None)
        return False


def logout():
    session = st.session_state.get('sniper_session', {})
    try:
        auth_request('logout?scope=local', token=session.get('access_token'))
    except AccountError:
        pass
    for key in list(st.session_state):
        del st.session_state[key]
    st.rerun()


def require_login():
    if ensure_session():
        return st.session_state.sniper_profile
    cfg = config()
    left, center, right = st.columns([1, 1.4, 1])
    with center:
        st.markdown('## Crypto Sniper')
        st.write('Entre para acompanhar o radar e configurar seus avisos.')
        if not cfg.get('SUPABASE_URL') or not cfg.get('SUPABASE_KEY'):
            st.info('Configure SUPABASE_URL e SUPABASE_KEY para habilitar o login.')
            st.stop()
        with st.form('sniper_login', clear_on_submit=True):
            username = st.text_input('Usuário', autocomplete='username')
            password = st.text_input('Senha', type='password', autocomplete='current-password')
            submit = st.form_submit_button('Entrar', type='primary', use_container_width=True)
        if submit:
            try:
                sign_in(username, password)
                st.rerun()
            except AccountError as exc:
                st.error(str(exc))
        st.caption('Acesso por convite. Se perdeu a senha, solicite uma redefinição ao administrador.')
    st.stop()


def password_form():
    with st.expander('Alterar minha senha'):
        with st.form('own_password', clear_on_submit=True):
            password = st.text_input('Nova senha (mínimo de 12 caracteres)', type='password')
            confirm = st.text_input('Repita a nova senha', type='password')
            submit = st.form_submit_button('Salvar nova senha')
        if submit:
            if password != confirm:
                st.error('As senhas não coincidem.')
            else:
                try:
                    action('change_password', password=password)
                    st.success('Senha atualizada.')
                except AccountError as exc:
                    st.error(str(exc))


def users_dashboard():
    st.title('Usuários')
    st.caption('Administração de acessos. Contas comuns usam o radar e configuram suas próprias notificações.')
    if st.session_state.get('sniper_profile', {}).get('role') != 'admin':
        st.error('Acesso exclusivo do administrador.')
        return
    try:
        users = action('admin_list')['users']
    except AccountError as exc:
        st.error(str(exc))
        return
    a,b,c = st.columns(3)
    a.metric('Contas', len(users))
    b.metric('Ativas', sum(u['active'] for u in users))
    c.metric('Administradores', sum(u['role']=='admin' for u in users))
    st.dataframe([{'Usuário':u['username'],'Nome':u['display_name'],'Perfil':u['role'],'Ativo':u['active']} for u in users], hide_index=True, use_container_width=True)
    with st.expander('Criar usuário'):
        with st.form('create_user', clear_on_submit=True):
            username = st.text_input('Nome de usuário (sem espaços)')
            name = st.text_input('Nome de exibição')
            password = st.text_input('Senha inicial (mínimo de 12 caracteres)', type='password')
            submit = st.form_submit_button('Criar conta')
        if submit:
            try:
                action('admin_create', username=username.strip().lower(), display_name=name.strip(), password=password)
                st.success('Conta criada. Entregue o usuário e a senha diretamente à pessoa.')
                st.rerun()
            except AccountError as exc:
                st.error(str(exc))
    others = [u for u in users if u['role']!='admin']
    for u in others:
        with st.expander(f"{u['username']} · {'Ativo' if u['active'] else 'Desativado'}"):
            if st.button('Desativar acesso' if u['active'] else 'Reativar acesso', key='toggle_'+u['id']):
                try:
                    action('admin_toggle', user_id=u['id'])
                    st.rerun()
                except AccountError as exc:
                    st.error(str(exc))
            with st.form('reset_'+u['id'], clear_on_submit=True):
                new = st.text_input('Nova senha (mínimo de 12 caracteres)', type='password')
                submit = st.form_submit_button('Redefinir senha')
            if submit:
                try:
                    action('admin_reset', user_id=u['id'], password=new)
                    st.success('Senha redefinida.')
                except AccountError as exc:
                    st.error(str(exc))
