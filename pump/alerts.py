import json
import time
import urllib.error
import urllib.request

LABELS = {'candidate': 'CANDIDATA A ACOMPANHAMENTO', 'conditions_lost': 'CONDIÇÕES PERDIDAS',
          'data_gap': 'CONSULTA INDISPONÍVEL'}


def alert_text(alert):
    s = alert['snapshot']
    label = LABELS[alert['kind']]
    if alert.get('demo'):
        label = 'DEMONSTRAÇÃO — ' + label
    return '\n'.join([
        f"Crypto Sniper | {label}",
        f"{s.get('symbol', '?')} | Solana",
        f"CA: {alert['address']}",
        *[str(x)[:250] for x in alert['reasons']],
        f"Consulta: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(alert['created_at']))}",
        'Triagem por regras experimentais. Confira os dados atuais antes de decidir.',
        f"https://gmgn.ai/sol/token/{alert['address']}"])


def deliver_pending(state, config, now=None):
    """Outbox bounded retries. Called only by the elected background worker."""
    now = now or time.time()
    sent_in_batch = 0
    for alert in state['alerts']:
        # Demo never sends external notifications, even if environment has a bot.
        if alert.get('demo') or alert.get('delivery') != 'pending':
            continue
        if now - alert['created_at'] > 900:
            alert['delivery'] = 'expired'
            continue
        if not config.get('TELEGRAM_BOT_TOKEN') or not config.get('TELEGRAM_CHAT_ID'):
            continue
        if alert.get('attempts', 0) >= 3:
            alert['delivery'] = 'failed'
            continue
        if alert.get('next_attempt', 0) > now:
            continue
        if sent_in_batch >= 3:
            break
        sent_in_batch += 1
        alert['attempts'] = alert.get('attempts', 0) + 1
        req = urllib.request.Request(
            'https://api.telegram.org/bot' + config['TELEGRAM_BOT_TOKEN'] + '/sendMessage',
            data=json.dumps({'chat_id': config['TELEGRAM_CHAT_ID'], 'text': alert_text(alert),
                             'link_preview_options': {'is_disabled': True}}).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.load(response)
            alert['delivery'] = 'sent' if result.get('ok') else 'failed'
        except (urllib.error.URLError, ValueError):
            # Never log exception URLs: a Telegram URL embeds the bot credential.
            alert['next_attempt'] = now + 120
            if alert['attempts'] >= 3:
                alert['delivery'] = 'failed'
