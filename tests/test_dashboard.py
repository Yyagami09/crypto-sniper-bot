from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_pump_opens_without_secrets_and_demo_renders(tmp_path, monkeypatch):
    monkeypatch.setenv('PUMP_LOCAL_DB', str(tmp_path / 'ui.sqlite3'))
    for name in ('SUPABASE_URL','SUPABASE_KEY','PUMP_SUPABASE_KEY'):
        monkeypatch.delenv(name, raising=False)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
    app.run()
    assert not app.exception
    app.toggle(key='pump_demo').set_value(True).run()
    assert not app.exception
    app.button(key='pump_seed').click().run()
    assert not app.exception
    assert any(m.label == 'Em acompanhamento' and m.value == '4' for m in app.metric)
    assert any('DEMONSTRAÇÃO' in w.value for w in app.warning)
    assert any('CANDIDATA' in m.value for m in app.markdown)
    app.sidebar.button(key='nav_game').click().run()
    assert not app.exception
    assert any('Game Sniper' in m.value for m in app.info)
