"""Authenticated projection for transparent Community runtime settings."""

from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.settings.capabilities import CapabilityFact, build_settings_overview


def _capability(item: CapabilityFact) -> dict[str, str]:
    return {
        "key": item.key,
        "label": item.label,
        "state": item.state,
        "state_label": item.state_label,
        "detail": item.detail,
    }


def overview_response(runtime, *, access_token: str, request_id: object = None) -> ApiResponse:
    try:
        session = runtime.session_status(access_token, request_id=request_id)
        if session.problem is not None:
            return session
        overview = build_settings_overview()
        return ApiResponse(200, data={
            "mode": "synthetic_demo",
            "persistence": False,
            "configuration_writable": False,
            "external_provider": False,
            "secret_access": False,
            "summary": (
                {"key": "runtime", "label": "运行模式", "value": "本地合成演示", "detail": "Loopback 单进程"},
                {"key": "data", "label": "数据状态", "value": "仅内存 · 重启清空", "detail": "无数据库写入"},
                {"key": "connections", "label": "外部连接", "value": "全部关闭", "detail": "无 Provider 调用"},
            ),
            "capabilities": tuple(_capability(item) for item in overview.capabilities),
            "privacy_boundaries": overview.privacy_boundaries,
            "session": {
                "workspace_id": runtime.grant.workspace_id,
                "workspace_label": "Demo Workspace",
                "role": runtime.grant.role,
                "role_label": "Owner",
                "scope_label": f"{len(runtime.grant.account_ids)} 个合成账户",
                "credential_lifetime": "服务停止或重启前",
            },
            "future_installation": {
                "cloud_ai_default_when_configured": True,
                "local_model_optional": True,
                "core_facts_work_without_ai": True,
                "configuration_available_now": False,
                "message": "未来安装层将以云端 AI 为默认能力、本地模型为可选增强；未配置任一模型时，核心事实与方法论能力仍可使用。",
            },
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
