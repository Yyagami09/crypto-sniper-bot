from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_login_blocks_navigation_without_configuration(monkeypatch):
    for name in ('SUPABASE_URL', 'SUPABASE_KEY'):
        monkeypatch.delenv(name, raising=False)
    app = AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    assert not app.sidebar.button
    assert any('Configure SUPABASE_URL' in i.value for i in app.info)


def test_regular_user_cannot_open_admin_and_can_render_demo(tmp_path, monkeypatch):
    monkeypatch.setenv('PUMP_LOCAL_DB', str(tmp_path/'ui.sqlite3'))
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'sb_publishable_example')
    profile = {'id':'test','username':'teste','display_name':'Teste','role':'user','active':True}
    with patch('supabase.create_client'), patch('pump.account.ensure_session', return_value=True), patch('pump.storage.PublicMarketStore.read', return_value={'tokens':{},'alerts':[], 'run':{}}):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20)
        app.session_state['sniper_profile'] = profile
        app.session_state['sniper_session'] = {'access_token':'user-token'}
        app.run()
        assert not app.exception
        keys = [b.key for b in app.sidebar.button]
        assert 'nav_users' not in keys and 'nav_game' not in keys
        app.toggle(key='pump_demo').set_value(True).run()
        app.button(key='pump_seed').click().run()
        assert not app.exception
        assert any(m.label=='Em acompanhamento' and m.value=='4' for m in app.metric)
        app.session_state['modulo_ativo'] = 'Usuários'
        app.run()
        assert not app.exception
        assert any('exclusivo' in e.value for e in app.error)


def test_admin_users_and_personal_telegram_pages_render(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'sb_publishable_example')
    profile = {'id':'admin-id','username':'admin','display_name':'Administrador','role':'admin','active':True}
    user = {'id':'test-id','username':'teste','display_name':'Teste','role':'user','active':True}
    def action(name, **kwargs):
        return {'users':[profile,user]} if name=='admin_list' else {'connection':None,'last_delivery':None}
    with patch('supabase.create_client'), patch('pump.account.ensure_session', return_value=True), patch('pump.account.action', side_effect=action):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20)
        app.session_state['sniper_profile'] = profile
        app.session_state['sniper_session'] = {'access_token':'admin-token'}
        app.session_state['modulo_ativo'] = 'Usuários'
        app.run()
        assert not app.exception
        assert any(m.label=='Contas' and m.value=='2' for m in app.metric)
        app.sidebar.button(key='nav_notifications').click().run()
        assert not app.exception
        assert any('Telegram pessoal' in h.value for h in app.subheader)
        assert any('Cole a chave' in t.label for t in app.text_input)


def test_live_cards_score_groups_search_and_table(monkeypatch):
    import time
    from tests.test_criteria import token, RULES
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'sb_publishable_example')
    now = time.time()
    tokens = {}
    for i,status in enumerate(['candidate','confirming','watch','incomplete','blocked']):
        t = token()
        t.update(address=str(i+2)*32,status=status,first_seen=now-3600,last_checked=now)
        t['snapshot'].update(symbol='CARD-'+str(i),name='Card de teste',observed_at=now,pool_created_at=now-3600)
        if status=='watch':
            t['snapshot']['volume_5m']=1000
        tokens[t['address']]=t
    state = {'tokens':tokens,'alerts':[],'run':{'rules':RULES,'completed_at':now,'status':'ok'}}
    profile = {'id':'test-id','username':'teste','display_name':'Teste','role':'user','active':True}
    with patch('supabase.create_client'), patch('pump.account.ensure_session', return_value=True), patch('pump.storage.PublicMarketStore.read', return_value=state):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20)
        app.session_state['sniper_profile']=profile
        app.session_state['sniper_session']={'access_token':'user-token'}
        app.run()
        assert not app.exception
        cards = '\n'.join(m.value for m in app.markdown)
        assert '6 de 7 critérios atendidos' in cards and '86<small>' in cards
        assert 'Bloqueada pelas verificações' in cards and 'Pontuação pendente' in cards
        assert any(h.value=='Em observação · 1' for h in app.subheader)
        app.selectbox(key='dex_group_filter').select('Em observação').run()
        assert not app.exception
        assert not any(h.value.startswith('Sinais confirmados') for h in app.subheader)
        app.radio(key='dex_view').set_value('Tabela').run()
        assert not app.exception
        assert len(app.dataframe[0].value)==1
        assert app.dataframe[0].value.iloc[0]['Aderência (/100)']==86
        app.text_input(key='dex_search').set_value('SEM_RESULTADO').run()
        assert not app.exception
        assert any('Nenhuma moeda' in msg.value for msg in app.info)
