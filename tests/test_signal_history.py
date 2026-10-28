from copy import deepcopy
from pump.signal_history import recent_confirmations, current_situation
from pump.criteria import adherence
from pump.radar_cards import card_markup, confirmed_find
from tests.test_criteria import NOW, RULES, token


def record(created=NOW-3600):
    t=token()
    t['snapshot'].update(observed_at=created,pool_created_at=created-3600)
    return {'payload':{'id':'saved','kind':'candidate','address':t['address'],
        'created_at':created,'snapshot':t['snapshot'],'reasons':['Confirmado']},'rules':RULES}


def test_losing_criteria_or_leaving_radar_cannot_remove_original_confirmation():
    row=record()
    before=deepcopy(row)
    assert len(recent_confirmations([row],NOW))==1
    assert 'Fora do radar' in current_situation(None,NOW)
    assert 'Rejeitada' in current_situation({'status':'blocked','last_checked':NOW},NOW)
    assert row==before
    original={'address':row['payload']['address'],'status':'candidate','snapshot':row['payload']['snapshot']}
    model=adherence(original,RULES,row['payload']['created_at'])
    assert model['score']==100
    assert confirmed_find(original,model)
    markup=card_markup(original,model,historical=True)
    assert 'Aderência na confirmação' in markup and 'Achado registrado' in markup


def test_original_confirmation_expires_after_24h_not_after_new_verifications():
    row=record(NOW-86400+1)
    assert recent_confirmations([row],NOW)==[row]
    assert recent_confirmations([row],NOW+1)==[]
    assert recent_confirmations([row],NOW+300)==[]


def test_deduplication_future_and_other_events_do_not_create_fake_finds():
    row=record()
    future=record(NOW+100)
    lost=deepcopy(row)
    lost['payload']['kind']='conditions_lost'
    assert recent_confirmations([row,row,lost,future],NOW)==[row]
