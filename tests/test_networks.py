import time
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest
from pump.networks import NETWORKS, network_tokens
from pump.radar_cards import chart_url, confirmed_find
from pump.storage import PublicMarketStore, StorageError
from tests.test_dashboard import ROOT
from tests.test_criteria import RULES, token


def network_state(chain='robinhood'):
    now=time.time()
    t=token()
    t.update(address='0x'+'a'*40,status='watch',first_seen=now-3600,last_checked=now)
    t['snapshot'].update(chain_id=chain,address=t['address'],profile='dex-market-observation-v1',
        symbol='ROBINTEST',pair_address='0x'+'b'*64,observed_at=now,pool_created_at=now-3600,
        risk={'status':'unsupported'},mint_disabled=None,freeze_disabled=None,extensions_review=True)
    return {'chain_id':chain,'tokens':{t['address']:t},'alerts':[],
            'run':{'completed_at':now,'checked':1,'status':'ok','rules':RULES}}


def test_chain_links_namespace_isolation_and_no_false_gold():
    state=network_state()
    t=next(iter(state['tokens'].values()))
    assert len(network_tokens(state,'robinhood'))==1 and not network_tokens(state,'base')
    assert chart_url(t)=='https://dexscreener.com/robinhood/'+'0x'+'b'*64
    t['status']='candidate'
    assert not confirmed_find(t,{'score':100,'issue':None,'stale':False})
    t['snapshot']['chain_id']='../../evil'
    assert chart_url(t) is None


def test_network_reader_projects_only_selected_chain_and_rejects_path_injection():
    store=PublicMarketStore('https://example.supabase.co','public', 'user-token')
    with patch.object(store,'request',return_value=[{'payload':network_state()}]) as request:
        assert store.read_network('robinhood')['chain_id']=='robinhood'
        assert request.call_args.args[0].endswith('payload->networks->robinhood')
        with pytest.raises(StorageError):store.read_network('../../evil')


def test_selector_robinhood_market_cards_and_legacy_menu_migration(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY','sb_publishable_example')
    profile={'id':'test-id','username':'teste','display_name':'Teste','role':'user','active':True}
    solana={'tokens':{},'alerts':[],'run':{}}
    with patch('supabase.create_client'),patch('pump.account.ensure_session',return_value=True),patch('pump.storage.PublicMarketStore.read',return_value=solana),patch('pump.storage.PublicMarketStore.read_history',return_value=[]),patch('pump.storage.PublicMarketStore.read_network',side_effect=lambda chain:network_state(chain)) as read:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        app.session_state['sniper_profile']=profile
        app.session_state['sniper_session']={'access_token':'user-token'}
        app.session_state['modulo_ativo']='Dex Trade'
        app.run()
        assert not app.exception
        assert app.session_state['modulo_ativo']=='Dex Sniper'
        assert any(b.label=='Dex Sniper' for b in app.sidebar.button)
        assert 'Robinhood Chain' in app.selectbox(key='dex_network').options
        app.selectbox(key='dex_network').set_value('robinhood').run()
        assert not app.exception
        assert read.call_args.args[0]=='robinhood'
        markup='\n'.join(m.value for m in app.markdown)
        assert 'ROBINTEST' in markup and 'Robinhood Chain' in markup and 'ACHADO NO GARIMPO' not in markup
        assert any('Não gera confirmação dourada' in i.value for i in app.info)
        assert any('Mercado: 7 de 7' in c.value for c in app.caption)
        assert all('Sinais confirmados' not in t.label for t in app.tabs)
        app.selectbox(key='dex_network').set_value('base').run()
        assert not app.exception and read.call_args.args[0]=='base'
        app.selectbox(key='dex_network').set_value('solana').run()
        assert not app.exception and any(t.label=='🔔 Alertas' for t in app.tabs)
