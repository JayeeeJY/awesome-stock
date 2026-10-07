"""Persistent local factual-report schedules. No remote calls or exchange calendar."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import uuid5, NAMESPACE_URL
import re
from . import owner_business as b, owner_diagnosis as diagnosis, owner_daily as daily
from .owner import identifier
from . import owner_diagnosis_scope as scopes
from .local import Conflict


def clock():
    return datetime.now(timezone.utc)


def next_due(config, after):
    zone = ZoneInfo(config['timezone'])
    hour, minute = map(int, config['time'].split(':'))
    first = after.astimezone(zone).date()
    for offset in range(9):
        day = first + timedelta(days=offset)
        if day.weekday() not in config['weekdays']:
            continue
        local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
        candidate = local.astimezone(timezone.utc)
        # A nonexistent spring-forward wall time is skipped. Fall-back uses
        # fold=0 once, not both occurrences of the same requested local time.
        if candidate.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
            continue
        if candidate > after:
            return candidate.isoformat()
    raise ValueError('no valid scheduled time')


def config(raw):
    b.fields(raw, 'enabled timezone time weekdays input')
    if type(raw['enabled']) is not bool or not isinstance(raw['timezone'], str):
        raise ValueError('invalid enabled or timezone')
    try:
        ZoneInfo(raw['timezone'])
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('unsupported timezone') from None
    if not isinstance(raw['time'], str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', raw['time']):
        raise ValueError('invalid local time')
    days = raw['weekdays']
    if not isinstance(days, list) or not days or any(type(x) is not int or not 0 <= x <= 6 for x in days) or len(set(days)) != len(days):
        raise ValueError('invalid weekdays')
    return {**raw, 'weekdays': sorted(days)}


def save(store, body):
    b.fields(body, 'operation_id revision config')
    value = config(body['config'])
    aid = scopes.scope_id(value['input']['account_id'])
    sid = str(uuid5(NAMESPACE_URL, 'owner-daily-schedule:' + aid))
    store._revision(body['revision'])
    with store.transaction() as db:
        fp, old = store._operation(db, body, 'schedule_save')
        if old is not None:
            return old
        current = next((r for r in b.records(db, 'daily_schedule') if r['id'] == sid), None)
        if (current['revision'] if current else 0) != body['revision']:
            raise Conflict('schedule changed')
        if value['enabled'] or current is None:
            diagnosis.calculate(store, db, value['input'])
        elif value['input'] != current['config']['input']:
            raise ValueError('disabled schedule cannot change diagnostic input')
        result = b._put(store, db, {'id': sid, 'revision': body['revision']},
                        {'kind': 'daily_schedule', 'title': '事实日报定时任务', 'account_id': aid,
                         'config': value, 'next_due': next_due(value, clock()) if value['enabled'] else None,
                         'attempts': 0, 'retry_at': None, 'last_status': 'configured'})
        return store._result(db, body, fp, result)


def status(store, account_id):
    scopes.scope_id(account_id)
    with store.connection() as db:
        db.execute('BEGIN')
        rows = b.records(db)
        return {'schedule': next((r for r in rows if r['kind'] == 'daily_schedule' and r['account_id'] == account_id), None),
                'runs': sorted((r for r in rows if r['kind'] == 'schedule_run' and r['account_id'] == account_id),
                               key=lambda r: (r['updated_at'], r['id']), reverse=True)}


def tick(store, at=None):
    at = at or clock()
    if at.tzinfo is None:
        raise ValueError('aware timestamp required')
    completed = []
    with store.transaction() as db:
        for schedule in b.records(db, 'daily_schedule'):
            value = schedule['config']
            due = schedule['next_due']
            if not value['enabled'] or not due or datetime.fromisoformat(schedule['retry_at'] or due) > at:
                continue
            attempt = schedule['attempts'] + 1
            run_id = str(uuid5(NAMESPACE_URL, f"{schedule['id']}:{due}:{attempt}"))
            result = None
            if at - datetime.fromisoformat(due) > timedelta(hours=6):
                outcome = 'missed'
            else:
                db.execute('SAVEPOINT daily_attempt')
                try:
                    data = value['input']
                    account = scopes.resolve(store, db, schedule['account_id'])
                    symbols = {p['symbol'] for p in account['positions']}
                    data = {**data, 'holding_context': {k:v for k,v in data['holding_context'].items() if k in symbols}}
                    result = daily.capture(store, {'operation_id': run_id, 'input': data,
                            'expected_token': diagnosis.evidence_token(store, db)}, _db=db, _source='scheduled')
                    outcome = 'completed'
                except Exception:
                    db.execute('ROLLBACK TO daily_attempt')
                    # Do not persist exception text: it can contain private data.
                    outcome = 'failed'
                finally:
                    db.execute('RELEASE daily_attempt')
            run = b._put(store, db, {'id': run_id, 'revision': 0},
                         {'kind': 'schedule_run', 'title': '定时日报运行', 'account_id': schedule['account_id'],
                          'scheduled_for': due, 'observed_at': at.isoformat(), 'attempt': attempt,
                          'status': outcome, 'brief_id': result['brief']['id'] if result else None,
                          'data_status': result['run']['data_status'] if result else None,
                          'error_code': 'capture_failed' if outcome == 'failed' else None})
            retry = outcome == 'failed' and attempt < 3
            b._put(store, db, {'id': schedule['id'], 'revision': schedule['revision']},
                   {**schedule, 'last_status': outcome, 'last_run_id': run_id,
                    'next_due': due if retry else next_due(value, at),
                    'attempts': attempt if retry else 0,
                    'retry_at': (at + timedelta(minutes=5)).isoformat() if retry else None})
            completed.append(run)
    return completed
