from copy import deepcopy
import pytest
from pump.criteria import adherence

NOW = 2_000_000_000
RULES = {'min_liquidity':25000,'min_volume_5m':5000,'min_transactions_5m':10,
         'min_buy_sell_count_ratio':1.2,'min_change_5m':2,'max_change_5m':40,
         'min_pool_age_minutes':15,'max_pool_age_minutes':10080,
         'min_valuation':100000,'max_valuation':10000000,'confirmation_max_seconds':1200}


def token():
    return {'address':'2'*32,'status':'confirming','snapshot':{
        'profile':'free-market-v1','observed_at':NOW,'price':.001,
        'liquidity':25000,'volume_5m':5000,'buy_count_5m':12,'sell_count_5m':10,
        'change_5m':2,'pool_created_at':NOW-900,'valuation':100000,
        'valuation_type':'FDV','mint_disabled':True,'freeze_disabled':True,'extensions_review':False}}


def test_full_score_does_not_confirm_or_mutate_the_token():
    t = token()
    before = deepcopy(t)
    model = adherence(t,RULES,NOW)
    assert model['score']==100 and model['passed']==7
    assert model['checks'][-1]['label']=='FDV'
    assert t==before and t['status']=='confirming'


def test_six_criteria_mean_86_and_failed_criterion_is_explainable():
    t = token()
    t['status']='watch'
    t['snapshot']['volume_5m']=4999
    result = adherence(t,RULES,NOW)
    assert result['score']==86 and result['passed']==6
    assert [c['label'] for c in result['checks'] if c['passed'] is False]==['Volume em 5 min']


@pytest.mark.parametrize('field,value', [('liquidity',None),('buy_count_5m',None),
    ('price',None),('price',0),('mint_disabled',None),('freeze_disabled',None),
    ('extensions_review',True),('valuation',float('nan')),('observed_at',NOW+60)])
def test_missing_invalid_or_unverified_data_never_get_a_numeric_score(field,value):
    t = token()
    t['snapshot'][field]=value
    assert adherence(t,RULES,NOW)['score'] is None


@pytest.mark.parametrize('status',['blocked','incomplete','queued'])
def test_blocked_or_pending_state_never_displays_full_score(status):
    t = token()
    t['status']=status
    assert adherence(t,RULES,NOW)['score'] is None


def test_zero_sells_fail_ratio_without_division_by_zero_and_counts_are_not_usd():
    t = token()
    t['snapshot'].update(sell_count_5m=0,buy_volume_5m=1_000_000,sell_volume_5m=1)
    result = adherence(t,RULES,NOW)
    assert result['score']==86
    assert result['checks'][3]['passed'] is False


def test_staleness_and_age_use_the_recorded_observation():
    t = token()
    assert adherence(t,RULES,NOW+600)['age_minutes']==15
    result = adherence(t,RULES,NOW+1201)
    assert result['score'] is None and result['issue']=='Consulta antiga'
    assert result['stale']


def test_missing_rules_are_pending_rather_than_using_hidden_defaults():
    assert adherence(token(),{},NOW)['score'] is None


def test_card_escapes_provider_text_and_builds_only_dex_links():
    from pump.radar_cards import card_markup, chart_url
    t = token()
    t['snapshot'].update(symbol='<script>alert(1)</script>',name='<img onerror=x>',pair_url='javascript:alert(1)')
    markup = card_markup(t,adherence(t,RULES,NOW))
    assert '<script>' not in markup and '<img' not in markup
    assert '&lt;script&gt;' in markup
    assert chart_url(t)=='https://dexscreener.com/solana/'+'2'*32
