from pump.manual_score import evaluate

NOW=2000000000


def complete(objective='general'):
    return {'chain':'solana','objective':objective,'queried_at':NOW,'snapshot':{
        'price':.001,'liquidity':30000,'volume_5m':10000,'sell_count_5m':8,
        'mint_disabled':True,'freeze_disabled':True,'extensions_review':False,
        'risk':{'status':'reviewed','checked_at':NOW,'report_fetched_at':NOW,
                'lp_chain_checked':True,'lp_locked_pct':100,'top10_ex_pool_pct':30,'creator_pool_claim_pct':0,
                'rugcheck':{'status':'reported','critical':[],'warnings':[],'other':[]}}},
        'chart':{'status':'available','candles':[[NOW-60]],'higher_lows_last3':True,'volume_last5_vs_prior5':1.2},
        'verdict':{'tone':'blue'}}


def test_complete_evidence_can_be_favorable_without_claiming_buy_or_profit():
    m=evaluate(complete(),NOW)
    assert m['score']==100 and m['title']=='Favorável para observar' and not m['missing']
    assert sum(x['weight'] for x in m['rows'])==100


def test_high_score_never_overrides_a_single_restriction():
    r=complete();r['snapshot']['freeze_disabled']=False
    m=evaluate(r,NOW)
    assert m['score']==90 and m['tone']=='red'


def test_missing_and_old_reports_do_not_pass_or_reweight_score():
    r=complete();r['snapshot']['risk']['report_fetched_at']=NOW-1801
    m=evaluate(r,NOW)
    assert m['score']==55 and m['missing']==4 and m['tone']=='gray'
    r['snapshot']['risk']['report_fetched_at']=NOW
    r['snapshot']['risk']['lp_chain_checked']=False
    m=evaluate(r,NOW)
    assert m['score']==75 and m['missing']==2 and m['tone']=='gray'


def test_stale_query_and_unsupported_chain_are_never_favorable():
    r=complete();assert evaluate(r,NOW+181)['score']==0
    r['chain']='base';m=evaluate(r,NOW)
    assert m['tone']=='gray' and m['score']==30


def test_reentry_needs_candles_and_recovery_while_risk_focus_excludes_timing():
    r=complete('reentry');r['chart']={'status':'insufficient'}
    m=evaluate(r,NOW);assert m['tone']=='gray' and m['score']==90
    r=complete('reentry');r['chart']['higher_lows_last3']=False
    assert evaluate(r,NOW)['tone']=='yellow'
    r=complete('risk');r['chart']={'status':'not_requested'}
    m=evaluate(r,NOW)
    assert m['total']==90 and m['score']==100 and m['title']=='Favorável na triagem de risco'


def test_critical_provider_and_backend_blocks_precede_missing_candles():
    r=complete('reentry');r['chart']={'status':'insufficient'}
    r['snapshot']['risk']['rugcheck']['critical']=['LP unlocked']
    assert evaluate(r,NOW)['tone']=='red'
    r=complete();r['snapshot']['risk']['status']='blocked'
    assert evaluate(r,NOW)['tone']=='red'


def test_warning_and_zero_sells_do_not_turn_green():
    r=complete();r['snapshot']['risk']['rugcheck']['warnings']=['Low holders']
    assert evaluate(r,NOW)['tone']=='yellow'
    r=complete();r['snapshot']['sell_count_5m']=0
    assert evaluate(r,NOW)['tone']=='yellow'


def test_missing_price_does_not_earn_market_points():
    r=complete();r['snapshot']['price']=None
    m=evaluate(r,NOW)
    assert m['tone']=='gray' and m['score']==90 and m['missing']==1
