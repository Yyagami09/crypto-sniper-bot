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
