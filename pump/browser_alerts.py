from pathlib import Path
import streamlit as st

_component = st.components.v2.component(
    'sniper_browser_alerts',
    html='''<div class="controls"><button data-sound type="button">🔊 Ativar e testar som</button><button data-desktop type="button">Ativar notificações do navegador</button></div><p data-status role="status" aria-live="polite"></p>''',
    css='''button{background:#162128;color:#eaecef;border:1px solid #35454c;border-radius:8px;padding:10px 14px;cursor:pointer;font:inherit}.controls{display:flex;gap:10px;flex-wrap:wrap}p{color:#9eacba;font-size:13px;line-height:1.5}button:hover{border-color:#00dcb0}button:focus-visible{outline:2px solid #00dcb0}''',
    js=Path(__file__).with_suffix('.js').read_text(),
)


def render_browser_alerts(alerts, demo=False, mode='classic'):
    uid = st.session_state.get('sniper_profile', {}).get('id', 'demo')
    _component(key='sniper_browser_notifications', data={
        'scope': f'{uid}:{"demo" if demo else "live"}:{mode}',
        'alerts': [{'id': a['id'], 'kind': a['kind'], 'created_at': a['created_at'],
                    'symbol': str(a.get('snapshot', {}).get('symbol', '?'))[:30]} for a in alerts],
    })
