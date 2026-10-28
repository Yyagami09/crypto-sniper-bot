import time
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from tests.test_dashboard import ROOT
from tests.test_criteria import RULES,token
from pump.early import experiment_tokens


def state_fixture():
    now=time.time();t=token()
    t.update(address='2'*32,status='watch',first_seen=now-60,last_checked=now)
    t['snapshot'].update(chain_id='solana',symbol='EARLY',observed_at=now,pool_created_at=now-180,valuation=60000)
    t['early']={'id':'trial-1','version':'early-v1','first_at':now-60,'first_price':.001,
        'last_at':now,'status':'reviewed','observations':2,'symbol':'EARLY','assessment':{
            'price_since_first_pct':5,'checks':[{'label':'Permissões básicas','state':'met'}]}}
    return {'tokens':{t['address']:t},'early_tokens':{},'alerts':[],
            'run':{'status':'ok','completed_at':now,'rules':RULES}}


def test_stale_experiment_never_displays_as_current_reviewed():
    s=state_fixture();assert experiment_tokens(s,time.time()+300)[0][2]=='pending'


def test_experimental_ui_has_no_market_score_and_rollback_restores_classic(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY','sb_publishable_example')
    profile={'id':'test-id','username':'teste','display_name':'Teste','role':'user','active':True,'radar_mode':'early-v1'}
    state=state_fixture()
    def action(name,**kwargs):
        assert name=='radar_mode' and kwargs['mode']=='classic'
        return {'profile':{**profile,'radar_mode':'classic'}}
    with patch('supabase.create_client'),patch('pump.account.ensure_session',return_value=True),patch('pump.storage.PublicMarketStore.read',return_value=state),patch('pump.storage.PublicMarketStore.read_trials',return_value=[{'payload':next(iter(state['tokens'].values()))['early']}]),patch('pump.storage.PublicMarketStore.read_history',return_value=[]),patch('pump.account.action',side_effect=action) as api:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        app.session_state['sniper_profile']=profile;app.session_state['sniper_session']={'access_token':'user-token'}
        app.run();assert not app.exception
        assert any(t.label=='🧪 Comparação' for t in app.tabs)
        assert not any('100<small>' in m.value or 'ACHADO NO GARIMPO' in m.value for m in app.markdown)
        assert any(m.label=='Vale abrir o gráfico' and m.value=='1' for m in app.metric)
        assert any('POSSÍVEL OPORTUNIDADE · REVISAR GRÁFICO' in m.value for m in app.markdown)
        assert any('Vale abrir o gráfico' in h.value for h in app.subheader)
        app.button(key='early_rollback').click().run()
        assert not app.exception and api.call_count==1
        assert app.session_state['sniper_profile']['radar_mode']=='classic'
        assert any(t.label=='⛏️ Achados · 24h' for t in app.tabs)


def test_low_liquidity_with_twenty_observations_explains_the_actual_obstacle():
    from pump.early_details import explanation
    s=state_fixture();t=next(iter(s['tokens'].values()));r=t['early']
    t['snapshot']['liquidity']=17616;r['observations']=20
    text=explanation(t,r,'observing',time.time())
    assert '17,616' in text and '25.000' in text
    assert 'duas consultas' not in text


def test_missing_or_stale_rugcheck_is_never_shown_as_no_alerts():
    from pump.early_details import rugcheck_summary
    now=time.time()
    assert not rugcheck_summary({'risk':{}},now)['available']
    risk={'report_fetched_at':now-1801,'rugcheck':{'status':'reported','critical':[],'warnings':[]}}
    result=rugcheck_summary({'risk':risk},now)
    assert result['icon']=='❔' and not result['available']
    risk['report_fetched_at']=now
    assert rugcheck_summary({'risk':risk},now)['available']
    risk['rugcheck']['critical']=['LP unlocked']
    assert rugcheck_summary({'risk':risk},now)['icon']=='⛔'


def test_lp_circulating_ownership_does_not_replace_reference_pool_claim_in_explanation():
    from pump.early_details import evidence_rows
    rows=evidence_rows({'risk':{'creator_lp_pct':100,'creator_pool_claim_pct':1,'lp_locked_pct':99}}, {})
    creator=next(r for r in rows if 'criador' in r[1])
    assert creator[2]=='1.0%' and creator[0]=='✓'
    assert 'referência' in creator[3]
