"""Explicit, uncalibrated screening rules. No predictive safety or profit score."""


def evaluate(s, r, now, previous=None):
    missing = [k for k in ('price', 'market_cap', 'liquidity', 'holders', 'created_at',
               'volume_5m', 'buy_volume_5m', 'sell_volume_5m', 'change_5m',
               'top10', 'rug', 'bundler', 'insider', 'mint_disabled', 'freeze_disabled', 'wash_trading')
               if s.get(k) is None]
    blocked = []
    for key, label in [('mint_disabled', 'Emissão adicional habilitada'),
                       ('freeze_disabled', 'Congelamento habilitado')]:
        if s.get(key) is False:
            blocked.append(label)
    if s.get('wash_trading') is True:
        blocked.append('Provedor sinalizou negociação artificial')
    for key, limit, label in [('top10', r.max_top10, 'Concentração Top 10'),
                             ('rug', r.max_rug, 'Indicador de rug do provedor'),
                             ('bundler', r.max_bundler, 'Atividade de bundles'),
                             ('insider', r.max_insider, 'Atividade de insiders')]:
        if s.get(key) is not None and s[key] > limit:
            blocked.append(f'{label} acima do limite')
    if previous and previous.get('liquidity') and s.get('liquidity') is not None:
        if s['liquidity'] < previous['liquidity'] * (1 - r.liquidity_drop):
            blocked.append('Queda de liquidez acima do limite entre consultas')
    if blocked:
        return {'status': 'blocked', 'reasons': blocked, 'missing': missing}
    if missing:
        return {'status': 'incomplete', 'reasons': ['Dados obrigatórios ausentes: ' + ', '.join(missing)], 'missing': missing}
    age = (now - s['created_at']) / 60
    if s['created_at'] <= 0 or age < 0:
        return {'status': 'incomplete', 'reasons': ['Data de criação inválida'], 'missing': ['created_at']}
    reasons = []
    if not r.min_age_minutes <= age <= r.max_age_minutes:
        reasons.append('Idade fora da janela configurada')
    if s['launchpad_status'] in (0, 1):
        reasons.append('Lançamento ainda não migrado para mercado aberto')
    if s['liquidity'] < r.min_liquidity:
        reasons.append('Liquidez abaixo do mínimo')
    if not r.min_market_cap <= s['market_cap'] <= r.max_market_cap:
        reasons.append('Valor de mercado fora da faixa')
    if s['holders'] < r.min_holders:
        reasons.append('Quantidade de holders abaixo do mínimo')
    if s['volume_5m'] < r.min_volume_5m:
        reasons.append('Volume de 5 minutos abaixo do mínimo')
    buy, sell = s['buy_volume_5m'], s['sell_volume_5m']
    if sell <= 0 or buy / sell < r.min_buy_sell_ratio:
        reasons.append('Relação de volume comprado/vendido insuficiente ou sem vendas observadas')
    if not r.min_change_5m <= s['change_5m'] <= r.max_change_5m:
        reasons.append('Variação de 5 minutos fora da faixa de interesse')
    return {'status': 'watch' if reasons else 'qualified', 'reasons': reasons or [
        'Passou pelos filtros configurados de permissões, concentração, liquidez e atividade'], 'missing': []}
