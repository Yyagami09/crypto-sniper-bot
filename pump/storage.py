import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from pump.config import ROOT


class StorageError(RuntimeError):
    pass


class LeaseLost(StorageError):
    pass


def empty_state():
    return {'tokens': {}, 'alerts': [], 'run': {}, 'backoff_until': 0, 'version': 1}


class LocalStore:
    """Only for demo/testing; same lease semantics as production."""
    def __init__(self, path=None):
        self.path = str(path or ROOT / 'demo.sqlite3')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('create table if not exists state (id integer primary key, payload text, owner text, expires real)')
            db.execute('insert or ignore into state values (1, ?, null, 0)', (json.dumps(empty_state()),))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def read(self):
        with self.connect() as db:
            return json.loads(db.execute('select payload from state where id=1').fetchone()[0])

    def acquire(self, owner):
        with self.connect() as db:
            return db.execute('update state set owner=?, expires=? where id=1 and (expires < ? or owner=?)',
                              (owner, time.time()+120, time.time(), owner)).rowcount == 1

    def commit(self, owner, state):
        with self.connect() as db:
            n = db.execute('update state set payload=?, expires=? where id=1 and owner=? and expires>?',
                           (json.dumps(state, allow_nan=False), time.time()+120, owner, time.time())).rowcount
            if not n:
                raise LeaseLost('Processo perdeu a exclusividade da varredura')

    def release(self, owner):
        with self.connect() as db:
            db.execute('update state set owner=null, expires=0 where id=1 and owner=?', (owner,))


class SupabaseStore:
    def __init__(self, url, key):
        if not url.startswith('https://') or not key:
            raise StorageError('Configure SUPABASE_URL e PUMP_SUPABASE_KEY')
        self.url = url.rstrip('/') + '/rest/v1/'
        self.key = key

    def request(self, path, body=None):
        headers = {'apikey': self.key, 'Content-Type': 'application/json'}
        if self.key.startswith('eyJ') and self.key.count('.') == 2:
            headers['Authorization'] = 'Bearer ' + self.key
        req = urllib.request.Request(self.url + path,
            data=json.dumps(body, allow_nan=False).encode() if body is not None else None,
            headers=headers, method='POST' if body is not None else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except (urllib.error.URLError, ValueError):
            raise StorageError('Supabase indisponível: confira conexão, chave do servidor e migração SQL') from None

    def read(self):
        rows = self.request('pump_radar_state?id=eq.main&select=payload')
        if not isinstance(rows, list) or len(rows) != 1:
            raise StorageError('Execute a migração SQL do Pump Trader')
        return rows[0]['payload']

    def acquire(self, owner):
        return self.request('rpc/pump_acquire', {'p_owner': owner}) is True

    def commit(self, owner, state):
        if self.request('rpc/pump_commit', {'p_owner': owner, 'p_payload': state}) is not True:
            raise LeaseLost('Processo perdeu a exclusividade da varredura')

    def release(self, owner):
        self.request('rpc/pump_release', {'p_owner': owner})


class PublicMarketStore(SupabaseStore):
    """Read-only shared market feed. Does not expose the private radar state."""
    def __init__(self, url, key):
        if not url or not key:
            raise StorageError('Configure SUPABASE_URL e SUPABASE_KEY, já usados pelo Game Sniper')
        super().__init__(url, key)

    def read(self):
        rows = self.request('pump_market_feed?id=eq.public&select=payload')
        if not isinstance(rows, list) or len(rows) != 1:
            raise StorageError('Feed de mercado aguardando publicação')
        return rows[0]['payload']


def make_store(config, demo=False):
    return LocalStore(config.get('PUMP_LOCAL_DB') or None) if demo else SupabaseStore(
        config.get('SUPABASE_URL', ''), config.get('PUMP_SUPABASE_KEY') or config.get('SUPABASE_KEY', ''))
