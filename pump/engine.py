import hashlib
import time
import uuid
from dataclasses import asdict

from pump.alerts import deliver_pending
from pump.gmgn import APIError, DataError, address_ok, number, discovery_risk, enrich_discovery
from pump.rules import evaluate


def add_alert(state, token, kind, reasons, now, rules, demo):
    events = token.setdefault('last_alert', {})
    if now - events.get(kind, 0) < rules.cooldown_seconds:
        return
    events[kind] = now
    event_id = hashlib.sha256(f"{token['address']}:{kind}:{now}".encode()).hexdigest()[:24]
    state['alerts'].append({'id': event_id, 'address': token['address'], 'kind': kind,
        'created_at': now, 'reasons': reasons, 'snapshot': token.get('snapshot') or {},
        'demo': demo, 'delivery': 'demo' if demo else 'pending', 'attempts': 0})


def apply_snapshot(state, token, snapshot, rules, now, demo=False):
    previous = token.get('snapshot')
    verdict = evaluate(snapshot, rules, now, previous)
    token.update(last_checked=now, snapshot=snapshot)
    token.setdefault('history', []).append({k: snapshot.get(k) for k in
        ('observed_at', 'price', 'liquidity', 'holders', 'volume_5m', 'top10')})
    token['history'] = token['history'][-30:]
    old_status = token.get('status')
    token['reasons'] = verdict['reasons']
    token['missing'] = verdict['missing']
    if verdict['status'] == 'qualified':
        last = token.get('qualified_at', 0)
        dt = now - last
        confirmed = last > 0 and rules.confirmation_min_seconds <= dt <= rules.confirmation_max_seconds
        token['qualified_at'] = now
        token['status'] = 'candidate' if confirmed else 'confirming'
        if token['status'] == 'candidate' and old_status != 'candidate':
            token['last_signal_at'] = now
            add_alert(state, token, 'candidate', verdict['reasons'], now, rules, demo)
    else:
        token['qualified_at'] = 0
        token['status'] = verdict['status']
        if old_status == 'candidate':
            kind = 'data_gap' if verdict['status'] == 'incomplete' else 'conditions_lost'
            add_alert(state, token, kind, verdict['reasons'], now, rules, demo)


def scan(store, api, rules, config=None, demo=False):
    owner = str(uuid.uuid4())
    if not store.acquire(owner):
        return 'busy'
    try:
        state = store.read()
        if state.get('backoff_until', 0) > time.time():
            return 'cooldown'
        started = time.time()
        state['run'] = {'started_at': started, 'status': 'running', 'demo': demo,
                        'rules': asdict(rules), 'checked': 0, 'errors': 0}
        store.commit(owner, state)
        try:
            discovered = api.discover()
            now = time.time()
            tokens = state['tokens']
            expired = [a for a,t in tokens.items() if now-t['first_seen'] > rules.retention_hours*3600
                       and t.get('status') != 'candidate']
            for a in expired:
                del tokens[a]
            for item in discovered:
                if not isinstance(item, dict):
                    continue
                a, liquidity = item.get('address'), number(item.get('liquidity'))
                if not address_ok(a):
                    continue
                risk_data = discovery_risk(item, now)
                if a in tokens:
                    tokens[a]['discovery_risk'] = risk_data
                    continue
                if liquidity is not None and liquidity < rules.min_liquidity:
                    continue
                if len(tokens) >= rules.max_tracked:
                    # Retire oldest non-candidate only after it has actually been examined.
                    removable = [t for t in tokens.values() if t.get('status') not in ('candidate','confirming')
                                 and now-t.get('last_checked', now) > 600 and t.get('last_checked', 0) > 0]
                    if not removable:
                        continue
                    del tokens[min(removable, key=lambda t:t['first_seen'])['address']]
                tokens[a] = {'address': a, 'first_seen': now, 'last_checked': 0,
                             'status': 'queued', 'reasons': [], 'history': [], 'discovery_risk': risk_data}
            # Half reserved for existing candidates, half for fair discovery/rechecks.
            ordered = sorted(tokens.values(), key=lambda t:t.get('last_checked', 0))
            hot = [t for t in ordered if t.get('status') in ('candidate','confirming')][:rules.batch_size//2]
            selected = hot + [t for t in ordered if t not in hot][:rules.batch_size-len(hot)]
            for token in selected:
                store.commit(owner, state)  # Heartbeat/lease renewal, pending state persisted.
                now = time.time()
                try:
                    snapshot = api.snapshot(token['address'])
                    now = time.time()
                    snapshot = enrich_discovery(snapshot, token.get('discovery_risk'), now)
                    apply_snapshot(state, token, snapshot, rules, now, demo)
                except (DataError, APIError) as exc:
                    if isinstance(exc, APIError) and exc.kind in ('rate_limit','auth','missing_key','cli_missing'):
                        raise
                    was_candidate = token.get('status') == 'candidate'
                    token.update(status='incomplete', qualified_at=0, last_checked=now,
                                 reasons=['Consulta indisponível ou formato incompatível; confirmação interrompida'])
                    state['run']['errors'] += 1
                    if was_candidate:
                        add_alert(state, token, 'data_gap', token['reasons'], now, rules, demo)
                state['run']['checked'] += 1
            state['run'].update(status='partial' if state['run']['errors'] else 'ok', completed_at=time.time())
            state['backoff_until'] = 0
        except (APIError, DataError) as exc:
            kind = exc.kind if isinstance(exc, APIError) else 'schema_changed'
            state['run'].update(status='error', error=kind, completed_at=time.time())
            state['backoff_until'] = time.time() + 600
        # Keep pending notifications even when the visible archive is trimmed.
        pending = [a for a in state['alerts'] if a.get('delivery') == 'pending']
        archive = [a for a in state['alerts'] if a.get('delivery') != 'pending'][-200:]
        state['alerts'] = (archive + pending)[-400:]
        store.commit(owner, state)  # Outbox committed before any external send.
        deliver_pending(state, config or {})
        store.commit(owner, state)
        return state['run']['status']
    finally:
        store.release(owner)
