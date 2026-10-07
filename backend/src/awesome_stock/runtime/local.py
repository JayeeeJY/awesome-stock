"""Loopback-only local synthetic persistence candidate."""
import argparse
from pathlib import Path
import sqlite3
from wsgiref.simple_server import make_server
from awesome_stock.api.contracts import ApiResponse, ApiProblem, PUBLIC_MESSAGES
from awesome_stock.api.cookies import ACCESS_COOKIE, validate_csrf
from awesome_stock.storage.local import LocalStore, Conflict, restore
from .demo import DemoRuntime, synthetic_rows
from .server import create_application, _cookies, _headers, _json_body, _response, _file_response, QuietRequestHandler


def failure(status, message):
    code = {400:'local_invalid',403:'csrf_rejected',404:'capability_unsupported',405:'capability_unsupported',409:'local_conflict',503:'local_unavailable'}[status]
    return ApiResponse.failure(ApiProblem(status, code, PUBLIC_MESSAGES[code], status==503, None))


class LocalRuntime(DemoRuntime):
    def __init__(self, *, allowed_origins, store):
        super().__init__(allowed_origins=allowed_origins)
        self.store = store
        self._rows = store.snapshot()

    def bootstrap(self):
        return {**super().bootstrap(), 'mode':'synthetic_local', 'persistence':True, 'saved_scope':'synthetic_snapshot_and_manual_drafts', 'credential_lifetime':'until_process_restart'}


def application(*, port, data_dir):
    store = LocalStore(data_dir, synthetic_rows())
    base = create_application(port=port, runtime_factory=lambda **kw: LocalRuntime(store=store, **kw))
    runtime = base.demo_runtime
    origins = frozenset({f'http://127.0.0.1:{port}',f'http://localhost:{port}'})
    root = base.frontend_root

    def app(env, start):
        path = env.get('PATH_INFO','/'); method=env.get('REQUEST_METHOD','GET')
        # Reject DNS rebinding and cross-site requests, including demo bootstrap.
        if env.get('HTTP_HOST') not in {f'127.0.0.1:{port}',f'localhost:{port}'}:
            return _response(start, failure(403,'本地地址不匹配'))
        if env.get('HTTP_ORIGIN') and env['HTTP_ORIGIN'] not in origins:
            return _response(start, failure(403,'请求来源不匹配'))
        if path in {'/local-data','/assets/local-data.js','/assets/local-data.css'} and method=='GET':
            filename={'/local-data':'local-data.html','/assets/local-data.js':'local-data.js','/assets/local-data.css':'local-data.css'}[path]
            return _file_response(start,root/filename)
        if path=='/api/v1/health' and method=='GET':
            return _response(start,ApiResponse(200,data={'status':'ok','mode':'synthetic_local','schema_version':1}))
        if path=='/api/v1/local/session' and method=='GET':
            status=runtime.session_status(_cookies(env).get(ACCESS_COOKIE,''))
            return _response(start,ApiResponse(200,data={'authenticated':status.problem is None}))
        if not path.startswith('/api/v1/local/'):
            return base(env,start)
        cookies=_cookies(env)
        try:
            status=runtime.session_status(cookies.get(ACCESS_COOKIE,''))
            if status.problem is not None:return _response(start,status)
            if method not in {'GET','POST','DELETE'}:
                return _response(start,failure(405,'不支持此操作'))
            if method!='GET':
                validate_csrf(method=method,headers=_headers(env),cookies=cookies,allowed_origins=origins)
            if path=='/api/v1/local/drafts':
                if method=='GET':return _response(start,ApiResponse(200,data={'drafts':store.list_drafts(),'synthetic':True}))
                return _response(start,ApiResponse(200,data=store.mutate(_json_body(env),delete=method=='DELETE')))
            if path=='/api/v1/local/status' and method=='GET':
                return _response(start,ApiResponse(200,data={'mode':'synthetic_local','schema_version':1,'saved_drafts':len(store.list_drafts()),'snapshot_trades':len(store.snapshot()),'credentials_persisted':False}))
            if path=='/api/v1/local/backup' and method=='POST':
                if _json_body(env):raise ValueError('unexpected fields')
                return _response(start,ApiResponse(200,data=store.backup()))
            return _response(start,failure(404,'未找到操作'))
        except Conflict:
            return _response(start,failure(409,'内容已变化或请求编号重复，请重新载入后保存；你的输入仍保留。'))
        except PermissionError:
            return _response(start,failure(403,'请求安全校验失败'))
        except (ValueError,TypeError,KeyError):
            return _response(start,failure(400,'输入无效，请检查标题、正文和版本。'))
        except (sqlite3.Error,OSError):
            return _response(start,failure(503,'本地保存暂不可用，未确认写入；请保留输入并重试。'))
    app.store=store;app.demo_runtime=runtime
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=4321)
    parser.add_argument('--open-browser',action='store_true')
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[4]/'.local-state')
    parser.add_argument('--restore-from',type=Path)
    args=parser.parse_args()
    if args.restore_from:
        restore(args.restore_from,args.data_dir)
        print('已恢复到新数据目录。使用相同 --data-dir 启动核对；原数据未覆盖。')
        return
    app=application(port=args.port,data_dir=args.data_dir)
    print(f'Community 持久化测试：http://127.0.0.1:{args.port}/local-data',flush=True)
    print('仅合成快照与手动草稿保存在本机。临时会话重启后失效。',flush=True)
    with make_server('127.0.0.1',args.port,app,handler_class=QuietRequestHandler) as server:
        if args.open_browser:
            import webbrowser
            from threading import Timer
            Timer(0.2, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}/local-data')).start()
        server.serve_forever()

if __name__=='__main__':main()
