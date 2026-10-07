"""Single owner manual ledger server. No demo credentials or live brokerage access."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import sqlite3
from wsgiref.simple_server import make_server
from awesome_stock.api import CommunityApi, LegacyReadAdapter
from awesome_stock.api.contracts import ApiResponse, ApiProblem, PUBLIC_MESSAGES
from awesome_stock.api.cookies import ACCESS_COOKIE, validate_csrf
from awesome_stock.security.auth import authenticate, AuthenticationError
from awesome_stock.security.sessions import InMemorySessionRepository, SessionService, SessionError
from awesome_stock.security.rate_limit import LoginAttemptLimiter, RateLimitError
from awesome_stock.core.owner_views import project
from awesome_stock.storage.owner_plan import workspace as plan_workspace, save_plan, save_execution, record_trade
from awesome_stock.storage.owner_evolve import workspace as evolve_workspace, save_review
from awesome_stock.storage.owner_journal import workspace as journal_workspace, save as save_journal
from awesome_stock.storage.owner import OwnerStore, LedgerInvalid, AccountHasHistory, restore_owner
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner_transfer import preview as import_preview, commit as import_commit, export_data
from awesome_stock.storage.owner_cash import save as save_cash, history as cash_history
from .owner_info import academy, settings
from awesome_stock.storage import owner_business as business, owner_privacy as privacy, owner_diagnosis as diagnosis, owner_diagnosis_scope as diagnosis_scope, owner_diagnosis_sources as diagnosis_sources, owner_daily as daily, owner_schedule as schedule, owner_coach as coach, owner_coach_period as coach_period, owner_feedback as feedback, owner_constitution as constitution, owner_trade_context as trade_context, owner_research_reports as research_reports, owner_fx as fx
from .owner_scheduler import ScheduledOwnerServer
from awesome_stock.storage import owner_market_history as market_history, owner_research_technical as research_technical, owner_research_position as research_position, owner_news as news, owner_company as company, owner_research_memory as research_memory
from .owner_connections import Connections, ConnectionFailure
from .server import _cookies, _headers, _json_body, _response, _file_response, QuietRequestHandler


COOKIE_NAMES = {name: name.replace('awesome_', 'awesome_owner_') for name in ('__Host-awesome_access','__Host-awesome_refresh','__Host-awesome_csrf')}

def owner_cookies(env):
    original=_cookies(env)
    return {name: original.get(owner_name,'') for name,owner_name in COOKIE_NAMES.items()}

def respond(start,response):
    def renamed(status,headers):
        output=[]
        for key,value in headers:
            if key.lower()=='set-cookie':
                name,rest=value.split('=',1)
                value=COOKIE_NAMES.get(name,name)+'='+rest
            output.append((key,value))
        return start(status,output)
    return _response(renamed,response)


def error(status,code):
    return ApiResponse.failure(ApiProblem(status,code,PUBLIC_MESSAGES[code],status in {429,503},None))


def application(*,port,data_dir,ui_dist=None):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('invalid port')
    from .owner_ui import OwnerUI
    ui=OwnerUI(ui_dist) if ui_dist is not None else None
    store=OwnerStore(data_dir);connections=Connections();root=Path(__file__).resolve().parents[4]/'frontend'
    clock=lambda:datetime.now(timezone.utc)
    sessions=SessionService(InMemorySessionRepository(),clock=clock,token_factory=lambda:secrets.token_urlsafe(32),is_user_active=lambda uid:uid=='local-owner' and store.owner() is not None,access_lifetime=timedelta(minutes=15),refresh_lifetime=timedelta(hours=8))
    origins=frozenset({f'http://127.0.0.1:{port}',f'http://localhost:{port}'})
    def lookup(username):
        user=store.owner()
        return user if user and user.username==username else None
    api=CommunityApi(sessions=sessions,user_lookup=lookup,legacy=LegacyReadAdapter(lambda *_:()),clock=clock,csrf_factory=lambda:secrets.token_urlsafe(32),allowed_origins=origins)
    limiter=LoginAttemptLimiter(clock=clock,key_secret=secrets.token_bytes(32),max_failures=5)

    initial_owner=store.owner()
    def auth_epoch():
        with store.connection() as db:
            row=db.execute("SELECT value FROM metadata WHERE key='data_epoch'").fetchone()
        return row[0] if row else None
    credential_state=[(initial_owner.credential.digest_hex if initial_owner else None,auth_epoch())]

    def app(env,start):
        path=env.get('PATH_INFO','/');method=env.get('REQUEST_METHOD','GET').upper()
        try:
            if env.get('HTTP_HOST') not in {f'127.0.0.1:{port}',f'localhost:{port}'}:return respond(start,error(403,'csrf_rejected'))
            if env.get('HTTP_ORIGIN') and env['HTTP_ORIGIN'] not in origins:return respond(start,error(403,'csrf_rejected'))
            if env.get('HTTP_SEC_FETCH_SITE')=='cross-site':return respond(start,error(403,'csrf_rejected'))
            if ui is not None and method=='GET':
                result=ui.serve(path,env.get('QUERY_STRING',''),start)
                if result is not None:return result
            if ui is None and path in {'/','/ledger','/cockpit','/portfolio','/research','/decisions','/evolve','/plans','/cash','/academy','/settings','/login','/assets/owner.js','/assets/owner-research.js','/assets/owner-evolve.js','/assets/owner-plan.js','/assets/owner-info.js','/assets/owner-transfer.js','/assets/owner-cash.js','/assets/owner-business.js','/assets/owner-shell.js','/screening','/planning','/trends','/assets/owner.css'} and method=='GET':
                name={'/assets/owner-shell.js':'owner-shell.js','/assets/owner-business.js':'owner-business.js','/assets/owner-cash.js':'owner-cash.js','/assets/owner-transfer.js':'owner-transfer.js','/assets/owner-info.js':'owner-info.js','/assets/owner-plan.js':'owner-plan.js','/assets/owner-evolve.js':'owner-evolve.js','/assets/owner-research.js':'owner-research.js','/assets/owner.js':'owner.js','/assets/owner.css':'owner.css'}.get(path,'owner.html')
                return _file_response(start,root/name)
            if path=='/api/v1/health' and method=='GET':return respond(start,ApiResponse(200,data={'status':'ok','mode':'owner_local'}))
            if not path.startswith('/api/v1/owner/') and not path.startswith('/api/v1/auth/'):
                return respond(start,error(404,'capability_unsupported'))
            cookies=owner_cookies(env);headers=_headers(env)
            current_user=store.owner()
            current_digest=current_user.credential.digest_hex if current_user else None
            if (current_digest,auth_epoch())!=credential_state[0]:
                sessions.revoke_user('local-owner');connections.clear();credential_state[0]=(current_digest,auth_epoch())
            if path=='/api/v1/owner/status' and method=='GET':
                valid=False
                try:valid=sessions.validate_access(cookies.get(ACCESS_COOKIE,''))=='local-owner'
                except SessionError:pass
                return respond(start,ApiResponse(200,data={'initialized':store.owner() is not None,'authenticated':valid,'mode':'owner_local'}))
            if method not in {'GET','POST','DELETE'}:return respond(start,error(405,'capability_unsupported'))
            if method!='GET':
                if env.get('CONTENT_TYPE','').split(';')[0].strip()!='application/json' or env.get('HTTP_ORIGIN') not in origins:
                    return respond(start,error(403,'csrf_rejected'))
            if path=='/api/v1/owner/setup' and method=='POST':
                if env.get('HTTP_X_REQUESTED_WITH')!='awesome-owner':return respond(start,error(403,'csrf_rejected'))
                if store.owner() is not None:return respond(start,error(409,'owner_initialized'))
                body=_json_body(env)
                if set(body)!={'username','password'}:raise ValueError('invalid fields')
                store.setup(body['username'],body['password'])
                return respond(start,ApiResponse(200,data={'initialized':True}))
            if path=='/api/v1/auth/login' and method=='POST':
                if env.get('HTTP_X_REQUESTED_WITH')!='awesome-owner':return respond(start,error(403,'csrf_rejected'))
                body=_json_body(env)
                if set(body)!={'username','password'} or not isinstance(body['username'],str) or not isinstance(body['password'],str) or len(body['username'])>80 or len(body['password'])>128:raise ValueError('invalid credentials shape')
                limiter.check('owner-login')
                response=api.login(username=body['username'],password=body['password'])
                if response.problem is not None:limiter.record_failure('owner-login')
                else:limiter.record_success('owner-login')
                return respond(start,response)
            if path=='/api/v1/auth/refresh' and method=='POST':
                return respond(start,api.refresh(method=method,headers=headers,cookies=cookies))
            # All remaining data/backup/password actions require the sole local owner.
            if sessions.validate_access(cookies.get(ACCESS_COOKIE,''))!='local-owner':return respond(start,error(403,'access_denied'))
            if method!='GET':validate_csrf(method=method,headers=headers,cookies=cookies,allowed_origins=origins)
            if path=='/api/v1/auth/logout' and method=='POST':
                connections.clear()
                return respond(start,api.logout(method=method,headers=headers,cookies=cookies))
            if path=='/api/v1/owner/password' and method=='POST':
                body=_json_body(env)
                if set(body)!={'current_password','new_password'} or not isinstance(body['current_password'],str) or len(body['current_password'])>128:raise ValueError('invalid fields')
                limiter.check('owner-password');user=store.owner()
                try:authenticate(user,body['current_password'])
                except AuthenticationError:
                    limiter.record_failure('owner-password');raise
                store.change_password(body['new_password'],user.credential.digest_hex)
                sessions.revoke_user(user.user_id);connections.clear();limiter.record_success('owner-password')
                return respond(start,ApiResponse(200,data={'changed':True,'reauthentication_required':True}))
            if path=='/api/v1/owner/business' and method=='GET':return respond(start,ApiResponse(200,data=business.workspace(store)))
            if path=='/api/v1/owner/business' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=business.save(store,_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/screen' and method=='POST':return respond(start,ApiResponse(200,data=business.screen(store,_json_body(env))))
            if path=='/api/v1/owner/handoff' and method=='POST':return respond(start,ApiResponse(200,data=business.handoff(store,_json_body(env))))
            if path=='/api/v1/owner/planning' and method=='POST':return respond(start,ApiResponse(200,data=business.preview_plan(store,_json_body(env))))
            if path=='/api/v1/owner/trends' and method=='POST':return respond(start,ApiResponse(200,data=business.trends(store,_json_body(env))))
            if path=='/api/v1/owner/privacy' and method=='GET':return respond(start,ApiResponse(200,data=privacy.preview(store)))
            if path=='/api/v1/owner/backup-list' and method=='GET':return respond(start,ApiResponse(200,data=privacy.backup_list(store)))
            if path in {'/api/v1/owner/reset','/api/v1/owner/delete-backup'} and method=='POST':
                body=_json_body(env);password=body.get('current_password')
                if not isinstance(password,str) or len(password)>128:raise ValueError('invalid password')
                limiter.check('owner-privacy');user=store.owner()
                try:authenticate(user,password)
                except AuthenticationError:
                    limiter.record_failure('owner-privacy');raise
                result=privacy.reset(store,body,user.credential.digest_hex) if path.endswith('/reset') else privacy.delete_backup(store,body)
                limiter.record_success('owner-privacy')
                if path.endswith('/reset'):sessions.revoke_user(user.user_id);connections.clear()
                return respond(start,ApiResponse(200,data=result))
            if path=='/api/v1/owner/connections' and method=='GET':return respond(start,ApiResponse(200,data=connections.status()))
            if path=='/api/v1/owner/connections' and method=='POST':return respond(start,ApiResponse(200,data=connections.configure(_json_body(env))))
            if path=='/api/v1/owner/news-fetch' and method=='POST':return respond(start,ApiResponse(200,data=connections.news_feed(_json_body(env))))
            if path=='/api/v1/owner/news-snapshots' and method=='POST':return respond(start,ApiResponse(200,data=news.save(store,_json_body(env),connections)))
            if path=='/api/v1/owner/news-source' and method=='POST':return respond(start,ApiResponse(200,data=news.read(store,_json_body(env))))
            if path=='/api/v1/owner/company-fetch' and method=='POST':return respond(start,ApiResponse(200,data=connections.company_overview(_json_body(env))))
            if path=='/api/v1/owner/company-snapshots' and method=='POST':return respond(start,ApiResponse(200,data=company.save(store,_json_body(env),connections)))
            if path=='/api/v1/owner/company-source' and method=='POST':return respond(start,ApiResponse(200,data=company.read(store,_json_body(env))))
            if path=='/api/v1/owner/market-history-fetch' and method=='POST':return respond(start,ApiResponse(200,data=connections.market_history(_json_body(env))))
            if path=='/api/v1/owner/market-history' and method=='POST':return respond(start,ApiResponse(200,data=market_history.save(store,_json_body(env),connections)))
            if path=='/api/v1/owner/market-history' and method=='GET':return respond(start,ApiResponse(200,data=market_history.history(store)))
            if path=='/api/v1/owner/quote-fetch-public' and method=='POST':return respond(start,ApiResponse(200,data=connections.public_market(_json_body(env))))
            if path=='/api/v1/owner/market-history-fetch-public' and method=='POST':return respond(start,ApiResponse(200,data=connections.public_market(_json_body(env),history=True)))
            if path=='/api/v1/owner/quote-fetch' and method=='POST':return respond(start,ApiResponse(200,data=connections.quote(_json_body(env))))
            if path=='/api/v1/owner/ai-preview' and method=='POST':return respond(start,ApiResponse(200,data=connections.preview(_json_body(env))))
            if path=='/api/v1/owner/ai-generate' and method=='POST':return respond(start,ApiResponse(200,data=connections.generate(_json_body(env))))
            if path=='/api/v1/owner/cash-flows' and method=='GET':return respond(start,ApiResponse(200,data=cash_history(store)))
            if path=='/api/v1/owner/cash-flows' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=save_cash(store,_json_body(env),delete=method=='DELETE')))
            if path=='/api/v1/owner/import-preview' and method=='POST':return respond(start,ApiResponse(200,data=import_preview(store,_json_body(env))))
            if path=='/api/v1/owner/import-confirm' and method=='POST':return respond(start,ApiResponse(200,data=import_commit(store,_json_body(env))))
            if path=='/api/v1/owner/export' and method=='GET':return respond(start,ApiResponse(200,data=export_data(store)))
            if path=='/api/v1/owner/academy' and method=='GET':return respond(start,ApiResponse(200,data=academy()))
            if path=='/api/v1/owner/settings' and method=='GET':return respond(start,ApiResponse(200,data=settings(store)))
            if path=='/api/v1/owner/allocation-assignment' and method=='POST':return respond(start,ApiResponse(200,data=business.assign_position(store,_json_body(env))))
            if path=='/api/v1/owner/daily-schedule' and method=='POST':return respond(start,ApiResponse(200,data=schedule.save(store,_json_body(env))))
            if path=='/api/v1/owner/daily-schedule-status' and method=='POST':
                body=_json_body(env);business.fields(body,'account_id');return respond(start,ApiResponse(200,data=schedule.status(store,body['account_id'])))
            if path=='/api/v1/owner/trade-context' and method=='POST':return respond(start,ApiResponse(200,data=trade_context.save(store,_json_body(env))))
            if path=='/api/v1/owner/trade-context-history' and method=='POST':return respond(start,ApiResponse(200,data=trade_context.history(store,_json_body(env))))
            if path=='/api/v1/owner/constitution' and method=='GET':return respond(start,ApiResponse(200,data=constitution.history(store)))
            if path=='/api/v1/owner/constitution' and method=='POST':return respond(start,ApiResponse(200,data=constitution.save(store,_json_body(env))))
            if path=='/api/v1/owner/insight-feedback' and method=='POST':return respond(start,ApiResponse(200,data=feedback.save(store,_json_body(env))))
            if path=='/api/v1/owner/insight-feedback' and method=='GET':return respond(start,ApiResponse(200,data=feedback.summary(store)))
            if path=='/api/v1/owner/insight-feedback-history' and method=='POST':return respond(start,ApiResponse(200,data=feedback.history(store,_json_body(env))))
            if path=='/api/v1/owner/fx-rates' and method=='GET':return respond(start,ApiResponse(200,data=fx.history(store)))
            if path=='/api/v1/owner/fx-rates' and method=='POST':return respond(start,ApiResponse(200,data=fx.save(store,_json_body(env))))
            if path=='/api/v1/owner/base-valuation' and method=='GET':return respond(start,ApiResponse(200,data=fx.valuation(store)))
            if path=='/api/v1/owner/research-memory' and method=='POST':return respond(start,ApiResponse(200,data=research_memory.read(store,_json_body(env))))
            if path=='/api/v1/owner/research-position' and method=='POST':return respond(start,ApiResponse(200,data=research_position.read(store,_json_body(env))))
            if path=='/api/v1/owner/research-technical' and method=='POST':return respond(start,ApiResponse(200,data=research_technical.read(store,_json_body(env))))
            if path=='/api/v1/owner/research-report-preview' and method=='POST':return respond(start,ApiResponse(200,data=research_reports.preview(store,_json_body(env),connections.receipts)))
            if path=='/api/v1/owner/research-reports' and method=='POST':return respond(start,ApiResponse(200,data=research_reports.save(store,_json_body(env),connections.receipts)))
            if path=='/api/v1/owner/research-reports' and method=='GET':return respond(start,ApiResponse(200,data=research_reports.history(store)))
            if path=='/api/v1/owner/coach-period-preview' and method=='POST':return respond(start,ApiResponse(200,data=coach_period.preview(store,_json_body(env))))
            if path=='/api/v1/owner/coach-period' and method=='POST':return respond(start,ApiResponse(200,data=coach_period.save(store,_json_body(env))))
            if path=='/api/v1/owner/coach-period' and method=='GET':return respond(start,ApiResponse(200,data=coach_period.history(store)))
            if path=='/api/v1/owner/coach-review' and method=='POST':return respond(start,ApiResponse(200,data=coach.annotate(store,_json_body(env))))
            if path=='/api/v1/owner/coach-preview' and method=='POST':return respond(start,ApiResponse(200,data=coach.preview(store,_json_body(env))))
            if path=='/api/v1/owner/coach' and method=='POST':return respond(start,ApiResponse(200,data=coach.save(store,_json_body(env))))
            if path=='/api/v1/owner/coach' and method=='GET':return respond(start,ApiResponse(200,data=coach.history(store)))
            if path=='/api/v1/owner/daily-ai-draft' and method=='POST':return respond(start,ApiResponse(200,data=daily.save_ai_draft(store,_json_body(env),connections.receipts)))
            if path=='/api/v1/owner/daily-capture' and method=='POST':return respond(start,ApiResponse(200,data=daily.capture(store,_json_body(env))))
            if path=='/api/v1/owner/daily-history' and method=='POST':
                body=_json_body(env);business.fields(body,'account_id');return respond(start,ApiResponse(200,data=daily.history(store,body['account_id'])))
            if path=='/api/v1/owner/diagnosis-scope' and method=='POST':
                body=_json_body(env);business.fields(body,'account_id');return respond(start,ApiResponse(200,data=diagnosis_scope.read(store,body['account_id'])))
            if path=='/api/v1/owner/diagnosis-sources' and method=='POST':return respond(start,ApiResponse(200,data=diagnosis_sources.read(store,_json_body(env))))
            if path=='/api/v1/owner/diagnosis-preview' and method=='POST':return respond(start,ApiResponse(200,data=diagnosis.preview(store,_json_body(env))))
            if path=='/api/v1/owner/diagnosis' and method=='POST':return respond(start,ApiResponse(200,data=diagnosis.save(store,_json_body(env))))
            if path=='/api/v1/owner/diagnosis-history' and method=='POST':
                body=_json_body(env);business.fields(body,'account_id');return respond(start,ApiResponse(200,data=diagnosis.history(store,body['account_id'])))
            if path=='/api/v1/owner/plan-trades' and method=='POST':return respond(start,ApiResponse(200,data=record_trade(store,_json_body(env))))
            if path=='/api/v1/owner/plan-executions' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=save_execution(store,_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/plans' and method=='GET':return respond(start,ApiResponse(200,data=plan_workspace(store)))
            if path=='/api/v1/owner/plans' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=save_plan(store,_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/evolve' and method=='GET':return respond(start,ApiResponse(200,data=evolve_workspace(store)))
            if path=='/api/v1/owner/evolve' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=save_review(store,_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/journal' and method=='GET':return respond(start,ApiResponse(200,data=journal_workspace(store)))
            if path=='/api/v1/owner/journal' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=save_journal(store,_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/documents' and method=='GET':return respond(start,ApiResponse(200,data=store.documents()))
            if path=='/api/v1/owner/documents' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=store.save_document(_json_body(env),archive=method=='DELETE')))
            if path=='/api/v1/owner/trade-reference' and method=='POST':return respond(start,ApiResponse(200,data=store.link_trade(_json_body(env))))
            if path=='/api/v1/owner/views' and method=='GET':return respond(start,ApiResponse(200,data=project(store.ledger())))
            if path=='/api/v1/owner/ledger' and method=='GET':return respond(start,ApiResponse(200,data=store.ledger()))
            if path=='/api/v1/owner/account-edit' and method=='POST':return respond(start,ApiResponse(200,data=store.edit_account(_json_body(env))))
            if path=='/api/v1/owner/accounts' and method=='DELETE':return respond(start,ApiResponse(200,data=store.delete_account(_json_body(env))))
            if path=='/api/v1/owner/accounts' and method=='POST':return respond(start,ApiResponse(200,data=store.add_account(_json_body(env))))
            if path=='/api/v1/owner/trades' and method in {'POST','DELETE'}:return respond(start,ApiResponse(200,data=store.trade(_json_body(env),delete=method=='DELETE')))
            if path=='/api/v1/owner/backup' and method=='POST':
                if _json_body(env):raise ValueError('invalid fields')
                return respond(start,ApiResponse(200,data=store.backup()))
            return respond(start,error(404,'capability_unsupported'))
        except ConnectionFailure as ex:
            safe_codes={'provider_auth_failed','provider_permission_denied','provider_model_unavailable','provider_rate_limited','connection_failed','invalid_model_output','model_output_truncated','public_market_unavailable'}
            return respond(start,error(503,str(ex) if str(ex) in safe_codes else 'connection_unavailable'))
        except RateLimitError as ex:
            resp=error(429,'too_many_attempts')
            return respond(start,ApiResponse(resp.status,problem=resp.problem,headers=(('Retry-After',str(ex.retry_after_seconds)),)))
        except AuthenticationError:return respond(start,error(401,'invalid_credentials'))
        except SessionError:return respond(start,error(401,'invalid_session'))
        except PermissionError:return respond(start,error(403,'csrf_rejected'))
        except AccountHasHistory:return respond(start,error(409,'account_has_history'))
        except Conflict:return respond(start,error(409,'local_conflict'))
        except LedgerInvalid:return respond(start,error(422,'owner_ledger_invalid'))
        except (ValueError,TypeError,KeyError):return respond(start,error(400,'connection_config_invalid' if path=='/api/v1/owner/connections' else 'connection_request_invalid' if path in {'/api/v1/owner/quote-fetch','/api/v1/owner/ai-preview','/api/v1/owner/ai-generate'} else 'privacy_invalid' if path in {'/api/v1/owner/reset','/api/v1/owner/delete-backup'} else 'business_invalid' if path in {'/api/v1/owner/business','/api/v1/owner/screen','/api/v1/owner/handoff','/api/v1/owner/planning','/api/v1/owner/trends'} else 'owner_cash_invalid' if path=='/api/v1/owner/cash-flows' else 'owner_transfer_invalid' if path in {'/api/v1/owner/import-preview','/api/v1/owner/import-confirm'} else 'owner_plan_invalid' if path=='/api/v1/owner/plans' else 'owner_evolve_invalid' if path in {'/api/v1/owner/evolve','/api/v1/owner/journal'} else 'owner_research_invalid' if path in {'/api/v1/owner/documents','/api/v1/owner/trade-reference'} else 'owner_invalid'))
        except (OSError,sqlite3.Error):return respond(start,error(503,'local_unavailable'))
    app.store=store;app.sessions=sessions;app.connections=connections
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=4322)
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[4]/'.owner-state')
    parser.add_argument('--restore-from',type=Path)
    parser.add_argument('--ui-build',type=Path,default=Path(__file__).resolve().parents[4]/'frontend/owner-ui/dist',help='Verified Vue dist directory (defaults to the bundled UI)')
    parser.add_argument('--open-browser',action='store_true')
    args=parser.parse_args()
    if args.restore_from:
        restore_owner(args.restore_from,args.data_dir)
        print('已恢复到新目录；使用备份时的本地账号口令登录，原目录未覆盖。');return
    app=application(port=args.port,data_dir=args.data_dir,ui_dist=args.ui_build)
    with make_server('127.0.0.1',args.port,app,server_class=ScheduledOwnerServer,handler_class=QuietRequestHandler) as server:
        print(f'Community 本地账本：http://127.0.0.1:{args.port}/',flush=True)
        print('首次使用请在浏览器创建本地账号。无默认口令，不连接券商或旧数据库。',flush=True)
        if args.open_browser:
            import webbrowser
            from threading import Timer
            Timer(0.2,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}/')).start()
        server.serve_forever()

if __name__=='__main__':main()
