"""Synthetic observations only; these names/addresses are not recommendations."""
import time
import uuid

from pump.engine import apply_snapshot
from pump.storage import empty_state

ADDRESSES = ['2' * 32, '3' * 32, '4' * 32, '5' * 32]


def sample(index, now):
    return {'address': ADDRESSES[index], 'symbol': ['DEMO-A', 'DEMO-B', 'DEMO-C', 'DEMO-D'][index],
        'name': 'Exemplo simulado', 'observed_at': now, 'price': .0011, 'market_cap': 1100000,
        'liquidity': 65000, 'holders': 450, 'created_at': now-7200, 'launchpad_status': 2,
        'volume_5m': 18000, 'buy_volume_5m': 11000, 'sell_volume_5m': 7000,
        'change_5m': 10, 'top10': .15, 'rug': .05, 'bundler': .08, 'insider': .05,
        'mint_disabled': True, 'freeze_disabled': True, 'wash_trading': False,
        'burn_status': 'burn', 'smart_wallets': 3}


class DemoAPI:
    def discover(self):
        return [{'address': a, 'liquidity': 65000} for a in ADDRESSES]

    def snapshot(self, address):
        i = ADDRESSES.index(address)
        s = sample(i, time.time())
        if i == 1:
            s['mint_disabled'] = False
        elif i == 2:
            s['top10'] = None
        elif i == 3:
            s['volume_5m'] = 1000
        return s


def seed_demo(store, rules):
    owner = str(uuid.uuid4())
    if not store.acquire(owner):
        return False
    try:
        state, now = empty_state(), time.time()
        api = DemoAPI()
        for i, address in enumerate(ADDRESSES):
            token = {'address': address, 'first_seen': now-60, 'last_checked': 0, 'history': []}
            state['tokens'][address] = token
            s = api.snapshot(address)
            s['observed_at'] = now-60
            apply_snapshot(state, token, s, rules, now-60, demo=True)
            apply_snapshot(state, token, api.snapshot(address), rules, now, demo=True)
        state['run'] = {'demo': True, 'status': 'ok', 'checked': 4, 'errors': 0,
                        'started_at': now, 'completed_at': now}
        store.commit(owner, state)
        return True
    finally:
        store.release(owner)
