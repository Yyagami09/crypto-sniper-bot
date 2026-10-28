import time
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from pump.account import AccountError
from tests.test_dashboard import ROOT


def report(chain='solana',objective='reentry'):
    now=time.time()
    return {'chain':chain,'objective':objective,'queried_at':now,'snapshot':{
        'address':'2'*32,'symbol':'MANUAL','pair_url':'https://dexscreener.com/solana/'+'3'*32,
        'price':.001,'liquidity':30000,'valuation':60000,'valuation_type':'Market cap',
        'buy_count_5m':10,'sell_count_5m':5,'change_5m':2,'risk':{'status':'pending'}},
        'verdict':{'tone':'gray','title':'Faltam dados para avaliar reentrada','text':'Sem candles suficientes.'},
        'chart':{'status':'insufficient','reason':'Menos de 20 candles completos.','candles':[]},'source_errors':[],
        'limitations':['Venda não simulada.']}


def test_manual_submenu_only_queries_on_submit_and_clears_old_report_after_failure(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY','sb_publishable_example')
    profile={'id':'user','username':'teste','display_name':'Teste','role':'user','active':True}
    def action(name,**kwargs):
        assert name=='analyze_contract'
        return {'analysis':report(kwargs['chain'],kwargs['objective'])}
    with patch('supabase.create_client'),patch('pump.account.ensure_session',return_value=True),patch('pump.storage.PublicMarketStore.read',return_value={'tokens':{},'alerts':[],'run':{}}),patch('pump.storage.PublicMarketStore.read_history',return_value=[]),patch('pump.account.action',side_effect=action) as api:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        app.session_state['sniper_profile']=profile;app.session_state['sniper_session']={'access_token':'token'}
        app.run();assert not app.exception
        app.sidebar.button(key='nav_contract').click().run()
        assert not app.exception and api.call_count==0
        app.selectbox(key='manual_objective').set_value('reentry')
        app.text_input(key='manual_contract').set_value('2'*32)
        submit=next(b for b in app.button if b.label=='Analisar agora')
        submit.click().run()
        assert not app.exception and api.call_count==1
        assert api.call_args.kwargs['objective']=='reentry'
        assert any('Faltam dados para avaliar reentrada' in i.value for i in app.info)
        api.side_effect=AccountError('Aguarde 30 segundos')
        next(b for b in app.button if b.label=='Analisar agora').click().run()
        assert not app.exception and 'manual_result' not in app.session_state
        assert any('30 segundos' in e.value for e in app.error)
