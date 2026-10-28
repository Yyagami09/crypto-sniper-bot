"""Adapter for documented gmgn-cli 1.6.9 read-only commands."""
import json
import math
import os
import re
import subprocess
import time


class DataError(RuntimeError):
    pass


class APIError(RuntimeError):
    def __init__(self, kind):
        self.kind = kind
        super().__init__(kind)


def address_ok(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', value))


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def boolean(value):
    if value is True or value == 1 or value in ('true', '1', 'yes'):
        return True
    if value is False or value == 0 or value in ('false', '0', 'no'):
        return False
    return None


def unwrap(payload):
    if not isinstance(payload, dict):
        raise DataError('Resposta GMGN incompatível')
    if payload.get('code') not in (None, 0, '0'):
        code = str(payload.get('code'))
        raise APIError('rate_limit' if code == '429' else 'auth' if code in ('401','403') else 'api_rejected')
    return payload.get('data', payload)


class GMGN:
    def __init__(self, config):
        if not config.get('GMGN_API_KEY'):
            raise APIError('missing_key')
        self.executable = config.get('GMGN_CLI') or 'gmgn-cli'
        self.env = dict(os.environ, GMGN_API_KEY=config['GMGN_API_KEY'])
        # This adapter has no signing credentials and no swap/order methods.
        self.env.pop('GMGN_PRIVATE_KEY', None)
        self.last_call = 0

    def call(self, args):
        time.sleep(max(0, 1.1 - (time.monotonic() - self.last_call)))
        self.last_call = time.monotonic()
        try:
            proc = subprocess.run([self.executable, *args, '--raw'], env=self.env,
                                  capture_output=True, text=True, timeout=35, check=False)
        except FileNotFoundError:
            raise APIError('cli_missing') from None
        except subprocess.TimeoutExpired:
            raise APIError('timeout') from None
        if proc.returncode:
            message = proc.stderr + proc.stdout
            if any(x in message for x in ('429', 'RATE_LIMIT', 'PLAN_UPGRADE_REQUIRED')):
                raise APIError('rate_limit')
            if any(x in message for x in ('401', '403', 'Unauthorized')):
                raise APIError('auth')
            raise APIError('cli_failed')
        # Suspicious metadata detected by upstream must never silently become a candidate.
        if 'suspicious metadata' in proc.stderr.lower():
            raise DataError('Metadados suspeitos sinalizados pelo provedor')
        try:
            return unwrap(json.loads(proc.stdout))
        except json.JSONDecodeError:
            raise DataError('CLI não retornou JSON válido') from None

    def discover(self):
        recent = self.call(['market', 'trenches', '--chain', 'sol', '--type', 'completed', '--limit', '50'])
        trending = self.call(['market', 'trending', '--chain', 'sol', '--interval', '5m', '--limit', '50'])
        if not isinstance(recent, dict) or not isinstance(recent.get('completed'), list):
            raise DataError('Formato de Trenches alterado')
        if not isinstance(trending, dict) or not isinstance(trending.get('rank'), list):
            raise DataError('Formato de Trending alterado')
        return recent['completed'] + trending['rank']

    def snapshot(self, address):
        if not address_ok(address):
            raise DataError('Endereço Solana inválido')
        info = self.call(['token', 'info', '--chain', 'sol', '--address', address])
        security = self.call(['token', 'security', '--chain', 'sol', '--address', address])
        return normalize(address, info, security, time.time())


def normalize(address, info, security, now):
    if not isinstance(info, dict) or not isinstance(security, dict) or info.get('address') != address:
        raise DataError('Token ou formato da resposta não corresponde à consulta')
    price = info.get('price')
    if not isinstance(price, dict):
        raise DataError('Objeto price ausente ou incompatível')
    p = number(price.get('price'))
    supply = number(info.get('circulating_supply'))
    p5 = number(price.get('price_5m'))
    def risk(key):
        # No defaults to zero for absent/unknown metrics.
        n = number(security.get(key))
        return n if n is not None and 0 <= n <= 1 else None
    stat = info.get('stat') if isinstance(info.get('stat'), dict) else {}
    def with_stat(key, stat_key):
        value = risk(key)
        if value is not None:
            return value
        n = number(stat.get(stat_key))
        return n if n is not None and 0 <= n <= 1 else None
    def nonnegative(value):
        n = number(value)
        return n if n is not None and n >= 0 else None
    return {
        'address': address, 'symbol': str(info.get('symbol') or '?')[:30],
        'name': str(info.get('name') or '')[:100], 'observed_at': now,
        'price': p if p and p > 0 else None,
        'market_cap': p * supply if p and supply and p > 0 and supply > 0 else None,
        'liquidity': nonnegative(info.get('liquidity')),
        'holders': nonnegative(info.get('holder_count')),
        'created_at': number(info.get('creation_timestamp')),
        'launchpad_status': number(info.get('launchpad_status')),
        'volume_5m': nonnegative(price.get('volume_5m')),
        'buy_volume_5m': nonnegative(price.get('buy_volume_5m')),
        'sell_volume_5m': nonnegative(price.get('sell_volume_5m')),
        'change_5m': (p / p5 - 1) * 100 if p and p5 and p > 0 and p5 > 0 else None,
        'top10': risk('top_10_holder_rate'), 'rug': risk('rug_ratio'),
        'bundler': with_stat('bundler_trader_amount_rate', 'top_bundler_trader_percentage'),
        'insider': with_stat('rat_trader_amount_rate', 'top_rat_trader_percentage'),
        'mint_disabled': boolean(security.get('renounced_mint')),
        'freeze_disabled': boolean(security.get('renounced_freeze_account')),
        'wash_trading': boolean(security.get('is_wash_trading')),
        'burn_status': str(security.get('burn_status') or 'não informado'),
        'smart_wallets': number((info.get('wallet_tags_stat') or {}).get('smart_wallets')),
        'sources': {'market': 'token/info', 'permissions': 'token/security',
                    'concentration': 'token/security', 'activity_risk': 'token/security ou token/info.stat'},
    }


def discovery_risk(item, now):
    return {'observed_at': now, 'rug': number(item.get('rug_ratio')),
            'wash_trading': boolean(item.get('is_wash_trading')),
            'bundler': number(item.get('bundler_rate')),
            'insider': number(item.get('rat_trader_amount_rate'))}


def enrich_discovery(snapshot, discovery, now):
    """Use only recent, same-address discovery risk values; never stale defaults."""
    if not discovery or not 0 <= now-discovery.get('observed_at', 0) <= 120:
        return snapshot
    for key in ('rug','bundler','insider','wash_trading'):
        if snapshot.get(key) is not None:
            continue
        value = discovery.get(key)
        valid = isinstance(value, bool) if key == 'wash_trading' else (
            value is not None and not isinstance(value, bool) and 0 <= value <= 1)
        if valid:
            snapshot[key] = value
            snapshot.setdefault('sources', {})[key] = {
                'route': 'market/trenches ou market/trending', 'observed_at': discovery['observed_at']}
    return snapshot
