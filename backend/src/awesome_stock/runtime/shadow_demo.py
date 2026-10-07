"""Authenticated read-only projection of synthetic shadow evidence."""

from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.verification.shadow import build_switch_readiness, run_shadow_comparison


def shadow_response(runtime, *, access_token: str, request_id: object = None) -> ApiResponse:
    try:
        session = runtime.session_status(access_token, request_id=request_id)
        if session.problem is not None:
            return session
        report = run_shadow_comparison()
        readiness = build_switch_readiness(report)
        return ApiResponse(200, data={
            "mode": "synthetic_shadow",
            "persistence": False,
            "legacy_source_connected": False,
            "real_user_data_used": False,
            "write_path_changed": False,
            "comparison": report.as_dict(),
            "readiness": readiness.as_dict(),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
