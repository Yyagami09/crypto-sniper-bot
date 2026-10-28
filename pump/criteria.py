"""Presentation-only adherence to the seven free-market screening rules.

Never changes a token's state, confirms an event or estimates profitability.
"""
import math


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def adherence(token, rules, now, require_risk=True):
    s = token.get('snapshot') or {}
    def val(key):
        return number(s.get(key))
    def rule(key):
        return number(rules.get(key))
    checks = []
    def minimum(label, value, threshold, unit):
        passed = None if value is None or threshold is None else value >= threshold
        checks.append({'label':label, 'passed':passed,
            'value':'Indisponível' if value is None else f'{value:,.0f} {unit}'.strip(),
            'target':'Limite indisponível' if threshold is None else f'Mínimo: {threshold:,.0f} {unit}'.strip()})
    def interval(label, value, low, high, unit):
        passed = None if value is None or low is None or high is None else low <= value <= high
        checks.append({'label':label, 'passed':passed,
            'value':'Indisponível' if value is None else f'{value:,.2f} {unit}'.strip(),
            'target':'Faixa indisponível' if low is None or high is None else f'Faixa: {low:,.0f} a {high:,.0f} {unit}'.strip()})
    minimum('Liquidez', val('liquidity'), rule('min_liquidity'), 'USD')
    minimum('Volume em 5 min', val('volume_5m'), rule('min_volume_5m'), 'USD')
    buys, sells = val('buy_count_5m'), val('sell_count_5m')
    minimum('Quantidade de transações', None if buys is None or sells is None else buys+sells,
            rule('min_transactions_5m'), '')
    ratio = None if buys is None or sells is None or sells <= 0 else buys/sells
    threshold = rule('min_buy_sell_count_ratio')
    checks.append({'label':'Relação compras/vendas (quantidade)',
        'passed':None if buys is None or sells is None or threshold is None else sells>0 and buys/sells>=threshold,
        'value':'Sem vendas observadas' if sells==0 else 'Indisponível' if ratio is None else f'{ratio:.2f}×',
        'target':'Limite indisponível' if threshold is None else f'Mínimo: {threshold:.2f}×'})
    interval('Variação em 5 min', val('change_5m'), rule('min_change_5m'), rule('max_change_5m'), '%')
    observed, created = val('observed_at'), val('pool_created_at')
    age = (observed-created)/60 if observed and created and 0<created<=observed else None
    interval('Idade da pool na consulta', age, rule('min_pool_age_minutes'), rule('max_pool_age_minutes'), 'min')
    interval(s.get('valuation_type', 'Avaliação de mercado'), val('valuation'), rule('min_valuation'), rule('max_valuation'), 'USD')
    passed = sum(c['passed'] is True for c in checks)
    max_age = number(rules.get('confirmation_max_seconds')) or 1200
    stale = observed is not None and now-observed>max_age
    status = token.get('status', 'queued')
    risk = s.get('risk') or {}
    risk_checked = number(risk.get('checked_at'))
    issue = None
    if status=='blocked' or risk.get('status')=='blocked' or s.get('mint_disabled') is False or s.get('freeze_disabled') is False:
        issue = 'Bloqueada pelas verificações'
    elif stale:
        issue = 'Consulta antiga'
    elif require_risk and (risk.get('version')!='risk-v1' or risk.get('status')!='reviewed' or risk.get('lp_chain_checked') is not True or risk_checked is None or not 0<=now-risk_checked<=1200):
        issue = 'Pontuação pendente · camada de risco'
    elif (status in ('incomplete','queued') or s.get('profile')!='free-market-v1' or
          any(c['passed'] is None for c in checks) or s.get('mint_disabled') is not True or
          s.get('freeze_disabled') is not True or s.get('extensions_review') is not False or
          val('price') is None or val('price')<=0 or observed is None or observed<=0 or observed>now+30):
        issue = 'Pontuação pendente'
    return {'score':None if issue else round(100*passed/7), 'passed':passed, 'total':7,
            'checks':checks, 'issue':issue, 'stale':stale, 'age_minutes':age}
