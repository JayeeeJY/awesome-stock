"""Loopback-only WSGI server for the all-synthetic Community shell."""

import argparse
from http.cookies import SimpleCookie
import json
import mimetypes
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from wsgiref.simple_server import WSGIRequestHandler, make_server

from awesome_stock.api.contracts import ApiResponse, CapabilityError, problem_from_exception
from awesome_stock.api.cookies import ACCESS_COOKIE, CookieSpec, validate_csrf

from .academy_demo import library_response
from .demo import ACCOUNT_ID, WORKSPACE_ID, DemoRuntime
from .evolve_demo import reviews_response, rule_preview_response, trends_response
from .plan_demo import allocation_response, build_up_response, pre_trade_response
from .research_demo import batch_response, company_response, screening_response
from .settings_demo import overview_response
from .shadow_demo import shadow_response


APP_ROUTES = frozenset(
    {
        "/login",
        "/cockpit",
        "/cockpit/actions",
        "/portfolio",
        "/portfolio/trades",
        "/portfolio/accounts",
        "/research",
        "/research/screening",
        "/research/batch",
        "/plan/allocation",
        "/plan/build-up",
        "/plan/pre-trade",
        "/review",
        "/review/diagnosis",
        "/academy",
        "/settings",
    }
)
COMPATIBILITY_REDIRECTS = {
    "/": "/login",
    "/app": "/login",
    "/dashboard": "/cockpit",
    "/today": "/cockpit",
    "/today/actions": "/cockpit/actions",
    "/research/what-if": "/plan/pre-trade",
    "/research/whatif": "/plan/pre-trade",
    "/research/build-up": "/plan/build-up",
    "/research/buildup": "/plan/build-up",
    "/analysis": "/research",
    "/analysis/single": "/research",
    "/screening": "/research/screening",
    "/stocks": "/research",
    "/about": "/settings",
    "/learn": "/academy",
    "/education": "/academy",
    "/portfolio/overview": "/portfolio",
    "/portfolio/diagnosis": "/review/diagnosis",
    "/portfolio/reminders": "/cockpit/actions",
    "/portfolio/journal": "/review",
    "/portfolio/whatif": "/plan/pre-trade",
    "/portfolio/what-if": "/plan/pre-trade",
    "/portfolio/allocation": "/plan/allocation",
    "/portfolio/buildup": "/plan/build-up",
    "/plan": "/plan/allocation",
    "/plan/buildup": "/plan/build-up",
    "/evolve/diagnosis": "/review/diagnosis",
    "/evolve": "/review",
    "/trades": "/portfolio/trades",
    "/accounts": "/portfolio/accounts",
    "/diagnosis": "/review/diagnosis",
    "/journal": "/review",
    "/whatif": "/plan/pre-trade",
    "/analysis/batch": "/research/batch",
    "/alerts": "/cockpit/actions",
}
SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    ("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
)


def _cookie_header(cookie: CookieSpec) -> str:
    parts = [
        f"{cookie.name}={quote(cookie.value, safe='-_~.')}",
        f"Max-Age={cookie.max_age}",
        "Path=/",
        "Secure",
        f"SameSite={cookie.same_site}",
    ]
    if cookie.http_only:
        parts.append("HttpOnly")
    return "; ".join(parts)


def _cookies(environ: dict[str, object]) -> dict[str, str]:
    parsed = SimpleCookie()
    parsed.load(str(environ.get("HTTP_COOKIE", "")))
    return {name: morsel.value for name, morsel in parsed.items()}


def _headers(environ: dict[str, object]) -> dict[str, str]:
    result = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-")
            result[name] = str(value)
    return result


def _json_body(environ: dict[str, object]) -> dict[str, object]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid content length") from exc
    if length < 0 or length > 65536:
        raise ValueError("request body is too large")
    payload = environ["wsgi.input"].read(length) if length else b"{}"
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON body must be an object")
    return value


def _response(start_response, response: ApiResponse) -> list[bytes]:
    payload = json.dumps(response.body(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(payload)))]
    headers.extend(SECURITY_HEADERS)
    headers.extend(response.headers)
    headers.extend(("Set-Cookie", _cookie_header(cookie)) for cookie in response.cookies)
    start_response(f"{response.status} {_status_text(response.status)}", headers)
    return [payload]


def _status_text(status: int) -> str:
    return {
        200: "OK",
        302: "Found",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        501: "Not Implemented",
        503: "Service Unavailable",
    }.get(status, "Response")


def _file_response(start_response, path: Path) -> list[bytes]:
    payload = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    headers = [("Content-Type", f"{content_type}; charset=utf-8"), ("Content-Length", str(len(payload)))]
    headers.extend(SECURITY_HEADERS)
    start_response("200 OK", headers)
    return [payload]


def create_application(*, port: int, frontend_root: Path | None = None, origin_port: int | None = None, runtime_factory=DemoRuntime):
    """Create an isolated WSGI app bound by the caller to a loopback address."""

    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("demo port must be between 1024 and 65535")
    if origin_port is not None and (not isinstance(origin_port, int) or not 1024 <= origin_port <= 65535):
        raise ValueError("public origin port must be between 1024 and 65535")
    root = frontend_root or Path(__file__).resolve().parents[4] / "frontend"
    if not (root / "index.html").is_file():
        raise ValueError("Community frontend root is incomplete")
    browser_port = origin_port or port
    origins = frozenset({f"http://127.0.0.1:{browser_port}", f"http://localhost:{browser_port}"})
    runtime = runtime_factory(allowed_origins=origins)

    def application(environ: dict[str, object], start_response) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        request_id = environ.get("HTTP_X_REQUEST_ID")
        cookies = _cookies(environ)
        headers = _headers(environ)
        try:
            if path == "/api/v1/health" and method == "GET":
                return _response(start_response, ApiResponse(200, data={"status": "ok", "mode": "synthetic_demo"}))
            if path == "/api/v1/demo/bootstrap" and method == "GET":
                return _response(start_response, ApiResponse(200, data=runtime.bootstrap()))
            if path == "/api/v1/auth/login" and method == "POST":
                body = _json_body(environ)
                return _response(
                    start_response,
                    runtime.api.login(
                        username=str(body.get("username", "")),
                        password=str(body.get("password", "")),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/auth/session" and method == "GET":
                return _response(
                    start_response,
                    runtime.session_status(cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/auth/refresh" and method == "POST":
                return _response(
                    start_response,
                    runtime.api.refresh(method=method, headers=headers, cookies=cookies, request_id=request_id),
                )
            if path == "/api/v1/auth/logout" and method == "POST":
                return _response(
                    start_response,
                    runtime.api.logout(method=method, headers=headers, cookies=cookies, request_id=request_id),
                )
            if path == "/api/v1/portfolio" and method == "GET":
                return _response(
                    start_response,
                    runtime.portfolio(cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/portfolio/trades" and method == "GET":
                return _response(
                    start_response,
                    runtime.api.list_legacy_trades(
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        grant=runtime.grant,
                        workspace_id=WORKSPACE_ID,
                        account_id=ACCOUNT_ID,
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/allocation" and method == "GET":
                return _response(
                    start_response,
                    allocation_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/allocation/draft" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                body = _json_body(environ)
                return _response(
                    start_response,
                    allocation_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        targets=body.get("targets"),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/build-up" and method == "GET":
                return _response(
                    start_response,
                    build_up_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/build-up/preview" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    build_up_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        values=_json_body(environ),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/pre-trade" and method == "GET":
                return _response(
                    start_response,
                    pre_trade_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/plan/pre-trade/check" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    pre_trade_response(
                        runtime,
                        access_token=cookies.get(ACCESS_COOKIE, ""),
                        values=_json_body(environ),
                        request_id=request_id,
                    ),
                )
            if path == "/api/v1/research/company" and method == "GET":
                return _response(
                    start_response,
                    company_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/research/company/brief" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    company_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/research/screening" and method == "GET":
                return _response(
                    start_response,
                    screening_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/research/screening/run" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    screening_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/research/batch" and method == "GET":
                return _response(
                    start_response,
                    batch_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/research/batch/compare" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    batch_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/evolve/reviews" and method == "GET":
                return _response(
                    start_response,
                    reviews_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/evolve/reviews/view" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    reviews_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/evolve/trends" and method == "GET":
                return _response(
                    start_response,
                    trends_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/evolve/trends/window" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    trends_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/evolve/rules/preview" and method == "POST":
                validate_csrf(method=method, headers=headers, cookies=cookies, allowed_origins=origins)
                return _response(
                    start_response,
                    rule_preview_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), values=_json_body(environ), request_id=request_id),
                )
            if path == "/api/v1/academy/library" and method == "GET":
                return _response(
                    start_response,
                    library_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/settings/overview" and method == "GET":
                return _response(
                    start_response,
                    overview_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path == "/api/v1/verification/shadow" and method == "GET":
                return _response(
                    start_response,
                    shadow_response(runtime, access_token=cookies.get(ACCESS_COOKIE, ""), request_id=request_id),
                )
            if path.startswith("/api/"):
                raise CapabilityError("unsupported")
            if path in COMPATIBILITY_REDIRECTS:
                target = COMPATIBILITY_REDIRECTS[path]
                start_response("302 Found", [("Location", target), *SECURITY_HEADERS])
                return [b""]
            if path == "/assets/styles.css":
                return _file_response(start_response, root / "styles.css")
            if path == "/assets/app.js":
                return _file_response(start_response, root / "app.js")
            if path in APP_ROUTES or (path.startswith("/stocks/") and len(path.split("/")) == 3):
                return _file_response(start_response, root / "index.html")
            problem = problem_from_exception(CapabilityError("unsupported"), request_id=request_id)
            problem = type(problem)(404, "capability_unsupported", problem.message, False, problem.request_id)
            return _response(start_response, ApiResponse.failure(problem))
        except (ValueError, json.JSONDecodeError):
            problem = problem_from_exception(CapabilityError("unsupported", code="invalid_request"), request_id=request_id)
            problem = type(problem)(400, "invalid_request", "请求内容无效", False, problem.request_id)
            return _response(start_response, ApiResponse.failure(problem))
        except Exception as error:
            return _response(start_response, ApiResponse.failure(problem_from_exception(error, request_id=request_id)))

    application.demo_runtime = runtime
    application.frontend_root = root
    return application


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4319)
    parser.add_argument(
        "--origin-port",
        type=int,
        help="browser-facing loopback port when a local reverse proxy is used",
    )
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("synthetic demo may bind only to loopback")
    app = create_application(port=args.port, origin_port=args.origin_port)
    runtime = app.demo_runtime
    print(f"Awesome Stock Community demo: http://{args.host}:{args.port}/login", flush=True)
    print(f"Temporary username: {runtime.identity.username}", flush=True)
    print(f"Temporary password: {runtime.identity.password}", flush=True)
    print("All data and credentials are synthetic and disappear when this process stops.", flush=True)
    with make_server(args.host, args.port, app, handler_class=QuietRequestHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
