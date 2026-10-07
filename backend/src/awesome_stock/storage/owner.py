"""Owner-only manual long-position ledger. Decimal strings, atomic recalculation."""
from collections import defaultdict
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import uuid
from awesome_stock.core.ledger import Trade, calculate_position
from awesome_stock.security.auth import UserRecord, PasswordCredential, make_password_credential
from .local import LocalStore, Conflict, _canonical, _private_directory, restore

OWNER_APP_ID = 0x41534F31
CURRENCIES = {'USD','HKD','CNY','EUR','GBP','JPY'}

class AccountHasHistory(ValueError):
    pass

class LedgerInvalid(ValueError):
    pass


def text(value, limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or '\x00' in value:
        raise ValueError('invalid text')
    return value.strip()


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,64}',value):
        raise ValueError('invalid identifier')
    return value


def number(value, *, positive=False):
    if not isinstance(value,str) or not re.fullmatch(r'(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?',value):
        raise ValueError('decimal string expected')
    if positive and Decimal(value)<=0:raise ValueError('must be positive')
    return format(Decimal(value),'f')


def credential(password):
    if not isinstance(password,str) or not 12<=len(password)<=128:
        raise ValueError('password length must be 12 to 128')
    return make_password_credential(password,salt=secrets.token_bytes(16))


def check_owner(db, version=5):
    if db.execute('PRAGMA application_id').fetchone()[0]!=OWNER_APP_ID or db.execute('PRAGMA user_version').fetchone()[0]!=version:
        raise ValueError('unsupported owner database')
    if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('database corrupt')
    if db.execute("SELECT value FROM metadata WHERE key='mode'").fetchone()!=('owner_local',):raise ValueError('wrong mode')
    for sql in ['SELECT slot,user_id,username,credential FROM owner LIMIT 0','SELECT id,name,currency,opening_cash FROM accounts LIMIT 0','SELECT sequence,id,account_id,payload,revision FROM trades LIMIT 0','SELECT id,fingerprint,result FROM operations LIMIT 0','SELECT sequence,action,entity_id,before_value,after_value FROM audit LIMIT 0']:
        db.execute(sql)

    if version>=2:
        for sql in ['SELECT id,payload,revision FROM documents LIMIT 0','SELECT id,revision,payload FROM document_versions LIMIT 0','SELECT trade_id,decision_id,decision_revision,revision FROM trade_links LIMIT 0']:
            db.execute(sql)

    if version>=3:
        for sql in ['SELECT id,account_id,payload,revision FROM cash_flows LIMIT 0','SELECT id,revision,payload FROM cash_flow_versions LIMIT 0','SELECT sequence,kind,entity_id FROM ledger_events LIMIT 0']:
            db.execute(sql)

    if version>=4:
        db.execute('SELECT cost_method FROM accounts LIMIT 0')
        if db.execute("SELECT 1 FROM accounts WHERE cost_method NOT IN ('avg','fifo') OR cost_method IS NULL").fetchone():raise ValueError('invalid account cost method')
    if version>=5:
        db.execute('SELECT broker,revision FROM accounts LIMIT 0')

def add_cash_tables(db):
    db.execute('CREATE TABLE cash_flows(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,payload TEXT NOT NULL,revision INTEGER NOT NULL)')
    db.execute('CREATE TABLE cash_flow_versions(id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,revision))')
    db.execute("CREATE TABLE ledger_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL CHECK(kind IN ('trade','cash')),entity_id TEXT NOT NULL,UNIQUE(kind,entity_id))")
    # Preserve existing trade ordering when introducing cash events.
    for (id,) in db.execute('SELECT id FROM trades ORDER BY sequence').fetchall():
        db.execute("INSERT INTO ledger_events(kind,entity_id) VALUES ('trade',?)",(id,))


def add_research_tables(db):
    db.execute('CREATE TABLE documents(id TEXT PRIMARY KEY,payload TEXT NOT NULL,revision INTEGER NOT NULL)')
    db.execute('CREATE TABLE document_versions(id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,revision))')
    db.execute('CREATE TABLE trade_links(trade_id TEXT PRIMARY KEY,decision_id TEXT,decision_revision INTEGER,revision INTEGER NOT NULL)')



def trade_payload(body):
    identifier(body['account_id']);symbol=text(body['symbol'],24).upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.^_-]{0,23}',symbol):raise ValueError('invalid symbol')
    if body['side'] not in ('buy','sell'):raise ValueError('invalid side')
    when=datetime.fromisoformat(text(body['executed_at'],40).replace('Z','+00:00'))
    if when.utcoffset() is None or not 1900<=when.year<=2200:raise ValueError('timezone required')
    payload={'id':body['id'],'account_id':body['account_id'],'symbol':symbol,'side':body['side'],'quantity':number(body['quantity'],positive=True),'price':number(body['price'],positive=True),'fee':number(body['fee']),'executed_at':when.astimezone(timezone.utc).isoformat(timespec='microseconds')}
    return payload

class OwnerStore(LocalStore):
    validate=staticmethod(check_owner)
    storage_mode='owner_local'
    schema_version=5

    def __init__(self,directory):
        self.directory=_private_directory(directory);self.path=self.directory/'owner.sqlite3'
        if self.path.is_symlink():raise ValueError('symlink database')
        if self.path.exists():
            if self.path.stat().st_mode&0o077:raise ValueError('database permissions must be 0600')
            with self.connection() as db:
                version=db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (1,2,3,4,5):raise ValueError('unsupported owner version')
                check_owner(db,version)
            if version<5:self._upgrade_schema()
            return
        temporary=self.directory/('.owner-init-'+uuid.uuid4().hex)
        fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        db=sqlite3.connect(temporary)
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute(f'PRAGMA application_id={OWNER_APP_ID}');db.execute('PRAGMA user_version=5')
                for sql in ['CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
                            'CREATE TABLE owner(slot INTEGER PRIMARY KEY CHECK(slot=1),user_id TEXT NOT NULL,username TEXT NOT NULL,credential TEXT NOT NULL)',
                            "CREATE TABLE accounts(id TEXT PRIMARY KEY,name TEXT NOT NULL,currency TEXT NOT NULL,opening_cash TEXT NOT NULL,cost_method TEXT NOT NULL DEFAULT 'avg' CHECK(cost_method IN ('avg','fifo')),broker TEXT NOT NULL DEFAULT '',revision INTEGER NOT NULL DEFAULT 1)",
                            'CREATE TABLE trades(sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,account_id TEXT NOT NULL,payload TEXT NOT NULL,revision INTEGER NOT NULL)',
                            'CREATE TABLE operations(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,result TEXT NOT NULL)',
                            'CREATE TABLE audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT,action TEXT NOT NULL,entity_id TEXT NOT NULL,before_value TEXT,after_value TEXT,created_at TEXT NOT NULL)']:
                    db.execute(sql)
                db.execute('INSERT INTO metadata VALUES (?,?)',('mode','owner_local'))
                add_research_tables(db)
                add_cash_tables(db)
            db.close();os.link(temporary,self.path)
        finally:
            db.close();temporary.unlink(missing_ok=True)

    def _upgrade_schema(self):
        with self.transaction() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version==5:return
            check_owner(db,version)
            legacy=object.__new__(LocalStore)
            legacy.directory=self.directory;legacy.path=self.path
            legacy.storage_mode='owner_local';legacy.schema_version=version
            legacy.validate=lambda connection:check_owner(connection,version)
            backup=legacy.backup()
            if version==1:add_research_tables(db)
            if version<3:add_cash_tables(db)
            if version<4:db.execute("ALTER TABLE accounts ADD COLUMN cost_method TEXT NOT NULL DEFAULT 'avg' CHECK(cost_method IN ('avg','fifo'))")
            db.execute("ALTER TABLE accounts ADD COLUMN broker TEXT NOT NULL DEFAULT ''")
            db.execute('ALTER TABLE accounts ADD COLUMN revision INTEGER NOT NULL DEFAULT 1')
            db.execute('PRAGMA user_version=5')
            self._audit(db,'schema_upgraded','owner-schema',{'version':version},{'version':5,'backup':backup['name']})
            check_owner(db)

    def owner(self):
        with self.connection() as db:row=db.execute('SELECT user_id,username,credential FROM owner WHERE slot=1').fetchone()
        return None if row is None else UserRecord(row[0],row[1],PasswordCredential(**json.loads(row[2])))

    def setup(self,username,password):
        username=text(username,80).casefold()
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.@+-]{2,79}',username):raise ValueError('invalid username')
        cred=credential(password)
        with self.transaction() as db:
            if db.execute('SELECT 1 FROM owner').fetchone():raise Conflict('owner already initialized')
            db.execute('INSERT INTO owner VALUES (1,?,?,?)',('local-owner',username,_canonical(cred.__dict__)))
            self._audit(db,'owner_initialized','local-owner',None,{'username':username})

    def change_password(self,password,expected_digest):
        cred=credential(password)
        with self.transaction() as db:
            current=json.loads(db.execute('SELECT credential FROM owner WHERE slot=1').fetchone()[0])
            if current['digest_hex']!=expected_digest:raise Conflict('credential changed')
            db.execute('UPDATE owner SET credential=? WHERE slot=1',(_canonical(cred.__dict__),))
            self._audit(db,'password_changed','local-owner',None,None)

    def _audit(self,db,action,entity,before,after):
        db.execute('INSERT INTO audit(action,entity_id,before_value,after_value,created_at) VALUES (?,?,?,?,?)',(action,entity,None if before is None else _canonical(before),None if after is None else _canonical(after),datetime.now(timezone.utc).isoformat()))

    def _operation(self,db,body,action):
        identifier(body['operation_id'])
        fp=hashlib.sha256(_canonical({'action':action,'body':body}).encode()).hexdigest()
        old=db.execute('SELECT fingerprint,result FROM operations WHERE id=?',(body['operation_id'],)).fetchone()
        if old:
            if old[0]!=fp:raise Conflict('operation reused')
            return fp,json.loads(old[1])
        return fp,None

    def _result(self,db,body,fp,result):
        db.execute('INSERT INTO operations VALUES (?,?,?)',(body['operation_id'],fp,_canonical(result)))
        return result

    def add_account(self,body):
        required={'id','operation_id','name','currency','opening_cash'}
        if not isinstance(body,dict) or not required<=set(body) or set(body)-required-{'cost_method','broker'}:raise ValueError('invalid fields')
        broker=body.get('broker','')
        if not isinstance(broker,str) or len(broker)>80 or '\x00' in broker:raise ValueError('invalid broker')
        identifier(body['id']);name=text(body['name'],80);cash=number(body['opening_cash'])
        method=body.get('cost_method','avg')
        if not isinstance(method,str) or method not in ('avg','fifo'):raise ValueError('invalid cost method')
        if not isinstance(body['currency'],str) or body['currency'] not in CURRENCIES:raise ValueError('currency unsupported')
        with self.transaction() as db:
            fp,old=self._operation(db,body,'account_create')
            if old is not None:return old
            if db.execute('SELECT 1 FROM accounts WHERE id=?',(body['id'],)).fetchone():raise Conflict('account exists')
            if db.execute("SELECT 1 FROM audit WHERE entity_id=? AND action='account_deleted'",(body['id'],)).fetchone():raise Conflict('deleted account ID cannot be reused')
            account={'id':body['id'],'name':name,'currency':body['currency'],'opening_cash':cash,'cost_method':method,'broker':broker.strip(),'revision':1}
            db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?,?)',tuple(account.values()))
            self._audit(db,'account_created',body['id'],None,account)
            return self._result(db,body,fp,account)

    def edit_account(self,body):
        if not isinstance(body,dict) or set(body)!={'id','operation_id','revision','name','broker'}:raise ValueError('invalid fields')
        identifier(body['id']);revision=self._revision(body['revision']);name=text(body['name'],80)
        broker=body['broker']
        if not isinstance(broker,str) or len(broker)>80 or '\x00' in broker:raise ValueError('invalid broker')
        with self.transaction() as db:
            fp,old=self._operation(db,body,'account_edit')
            if old is not None:return old
            row=db.execute('SELECT name,broker,revision FROM accounts WHERE id=?',(body['id'],)).fetchone()
            if row is None or row[2]!=revision:raise Conflict('account version changed')
            result={'id':body['id'],'name':name,'broker':broker.strip(),'revision':revision+1}
            db.execute('UPDATE accounts SET name=?,broker=?,revision=? WHERE id=?',(name,broker.strip(),revision+1,body['id']))
            self._audit(db,'account_edited',body['id'],dict(zip(('name','broker','revision'),row)),result)
            return self._result(db,body,fp,result)

    def delete_account(self,body):
        if not isinstance(body,dict) or set(body)!={'id','revision','operation_id'}:raise ValueError('invalid fields')
        identifier(body['id']);revision=self._revision(body['revision'])
        def refers(value):
            if isinstance(value,dict):return any(refers(v) for v in value.values())
            if isinstance(value,list):return any(refers(v) for v in value)
            return value==body['id']
        with self.transaction() as db:
            fp,old=self._operation(db,body,'account_delete')
            if old is not None:return old
            row=db.execute('SELECT revision FROM accounts WHERE id=?',(body['id'],)).fetchone()
            if row is None or row[0]!=revision:raise Conflict('account version changed')
            account=self._account_projection(db,body['id'])
            if Decimal(account['opening_cash'])!=0 or Decimal(account['cash'])!=0 or account['trades'] or account['cash_flows']:raise AccountHasHistory('account has financial records')
            # Retain even deleted trade/cash history and immutable research/planning snapshots.
            for before,after in db.execute("SELECT before_value,after_value FROM audit WHERE action NOT IN ('account_created','account_edited')"):
                if any(raw and refers(json.loads(raw)) for raw in (before,after)):raise AccountHasHistory('account has historical references')
            for (raw,) in db.execute('SELECT payload FROM document_versions'):
                if refers(json.loads(raw)):raise AccountHasHistory('account has historical references')
            db.execute('DELETE FROM accounts WHERE id=?',(body['id'],))
            result={'id':body['id'],'deleted':True}
            self._audit(db,'account_deleted',body['id'],account,result)
            return self._result(db,body,fp,result)

    def trade(self,body,*,delete=False,_db=None):
        common={'id','operation_id','revision'}
        if not isinstance(body,dict) or set(body)!=(common if delete else common|{'account_id','symbol','side','quantity','price','fee','executed_at'}):raise ValueError('invalid fields')
        identifier(body['id'])
        if type(body['revision']) is not int or not 0<=body['revision']<2**31:raise ValueError('invalid revision')
        payload=None
        if not delete:
            payload=trade_payload(body)
        with (self.transaction() if _db is None else nullcontext(_db)) as db:
            fp,old=self._operation(db,body,'trade_delete' if delete else 'trade_save')
            if old is not None:return old
            current=db.execute('SELECT payload,revision,account_id FROM trades WHERE id=?',(body['id'],)).fetchone()
            if (current[1] if current else 0)!=body['revision'] or (delete and not current):raise Conflict('trade version changed')
            if current is None and not delete and db.execute("SELECT 1 FROM audit WHERE entity_id=? AND action IN ('trade_saved','trade_deleted')",(body['id'],)).fetchone():raise Conflict('deleted trade ID cannot be reused')
            if current and not delete and current[2]!=body['account_id']:raise ValueError('account cannot change')
            if not delete:
                link=db.execute('SELECT decision_id,decision_revision FROM trade_links WHERE trade_id=?',(body['id'],)).fetchone()
                if link and link[0]:
                    decision=self._document_version(db,link[0],link[1])
                    if decision['symbol']!=payload['symbol']:raise ValueError('unlink decision before changing symbol')
            if delete:
                link=db.execute('SELECT decision_id,decision_revision,revision FROM trade_links WHERE trade_id=?',(body['id'],)).fetchone()
                if link:
                    self._audit(db,'trade_reference_removed',body['id'],{'link':list(link)},None)
                    db.execute('DELETE FROM trade_links WHERE trade_id=?',(body['id'],))
                db.execute('DELETE FROM trades WHERE id=?',(body['id'],));account_id=current[2];result={'id':body['id'],'deleted':True}
            else:
                if not db.execute('SELECT 1 FROM accounts WHERE id=?',(body['account_id'],)).fetchone():raise ValueError('unknown account')
                db.execute('INSERT INTO trades(id,account_id,payload,revision) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],body['account_id'],_canonical(payload),body['revision']+1))
                account_id=body['account_id'];result={**payload,'revision':body['revision']+1}
            if not delete and current is None:
                db.execute("INSERT INTO ledger_events(kind,entity_id) VALUES ('trade',?)",(body['id'],))
            # Recompute every subsequent transaction before commit; failure rolls back.
            self._account_projection(db,account_id)
            self._audit(db,'trade_deleted' if delete else 'trade_saved',body['id'],json.loads(current[0]) if current else None,result)
            return self._result(db,body,fp,result)

    def _account_projection(self,db,account_id,additional=()):
        row=db.execute('SELECT id,name,currency,opening_cash,cost_method,broker,revision FROM accounts WHERE id=?',(account_id,)).fetchone()
        account=dict(zip(('id','name','currency','opening_cash','cost_method','broker','revision'),row))
        raw=db.execute("SELECT t.sequence,t.payload,t.revision,e.sequence FROM trades t LEFT JOIN ledger_events e ON e.kind='trade' AND e.entity_id=t.id WHERE t.account_id=?",(account_id,)).fetchall()
        if any(row[3] is None for row in raw):raise LedgerInvalid('missing trade order')
        trades=[{**json.loads(p),'sequence':seq,'revision':rev,'event_order':order} for seq,p,rev,order in raw]
        trades.extend(additional)
        trades.sort(key=lambda t:(t['executed_at'],t['event_order']))
        cash_flows=[json.loads(row[0]) for row in db.execute('SELECT payload FROM cash_flows WHERE account_id=?',(account_id,))]
        cash_flows.sort(key=lambda f:(f['occurred_at'],f['event_order']))
        events=[(t['executed_at'],t['event_order'],'trade',t) for t in trades]+[(f['occurred_at'],f['event_order'],'cash',f) for f in cash_flows]
        events.sort(key=lambda event:(event[0],event[1]))
        with localcontext() as ctx:
            ctx.prec=60
            cash=Decimal(account['opening_cash']);groups=defaultdict(list);quantities=defaultdict(lambda:Decimal(0))
            deposits=Decimal(0);withdrawals=Decimal(0);trade_cash=Decimal(0)
            for _,_,kind,t in events:
                if kind=='cash':
                    amount=Decimal(t['amount'])
                    if t['direction']=='deposit':cash+=amount;deposits+=amount
                    else:cash-=amount;withdrawals+=amount
                    if cash<0:raise LedgerInvalid('cash overdraft in chronological ledger')
                    continue
                previous_cash=cash
                item=Trade(t['side'],t['quantity'],t['price'],t['fee']);symbol=t['symbol']
                gross=item.quantity*item.price
                if t['side']=='buy':cash-=gross+item.fee;quantities[symbol]+=item.quantity
                else:
                    quantities[symbol]-=item.quantity;cash+=gross-item.fee
                if cash<0 or quantities[symbol]<0:raise LedgerInvalid('cash overdraft or oversell in chronological ledger')
                trade_cash+=cash-previous_cash
                groups[symbol].append(item)
            holdings=[]
            for symbol,items in sorted(groups.items()):
                f=calculate_position(items,quote=None,method=account['cost_method'],currency=account['currency'])
                holdings.append({'symbol':symbol,'quantity':format(f.shares,'f'),'open_cost':format(f.open_cost,'f'),'realized_pnl':format(f.realized,'f'),'market_value':None,'unrealized_pnl':None})
            return {**account,'cash':format(cash,'f'),'holdings':holdings,'trades':trades,'cash_flows':cash_flows,'deposits':format(deposits,'f'),'withdrawals':format(withdrawals,'f'),'cash_flow_net':format(deposits-withdrawals,'f'),'trade_cash_change':format(trade_cash,'f'),'valuation_status':'missing_quotes'}

    def ledger(self):
        with self.connection() as db:
            db.execute('BEGIN')
            ids=[row[0] for row in db.execute('SELECT id FROM accounts ORDER BY name,id')]
            return {'accounts':[self._account_projection(db,id) for id in ids],'valuation_status':'missing_quotes','cross_currency_total':None,'cost_method':'per_account','manual_records_only':True}

    @staticmethod
    def _revision(value):
        if type(value) is not int or not 0<=value<2**31:raise ValueError('invalid revision')
        return value

    @staticmethod
    def _document_version(db,id,revision):
        identifier(id);OwnerStore._revision(revision)
        row=db.execute('SELECT payload FROM document_versions WHERE id=? AND revision=?',(id,revision)).fetchone()
        if not row:raise ValueError('unknown document version')
        return json.loads(row[0])

    def documents(self):
        with self.connection() as db:
            db.execute('BEGIN')
            documents=[json.loads(row[0]) for row in db.execute('SELECT payload FROM documents ORDER BY id')]
            versions=[json.loads(row[0]) for row in db.execute('SELECT payload FROM document_versions ORDER BY id,revision')]
            links=[dict(zip(('trade_id','decision_id','decision_revision','revision'),row)) for row in db.execute('SELECT trade_id,decision_id,decision_revision,revision FROM trade_links ORDER BY trade_id')]
            trades=[{**json.loads(row[0]),'revision':row[1]} for row in db.execute('SELECT payload,revision FROM trades ORDER BY sequence')]
            return {'documents':[d for d in documents if d['kind'] in ('note','decision')],'versions':[d for d in versions if d['kind'] in ('note','decision')],'links':links,'trades':trades,'manual_only':True}

    def save_document(self,body,*,archive=False):
        common={'id','revision','operation_id'}
        fields={'kind','title','symbol','content','support','counter_case','invalidation','risk_limit','review_on','research_ref'}
        if not isinstance(body,dict) or set(body)!=(common if archive else common|fields):raise ValueError('invalid document fields')
        identifier(body['id']);self._revision(body['revision'])
        if not archive:
            if body['kind'] not in ('note','decision'):raise ValueError('invalid kind')
            symbol=text(body['symbol'],24).upper()
            if not re.fullmatch(r'[A-Z0-9][A-Z0-9.^_-]{0,23}',symbol):raise ValueError('invalid symbol')
            payload={'id':body['id'],'kind':body['kind'],'title':text(body['title'],120),'symbol':symbol,'content':text(body['content'],20000)}
            for key in ['support','counter_case','invalidation','risk_limit','review_on']:
                value=body[key]
                if not isinstance(value,str) or len(value)>4000 or '\x00' in value:raise ValueError('invalid text')
                if body['kind']=='note' and value:raise ValueError('note has decision fields')
                payload[key]=text(value,4000) if body['kind']=='decision' else ''
            if body['kind']=='decision':
                from datetime import date
                date.fromisoformat(payload['review_on'])
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',payload['review_on']):raise ValueError('invalid review date')
            if body['kind']=='note' and body['research_ref'] is not None:raise ValueError('note cannot reference note')
            payload['research_ref']=body['research_ref']
        with self.transaction() as db:
            fp,old=self._operation(db,body,'document_archive' if archive else 'document_save')
            if old is not None:return old
            row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['id'],)).fetchone()
            current=json.loads(row[0]) if row else None
            if (row[1] if row else 0)!=body['revision'] or (archive and not row):raise Conflict('document version changed')
            if current and current['kind'] not in ('note','decision'):raise ValueError('use matching document endpoint')
            if current and current['archived']:raise Conflict('document archived')
            if archive:payload={**current,'archived':True}
            else:
                if current and current['kind']!=payload['kind']:raise ValueError('kind cannot change')
                ref=payload['research_ref']
                if ref is not None:
                    if not isinstance(ref,dict) or set(ref)!={'id','revision'}:raise ValueError('invalid reference')
                    note=self._document_version(db,ref['id'],ref['revision'])
                    active=json.loads(db.execute('SELECT payload FROM documents WHERE id=?',(ref['id'],)).fetchone()[0])
                    unchanged=current and current['research_ref']==ref
                    if note['kind']!='note' or note['archived'] or note['symbol']!=payload['symbol'] or (active['archived'] and not unchanged):raise ValueError('invalid research reference')
                payload['archived']=False
            result={**payload,'revision':body['revision']+1,'updated_at':datetime.now(timezone.utc).isoformat()}
            encoded=_canonical(result)
            db.execute('INSERT INTO documents VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],encoded,result['revision']))
            db.execute('INSERT INTO document_versions VALUES (?,?,?)',(body['id'],result['revision'],encoded))
            self._audit(db,'document_archived' if archive else 'document_saved',body['id'],current,result)
            return self._result(db,body,fp,result)

    def link_trade(self,body):
        if not isinstance(body,dict) or set(body)!={'trade_id','trade_revision','revision','operation_id','decision_id','decision_revision'}:raise ValueError('invalid link fields')
        identifier(body['trade_id']);self._revision(body['revision']);self._revision(body['trade_revision'])
        if body['decision_id'] is None:
            if body['decision_revision'] is not None:raise ValueError('invalid empty reference')
        else:identifier(body['decision_id']);self._revision(body['decision_revision'])
        with self.transaction() as db:
            fp,old=self._operation(db,body,'trade_reference')
            if old is not None:return old
            trade=db.execute('SELECT payload,revision FROM trades WHERE id=?',(body['trade_id'],)).fetchone()
            if not trade or trade[1]!=body['trade_revision']:raise Conflict('trade changed')
            oldlink=db.execute('SELECT revision FROM trade_links WHERE trade_id=?',(body['trade_id'],)).fetchone()
            if (oldlink[0] if oldlink else 0)!=body['revision']:raise Conflict('link changed')
            if body['decision_id'] is not None:
                decision=self._document_version(db,body['decision_id'],body['decision_revision'])
                active=json.loads(db.execute('SELECT payload FROM documents WHERE id=?',(body['decision_id'],)).fetchone()[0])
                if decision['kind']!='decision' or decision['archived'] or active['archived'] or decision['symbol']!=json.loads(trade[0])['symbol']:raise ValueError('invalid decision reference')
            previous=db.execute('SELECT decision_id,decision_revision,revision FROM trade_links WHERE trade_id=?',(body['trade_id'],)).fetchone()
            result={'trade_id':body['trade_id'],'decision_id':body['decision_id'],'decision_revision':body['decision_revision'],'revision':body['revision']+1}
            db.execute('INSERT INTO trade_links VALUES (?,?,?,?) ON CONFLICT(trade_id) DO UPDATE SET decision_id=excluded.decision_id,decision_revision=excluded.decision_revision,revision=excluded.revision',tuple(result.values()))
            self._audit(db,'trade_reference_saved',body['trade_id'],{'link':list(previous)} if previous else None,result)
            return self._result(db,body,fp,result)


def restore_owner(source,destination):
    manifest=json.loads((Path(source)/'manifest.json').read_text())
    version=manifest.get('schema_version')
    if type(version) is not int or version not in (1,2,3,4,5):raise ValueError('unsupported backup version')
    return restore(source,destination,validator=lambda db:check_owner(db,version),schema_version=version,mode='owner_local',filename='owner.sqlite3')
