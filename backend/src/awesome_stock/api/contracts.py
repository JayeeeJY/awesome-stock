"""Stable response and failure semantics independent of an HTTP framework."""

from dataclasses import dataclass
from typing import Mapping

from awesome_stock.core.ledger import FactValidationError
from awesome_stock.security.access import AuthorizationError
from awesome_stock.security.auth import AuthenticationError
from awesome_stock.security.sessions import SessionError


PUBLIC_MESSAGES = {
    'public_market_unavailable': '公共行情暂不可用、缺少完整日线或标的身份不符。未保存；可以稍后主动查询，或切换到你自己的行情 API。',
    'provider_auth_failed': '服务商拒绝 API Key，请检查 Key 是否有效。',
    'provider_permission_denied': '服务商拒绝访问，请检查账号、模型权限和服务可用区域。',
    'provider_model_unavailable': '服务商未找到模型或接口，请检查实际模型 ID。',
    'provider_rate_limited': '服务商请求额度或频率受限，请检查余额、配额和频率限制。',
    'connection_failed': '无法连接服务商或请求超时，请检查网络；Ollama 请检查服务是否启动。',
    'invalid_model_output': '模型返回不完整或没有可用文本，请检查模型兼容性。',
    'model_output_truncated': '模型输出达到本次长度上限，未生成完整答案。请缩小问题或材料后重新预览。',

    'account_has_history': '账户有现金、成交、资金流水或历史业务引用，不能删除。请保留账户以供核对。',
    "connection_config_invalid": "模型或行情配置无效。模型名称不是登录账号或邮箱；云端需填写你自己的API Key，Ollama需填写本机已安装的模型名且不填写Key。",
    "connection_request_invalid": "连接请求无效。请检查标的代码、问题和上下文，或重新预览后确认发送。",
    "connection_unavailable": "连接未启用、预览已过期，或服务请求失败。请核对配置、额度和服务状态；没有自动切换服务或重试。",
    "business_invalid": "输入无效。请核对必填字段、日期、普通十进制数及证据状态；试算需账户全部持仓具有三日内同币种价格，配置比例须合计100%。",
    "privacy_invalid": "请先预览范围，填写当前口令并输入准确确认文字。已有备份和外部副本需要分别处理。",
    "owner_cash_invalid": "资金流水输入无效。请选择既有账户、入金或出金，填写正数金额与含时区的发生时间；更正时不能改变账户。",
    "owner_transfer_invalid": "导入无效。请检查固定CSV表头、32KiB及200行上限、账户与预览结果；整批未导入。",
    "owner_plan_invalid": "计划输入无效。请检查标题、Decision版本、触发/风险/停止条件、1至12条步骤和复核日期；已归档Decision不能用于新建计划。",
    "owner_evolve_invalid": "复盘输入无效，请检查Decision版本、复盘日期、过程说明与下次改进；标为已观察时需要填写结果备注。",
    "owner_research_invalid": "记录或引用无效。请检查必填判断、标的和复核日期；不同标的、未知版本或已归档记录不能新增引用。",
    "owner_invalid": "输入无效，请检查账号、口令、成交时间和数值格式。数值最多12位整数、8位小数，不能使用科学计数法。",
    "owner_ledger_invalid": "操作会导致现金不足、超卖或后续账目不成立，未保存。请核对成交时间、数量、金额与手续费。",
    "owner_initialized": "本地账号已经建立，不能重复初始化。",
    "too_many_attempts": "尝试次数过多，请稍后重试。",
    "local_conflict": "内容已变化或请求编号重复，请重新载入后保存；你的输入仍保留。",
    "local_unavailable": "本地保存暂不可用，未确认写入；请保留输入并重试。",
    "local_invalid": "输入无效，请检查标题、正文和版本。",
    "invalid_credentials": "用户名或密码不正确",
    "invalid_session": "会话已失效，请重新登录",
    "refresh_reused_family_revoked": "会话已失效，请重新登录",
    "access_denied": "无权访问该资源",
    "invalid_request": "请求内容无效",
    "invalid_plan_input": "计划输入无效",
    "invalid_research_input": "研究输入无效",
    "invalid_evolve_input": "进化输入无效",
    "csrf_rejected": "请求安全校验失败",
    "capability_unavailable": "服务暂时不可用，请稍后重试",
    "capability_unsupported": "当前版本不支持此能力",
    "legacy_data_unavailable": "历史数据暂不可用",
    "internal_error": "服务暂时无法完成请求",
}


def _request_id(value: object) -> str | None:
    if not isinstance(value, str) or not (1 <= len(value) <= 64):
        return None
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
    return value if all(character in allowed for character in value) else None


class CapabilityError(RuntimeError):
    """Explicit unavailable/unsupported capability without fake success."""

    def __init__(self, kind: str, *, code: str | None = None) -> None:
        if kind not in {"unavailable", "unsupported"}:
            raise ValueError("capability kind must be unavailable or unsupported")
        self.kind = kind
        self.code = code or f"capability_{kind}"
        super().__init__(PUBLIC_MESSAGES.get(self.code, PUBLIC_MESSAGES[f"capability_{kind}"]))


@dataclass(frozen=True)
class ApiProblem:
    """Public error body with no exception details or secret-bearing payload."""

    status: int
    code: str
    message: str
    retryable: bool
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, int) or self.status < 400 or self.status > 599:
            raise ValueError("problem status must be an HTTP error status")
        if self.code not in PUBLIC_MESSAGES:
            raise ValueError("problem code is not public")
        if self.message != PUBLIC_MESSAGES[self.code]:
            raise ValueError("problem message must use the public message registry")
        object.__setattr__(self, "request_id", _request_id(self.request_id))

    def as_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
            }
        }
        if self.request_id is not None:
            body["error"]["request_id"] = self.request_id
        return body


@dataclass(frozen=True)
class ApiResponse:
    """A response is either data or a problem, never both and never neither."""

    status: int
    data: Mapping[str, object] | None = None
    problem: ApiProblem | None = None
    cookies: tuple[object, ...] = ()
    headers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if (self.data is None) == (self.problem is None):
            raise ValueError("response must contain exactly one of data or problem")
        if self.problem is not None and self.status != self.problem.status:
            raise ValueError("response status must match problem status")
        if self.problem is None and not 200 <= self.status < 400:
            raise ValueError("data response must use a non-error status")

    @classmethod
    def failure(cls, problem: ApiProblem, **kwargs: object) -> "ApiResponse":
        return cls(problem.status, problem=problem, **kwargs)

    def body(self) -> dict[str, object]:
        return dict(self.data) if self.data is not None else self.problem.as_dict()


def problem_from_exception(error: Exception, *, request_id: object = None) -> ApiProblem:
    """Map known boundary errors to stable public failures; hide all other details."""

    if isinstance(error, AuthenticationError):
        status, code, retryable = 401, "invalid_credentials", False
    elif isinstance(error, SessionError):
        status = 401
        code = (
            "refresh_reused_family_revoked"
            if error.code == "refresh_reused_family_revoked"
            else "invalid_session"
        )
        retryable = False
    elif isinstance(error, AuthorizationError):
        status, code, retryable = 403, "access_denied", False
    elif error.__class__.__name__ == "CsrfError":
        status, code, retryable = 403, "csrf_rejected", False
    elif isinstance(error, FactValidationError):
        status, code, retryable = 422, "invalid_request", False
    elif getattr(error, "code", None) in {"invalid_plan_input", "invalid_research_input", "invalid_evolve_input"}:
        status, code, retryable = 422, error.code, False
    elif isinstance(error, CapabilityError):
        status = 503 if error.kind == "unavailable" else 501
        code = error.code if error.code in PUBLIC_MESSAGES else f"capability_{error.kind}"
        retryable = error.kind == "unavailable"
    else:
        status, code, retryable = 500, "internal_error", False
    return ApiProblem(status, code, PUBLIC_MESSAGES[code], retryable, _request_id(request_id))
