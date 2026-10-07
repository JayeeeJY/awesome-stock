"""Explicit isolated native-source delivery acceptance."""
from datetime import datetime, timezone
import platform
import http.client
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from package_owner import build
PASSWORD='Synthetic-install-only-2026'

class Client:
    def __init__(self,port):self.port=port;self.cookie='';self.csrf=''
    def call(self,path,body=None,expected=200,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10)
        headers={'Content-Type':'application/json','Origin':origin or f'http://127.0.0.1:{self.port}','X-Requested-With':'awesome-owner','Cookie':self.cookie,'X-CSRF-Token':self.csrf}
        conn.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
        r=conn.getresponse();raw=r.read();assert r.status==expected,(path,r.status,raw)
        if path=='/api/v1/auth/login':
            cookies=[v.split(';')[0] for k,v in r.getheaders() if k.lower()=='set-cookie'];self.cookie='; '.join(cookies);self.csrf=next(x.split('=',1)[1] for x in cookies if x.startswith('__Host-awesome_owner_csrf='))
        conn.close();return json.loads(raw)
    def ready(self):
        for _ in range(150):
            try:self.call('/api/v1/health');return
            except (OSError,AssertionError):time.sleep(.1)
        raise AssertionError('server unavailable')
    def check_ui(self):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10)
        conn.request('GET','/login');response=conn.getresponse();html=response.read().decode()
        assert response.status==200 and '<div id="app"></div>' in html
        assert "script-src 'self'" in response.getheader('Content-Security-Policy','')
        asset=re.search(r'src="(/assets/[^" ]+\.js)"',html);assert asset,html
        conn.request('GET',asset.group(1));response=conn.getresponse()
        assert response.status==200 and response.read()
        conn.close()
    def login(self):self.call('/api/v1/auth/login',dict(username='installer',password=PASSWORD))
    def seed(self):
        self.ready();self.check_ui();self.call('/api/v1/owner/ledger',expected=401)
        self.call('/api/v1/owner/setup',dict(username='installer',password=PASSWORD));self.login()
        self.call('/api/v1/owner/accounts',dict(id='qa-account',operation_id=str(uuid.uuid4()),name='Synthetic install',currency='USD',opening_cash='1000'))
        self.call('/api/v1/owner/trades',dict(id='qa-trade',operation_id=str(uuid.uuid4()),revision=0,account_id='qa-account',symbol='TEST',side='buy',quantity='2',price='10',fee='1',executed_at='2026-01-01T00:00:00Z'))
        self.call('/api/v1/owner/backup',{},expected=403,origin='https://invalid.example')
        self.seed_business()
        self.business_state=self.read_business()
        backup=self.call('/api/v1/owner/backup',{})
        ledger=self.call('/api/v1/owner/ledger');assert ledger['accounts'][0]['cash']=='979'
        return ledger,backup
    def check(self,ledger):
        self.ready();self.check_ui();self.call('/api/v1/owner/ledger',expected=401);self.login();assert self.call('/api/v1/owner/ledger')==ledger
        assert not self.call('/api/v1/owner/connections')['ai']['enabled']
        assert self.read_business()==self.business_state

    def seed_business(self):
        uid=lambda:str(uuid.uuid4())
        today=datetime.now(timezone.utc).date().isoformat()
        policy={'warning_percent':'20','max_percent':'30','shock_percent':'10','custom_rules':[]}
        self.call('/api/v1/owner/constitution',{'operation_id':uid(),'revision':0,'config':{'policy':policy,'require_reason_before_trade':True,'prohibited_actions':['Synthetic install restriction']}})
        self.call('/api/v1/owner/trade-context',{'operation_id':uid(),'trade_id':'qa-trade','trade_revision':1,'revision':0,'decision_required':True,'reason':'Synthetic install reason'})
        self.call('/api/v1/owner/business',{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'TEST','currency':'USD','price':'20','as_of':today,'source':'Synthetic install quote'}})
        diagnostic={'account_id':'qa-account','constitution_revision':1,'policy':policy,'holding_context':{'TEST':{'company':'Synthetic company','news':'neutral','source':'Synthetic observation','as_of':today}}}
        draft=self.call('/api/v1/owner/diagnosis-preview',diagnostic)
        daily=self.call('/api/v1/owner/daily-capture',{'operation_id':uid(),'input':diagnostic,'expected_token':draft['token']})
        self.brief_id=daily['brief']['id']
        assert daily['brief']['facts']['score']=='75.60'
        self.call('/api/v1/owner/insight-feedback',{'operation_id':uid(),'target_id':self.brief_id,'target_symbol':'','revision':0,'rating':'useful','reason':'Synthetic install feedback','note':'','action_taken':False,'action_type':''})
        self.call('/api/v1/owner/daily-schedule',{'operation_id':uid(),'revision':0,'config':{'enabled':False,'timezone':'UTC','time':'16:30','weekdays':[0,1,2,3,4],'input':diagnostic}})
        inp={'trade_id':'qa-trade','history_complete':True,'constitution_revision':1}
        preview=self.call('/api/v1/owner/coach-preview',inp)
        report=self.call('/api/v1/owner/coach',{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']})
        assert report['report']['checks'][0]['process_score']==100
        self.call('/api/v1/owner/coach-review',{'operation_id':uid(),'report_id':report['id'],'revision':0,'title':'Synthetic install review','content':'Synthetic fixed journal','status':'journaled'})
        span={'start':'2026-01-01','end':'2026-01-01'}
        preview=self.call('/api/v1/owner/coach-period-preview',span)
        self.call('/api/v1/owner/coach-period',{'id':uid(),'operation_id':uid(),'input':span,'expected_token':preview['token']})

    def read_business(self):
        return {'constitution':self.call('/api/v1/owner/constitution'),
                'trade_context':self.call('/api/v1/owner/trade-context-history',{'trade_id':'qa-trade'}),
                'daily':self.call('/api/v1/owner/daily-history',{'account_id':'qa-account'}),
                'diagnosis':self.call('/api/v1/owner/diagnosis-history',{'account_id':'qa-account'}),
                'schedule':self.call('/api/v1/owner/daily-schedule-status',{'account_id':'qa-account'}),
                'feedback':self.call('/api/v1/owner/insight-feedback-history',{'target_id':self.brief_id,'target_symbol':''}),
                'coach':self.call('/api/v1/owner/coach'),'period':self.call('/api/v1/owner/coach-period'),
                'journal':self.call('/api/v1/owner/evolve')['coach_journal']}

def run(*args,**kwargs):return subprocess.run(*args,check=True,**kwargs)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def native():
    with tempfile.TemporaryDirectory(prefix='awesome-install-') as raw:
        temp=Path(raw).resolve();archive=temp/'owner.tar.gz';package=build(archive)
        repeated=temp/'owner-repeat.tar.gz';assert build(repeated)['sha256']==package['sha256']
        assert repeated.read_bytes()==archive.read_bytes()
        with tarfile.open(archive) as tar:tar.extractall(temp)
        root=temp/'awesome-stock-owner';p=port();client=Client(p);data=temp/'data';child=None
        def start(directory):return subprocess.Popen([sys.executable,str(root/'start_owner.py'),'--port',str(p),'--data-dir',str(directory)],cwd=temp,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':''})
        def stop():child.terminate();child.wait(timeout=10)
        try:
            child=start(data);ledger,_=client.seed();stop();child=start(data);client.check(ledger);stop()
            backup=next((data/'backups').glob('backup-*'));restored=temp/'restored'
            run([sys.executable,str(root/'start_owner.py'),'--restore-from',str(backup),'--data-dir',str(restored)],cwd=temp,stdout=subprocess.DEVNULL)
            child=start(restored);client.check(ledger)
        finally:
            if child and child.poll() is None:stop()
    return {'passed':True,'scope':'native isolated source archive install restart restore','platform':platform.system()+' '+platform.machine(),'python':platform.python_version(),'archive_sha256':package['sha256'],'archive_files':package['files'],'reproducible_archive':True,'restored':['ledger','diagnosis','daily','disabled_schedule','constitution','trade_context','feedback','coach','period','coach_journal'],'external_provider_calls':False,'public_release_approved':False}

if __name__=='__main__':
    import argparse
    argparse.ArgumentParser(description='Isolated native-source installation, restart and backup/restore acceptance.').parse_args()
    print(json.dumps([native()]))
