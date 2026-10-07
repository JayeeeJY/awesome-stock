from datetime import datetime, timedelta, timezone
import pytest
from awesome_stock.storage import owner_schedule as s, owner_daily as daily
from awesome_stock.storage.owner import OwnerStore
from awesome_stock.storage.local import Conflict
from test_owner_business import funded, quote, uid
from test_owner_diagnosis import body
from test_owner_api import app, request, login


def setup_schedule(store, monkeypatch):
    now=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    monkeypatch.setattr(s,'clock',lambda:now)
    conf={'enabled':True,'timezone':'UTC','time':'01:00','weekdays':list(range(7)),'input':body()}
    return now,s.save(store,{'operation_id':uid(),'revision':0,'config':conf})


def test_persistent_schedule_once_and_disabled(funded,monkeypatch):
    quote(funded);now,config=setup_schedule(funded,monkeypatch)
    due=datetime.fromisoformat(config['next_due'])
    assert s.tick(funded,now)==[]
    run=s.tick(funded,due)[0];assert run['status']=='completed'
    restarted=OwnerStore(funded.directory)
    assert s.tick(restarted,due)==[]
    assert len(daily.history(restarted,'account-test')['records'])==3
    state=s.status(restarted,'account-test')['schedule']
    s.save(restarted,{'operation_id':uid(),'revision':state['revision'],'config':{**state['config'],'enabled':False}})
    assert s.tick(restarted,due+timedelta(days=1))==[]


def test_failure_retry_limit_and_recovery(funded,monkeypatch):
    quote(funded);_,config=setup_schedule(funded,monkeypatch);due=datetime.fromisoformat(config['next_due'])
    real=daily.capture
    with monkeypatch.context() as m:
        m.setattr(daily,'capture',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('DO NOT STORE THIS')))
        for minutes in [0,5,10]:
            assert s.tick(funded,due+timedelta(minutes=minutes))[0]['status']=='failed'
        assert s.tick(funded,due+timedelta(minutes=15))==[]
    state=s.status(funded,'account-test')
    assert len(state['runs'])==3 and 'DO NOT STORE' not in str(state)
    assert not daily.history(funded,'account-test')['records']
    assert s.tick(funded,datetime.fromisoformat(state['schedule']['next_due']))[0]['status']=='completed'


def test_missed_run_not_fabricated_and_revision_fenced(funded,monkeypatch):
    quote(funded);_,config=setup_schedule(funded,monkeypatch);due=datetime.fromisoformat(config['next_due'])
    assert s.tick(funded,due+timedelta(days=3))[0]['status']=='missed'
    assert not daily.history(funded,'account-test')['records']
    with pytest.raises(Conflict):s.save(funded,{'operation_id':uid(),'revision':config['revision'],'config':config['config']})


def test_dst_and_invalid_configuration():
    conf={'timezone':'America/New_York','time':'02:30','weekdays':list(range(7))}
    assert s.next_due(conf,datetime(2026,3,8,0,tzinfo=timezone.utc))=='2026-03-09T06:30:00+00:00'
    conf['time']='01:30'
    assert s.next_due(conf,datetime(2026,11,1,5,31,tzinfo=timezone.utc))=='2026-11-02T06:30:00+00:00'
    for key,value in [('enabled',1),('weekdays',[True]),('timezone','Fake/Zone'),('time','24:00')]:
        with pytest.raises(ValueError):s.config({'enabled':True,'timezone':'UTC','time':'01:00','weekdays':[0],'input':body(),key:value})


def test_api_schedule_auth(funded,app):
    quote(funded);data={'operation_id':uid(),'revision':0,'config':{'enabled':True,'timezone':'UTC','time':'01:00','weekdays':[0,1,2,3,4],'input':body()}}
    assert request(app,'/api/v1/owner/daily-schedule','POST',data)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/daily-schedule','POST',data,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/daily-schedule','POST',data,**auth)['status']==200
    assert request(app,'/api/v1/owner/daily-schedule-status','POST',{'account_id':'account-test'},**auth)['body']['schedule']['config']['enabled'] is True


def test_server_poll_survives_failure_and_throttles(monkeypatch):
    from awesome_stock.runtime import owner_scheduler as runtime
    from types import SimpleNamespace
    calls=[]
    server=SimpleNamespace(get_app=lambda:SimpleNamespace(store='synthetic'))
    monkeypatch.setattr(runtime.time,'monotonic',lambda:100)
    def failing(store):
        calls.append(store)
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(runtime.owner_schedule,'tick',failing)
    runtime.ScheduledOwnerServer.service_actions(server)
    runtime.ScheduledOwnerServer.service_actions(server)
    assert calls==['synthetic']
    monkeypatch.setattr(runtime.time,'monotonic',lambda:131)
    monkeypatch.setattr(runtime.owner_schedule,'tick',lambda store:calls.append(store))
    runtime.ScheduledOwnerServer.service_actions(server)
    assert calls==['synthetic','synthetic']


def test_retry_after_partial_write_rolls_back(funded,monkeypatch):
    quote(funded);_,config=setup_schedule(funded,monkeypatch);due=datetime.fromisoformat(config['next_due'])
    real=daily.capture
    def fail_after_write(*args,**kwargs):
        real(*args,**kwargs)
        raise RuntimeError('synthetic after-write failure')
    with monkeypatch.context() as m:
        m.setattr(daily,'capture',fail_after_write)
        assert s.tick(funded,due)[0]['status']=='failed'
    assert not daily.history(funded,'account-test')['records']
    assert s.tick(funded,due+timedelta(minutes=5))[0]['status']=='completed'
    assert len(daily.history(funded,'account-test')['records'])==3


def test_actual_server_loop_executes_due_schedule(funded,monkeypatch):
    from threading import Thread, Event
    from wsgiref.simple_server import make_server
    from awesome_stock.runtime.owner_scheduler import ScheduledOwnerServer
    quote(funded);_,config=setup_schedule(funded,monkeypatch)
    monkeypatch.setattr(s,'clock',lambda:datetime.fromisoformat(config['next_due']))
    done=Event();real=s.tick
    def checked(store):
        result=real(store)
        if result:done.set()
        return result
    monkeypatch.setattr(s,'tick',checked)
    def application(environ,start_response):
        start_response('200 OK',[]);return [b'ok']
    application.store=funded
    with make_server('127.0.0.1',0,application,server_class=ScheduledOwnerServer) as server:
        worker=Thread(target=server.serve_forever,kwargs={'poll_interval':0.05})
        worker.start()
        try:assert done.wait(5)
        finally:server.shutdown();worker.join(5)
    assert len(daily.history(funded,'account-test')['records'])==3


def test_disable_remains_available_when_diagnostic_inputs_are_obsolete(funded,monkeypatch):
    quote(funded);_,saved=setup_schedule(funded,monkeypatch)
    monkeypatch.setattr(s.diagnosis,'calculate',lambda *a:(_ for _ in ()).throw(ValueError('obsolete holding context')))
    disabled=s.save(funded,{'operation_id':uid(),'revision':saved['revision'],'config':{**saved['config'],'enabled':False}})
    assert disabled['next_due'] is None and disabled['config']['enabled'] is False
    changed={**disabled['config'],'input':{**body(),'holding_context':{}}}
    with pytest.raises(ValueError):s.save(funded,{'operation_id':uid(),'revision':disabled['revision'],'config':changed})
