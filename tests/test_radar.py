import copy
import json
import time
from dataclasses import replace
from unittest.mock import patch

import pytest

from pump.alerts import deliver_pending
from pump.config import Rules
from pump.demo import ADDRESSES, DemoAPI, sample, seed_demo
from pump.engine import apply_snapshot, scan
from pump.gmgn import APIError, DataError, GMGN, boolean, normalize, number, enrich_discovery, discovery_risk
from pump.rules import evaluate
from pump.storage import LeaseLost, LocalStore, SupabaseStore, empty_state


@pytest.fixture
def store(tmp_path):
    return LocalStore(tmp_path / 'radar.sqlite3')


def token():
    return {'address': ADDRESSES[0], 'first_seen': time.time(), 'history': []}


def test_normalize_documented_nested_fields_not_total_supply():
    now = time.time()
    info = {'address': ADDRESSES[0], 'price': {'price': '2', 'price_5m': '1',
            'buy_volume_5m': '0'}, 'circulating_supply': '100', 'total_supply': '1000'}
    s = normalize(ADDRESSES[0], info, {}, now)
    assert s['market_cap'] == 200
    assert s['change_5m'] == 100
    assert s['top10'] is None and s['mint_disabled'] is None
    assert s['buy_volume_5m'] == 0


@pytest.mark.parametrize('value', [None, '', 'NaN', 'Infinity', True, {}, []])
def test_unavailable_numeric_values_are_not_zero(value):
    assert number(value) is None


@pytest.mark.parametrize('value', [None, '', 'unknown'])
def test_unknown_flags_are_not_safe(value):
    assert boolean(value) is None


def test_mismatched_token_is_rejected():
    with pytest.raises(DataError):
        normalize(ADDRESSES[0], {'address': ADDRESSES[1], 'price': {}}, {}, time.time())


def test_recent_market_risk_complements_security_and_preserves_zero():
    now = time.time()
    s = sample(0, now)
    s.update(rug=None, wash_trading=None, bundler=None)
    d = discovery_risk({'rug_ratio':0,'is_wash_trading':False,'bundler_rate':0}, now)
    enriched = enrich_discovery(s, d, now+5)
    assert enriched['rug'] == 0 and enriched['wash_trading'] is False and enriched['bundler'] == 0
    assert enriched['sources']['rug']['observed_at'] == now


def test_stale_market_risk_never_completes_security():
    now = time.time()
    s = sample(0, now)
    s['rug'] = None
    d = discovery_risk({'rug_ratio':.01}, now-121)
    assert enrich_discovery(s, d, now)['rug'] is None


def test_security_risk_is_not_overwritten_by_discovery():
    now = time.time()
    s = sample(0, now)
    s['wash_trading'] = True
    enriched = enrich_discovery(s, discovery_risk({'is_wash_trading':False}, now), now)
    assert enriched['wash_trading'] is True


@pytest.mark.parametrize('key', ['top10', 'rug', 'bundler', 'insider', 'mint_disabled', 'wash_trading', 'liquidity'])
def test_missing_critical_field_never_qualifies(key):
    now = time.time()
    s = sample(0, now)
    s[key] = None
    assert evaluate(s, Rules(), now)['status'] == 'incomplete'


def test_explicit_risk_blocks_even_with_other_missing_data():
    now = time.time()
    s = sample(0, now)
    s.update(mint_disabled=False, top10=None)
    assert evaluate(s, Rules(), now)['status'] == 'blocked'


def test_counts_are_not_used_as_buy_sell_volume():
    now = time.time()
    s = sample(0, now)
    s.update(buy_volume_5m=1000, sell_volume_5m=17000, buys=200, sells=1)
    assert evaluate(s, Rules(), now)['status'] == 'watch'


def test_two_observations_and_cooldown_survive_state_serialization():
    now, r, state, t = time.time(), Rules(), empty_state(), token()
    apply_snapshot(state, t, sample(0, now), r, now)
    assert t['status'] == 'confirming' and not state['alerts']
    apply_snapshot(state, t, sample(0, now+60), r, now+60)
    assert t['status'] == 'candidate' and len(state['alerts']) == 1
    t, state = json.loads(json.dumps(t)), json.loads(json.dumps(state))
    bad = sample(0, now+120)
    bad['volume_5m'] = 1
    apply_snapshot(state, t, bad, r, now+120)
    assert state['alerts'][-1]['kind'] == 'conditions_lost'
    for delta in (180, 240):
        apply_snapshot(state, t, sample(0, now+delta), r, now+delta)
    assert t['status'] == 'candidate'
    assert len([a for a in state['alerts'] if a['kind'] == 'candidate']) == 1


def test_long_gap_requires_fresh_confirmation():
    now, r, state, t = time.time(), Rules(), empty_state(), token()
    apply_snapshot(state, t, sample(0, now), r, now)
    apply_snapshot(state, t, sample(0, now+1000), r, now+1000)
    assert t['status'] == 'confirming' and not state['alerts']


def test_liquidity_drop_invalidates_previous_candidate():
    now, state, t, r = time.time(), empty_state(), token(), Rules()
    for delta in (0, 60):
        apply_snapshot(state, t, sample(0, now+delta), r, now+delta)
    s = sample(0, now+120)
    s['liquidity'] = 40000  # Still above min, but materially below last observation.
    apply_snapshot(state, t, s, r, now+120)
    assert t['status'] == 'blocked'
    assert state['alerts'][-1]['kind'] == 'conditions_lost'


def test_lease_excludes_other_worker_and_rejects_late_commit(store):
    assert store.acquire('one')
    assert not store.acquire('two')
    with pytest.raises(LeaseLost):
        store.commit('two', empty_state())
    store.release('one')
    assert store.acquire('two')
    store.commit('two', empty_state())


def test_scan_runs_independently_and_round_robins_unchecked_tokens(store):
    r = replace(Rules(), batch_size=2)
    assert scan(store, DemoAPI(), r, demo=True) == 'ok'
    state = store.read()
    assert sum(t['last_checked'] > 0 for t in state['tokens'].values()) == 2
    scan(store, DemoAPI(), r, demo=True)
    assert sum(t['last_checked'] > 0 for t in store.read()['tokens'].values()) >= 3


def test_rate_limit_stops_cycle_and_survives_worker_restart(store):
    class Limited:
        calls = 0
        def discover(self):
            self.calls += 1
            raise APIError('rate_limit')
    api = Limited()
    assert scan(store, api, Rules()) == 'error'
    restarted_store = LocalStore(store.path)
    assert scan(restarted_store, api, Rules()) == 'cooldown'
    assert api.calls == 1


def test_per_token_failure_clears_previous_confirmation(store):
    seed_demo(store, Rules())
    class Broken(DemoAPI):
        def snapshot(self, address):
            raise DataError('bad')
    assert scan(store, Broken(), Rules(), demo=True) == 'partial'
    state = store.read()
    assert state['tokens'][ADDRESSES[0]]['status'] == 'incomplete'
    assert state['tokens'][ADDRESSES[0]]['qualified_at'] == 0
    assert any(a['kind'] == 'data_gap' for a in state['alerts'])


def test_demo_never_sends_even_with_telegram_credentials(store):
    seed_demo(store, Rules())
    state = store.read()
    with patch('pump.alerts.urllib.request.urlopen') as network:
        deliver_pending(state, {'TELEGRAM_BOT_TOKEN': 'secret', 'TELEGRAM_CHAT_ID':'123'})
    network.assert_not_called()


def test_telegram_send_commits_delivery_state_and_limits_batch():
    import io
    from pump.engine import add_alert
    now, state, t, r = time.time(), empty_state(), token(), Rules()
    t['snapshot'] = sample(0, now)
    for i in range(5):
        add_alert(state, t, 'candidate', ['test'], now+i*2000, r, False)
    # Make all pending events recent for this delivery test.
    for a in state['alerts']:
        a['created_at'] = now
    with patch('pump.alerts.urllib.request.urlopen', side_effect=lambda *a,**k:io.BytesIO(b'{"ok":true}')) as network:
        deliver_pending(state, {'TELEGRAM_BOT_TOKEN':'secret','TELEGRAM_CHAT_ID':'123'}, now)
    assert network.call_count == 3
    assert sum(a['delivery'] == 'sent' for a in state['alerts']) == 3


def test_telegram_failure_retries_and_expires_without_logging_secret():
    import urllib.error
    now, state = time.time(), empty_state()
    a = {'delivery':'pending','created_at':now,'snapshot':{},'address':ADDRESSES[0],
         'kind':'candidate','reasons':[]}
    state['alerts'] = [a]
    with patch('pump.alerts.urllib.request.urlopen', side_effect=urllib.error.URLError('secret')):
        deliver_pending(state, {'TELEGRAM_BOT_TOKEN':'secret','TELEGRAM_CHAT_ID':'123'}, now)
    assert a['attempts'] == 1 and a['delivery'] == 'pending'
    deliver_pending(state, {}, now+1000)
    assert a['delivery'] == 'expired'


def test_cli_is_read_only_uses_no_shell_and_validates_address():
    from subprocess import CompletedProcess
    api = GMGN({'GMGN_API_KEY':'test', 'GMGN_CLI':'gmgn-cli'})
    with patch('pump.gmgn.subprocess.run', return_value=CompletedProcess([],0,'{"code":0,"data":{"rank":[]}}','')) as run:
        assert api.call(['market','trending']) == {'rank':[]}
    assert run.call_args.args[0] == ['gmgn-cli','market','trending','--raw']
    assert 'shell' not in run.call_args.kwargs
    assert 'GMGN_PRIVATE_KEY' not in run.call_args.kwargs['env']
    with pytest.raises(DataError):
        api.snapshot('$(cat /etc/passwd)')


def test_supabase_adapter_rpc_semantics():
    store = SupabaseStore('https://example.supabase.co', 'server-only')
    with patch.object(store, 'request', return_value=True) as request:
        assert store.acquire('owner')
        store.commit('owner', empty_state())
    assert request.call_args.args[0] == 'rpc/pump_commit'
    with patch.object(store, 'request', return_value=False):
        with pytest.raises(LeaseLost):
            store.commit('owner', empty_state())


@pytest.mark.parametrize('kwargs', [{'max_top10':30}, {'interval_seconds':0}, {'batch_size':2.5},
                                    {'max_market_cap':1}, {'min_liquidity':float('nan')}])
def test_bad_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        Rules(**kwargs)
