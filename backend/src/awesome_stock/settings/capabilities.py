"""Validated, non-configurable capability facts for the isolated demo."""

from dataclasses import dataclass


CAPABILITY_STATES = frozenset({"available", "not_enabled", "not_connected"})


@dataclass(frozen=True)
class CapabilityFact:
    key: str
    label: str
    state: str
    state_label: str
    detail: str

    def __post_init__(self) -> None:
        if not self.key or not self.label or not self.detail:
            raise ValueError("capability facts require a key, label and detail")
        if self.state not in CAPABILITY_STATES:
            raise ValueError("unsupported capability state")


@dataclass(frozen=True)
class SettingsOverview:
    capabilities: tuple[CapabilityFact, ...]
    privacy_boundaries: tuple[str, ...]

    def __post_init__(self) -> None:
        keys = tuple(item.key for item in self.capabilities)
        if len(keys) != 6 or len(set(keys)) != len(keys):
            raise ValueError("settings must expose six unique capability facts")
        if len(self.privacy_boundaries) != 4 or any(not item for item in self.privacy_boundaries):
            raise ValueError("settings must expose four explicit privacy boundaries")


def build_settings_overview() -> SettingsOverview:
    """Return only facts that are true for the current in-memory demo."""

    return SettingsOverview(
        capabilities=(
            CapabilityFact(
                "session_auth",
                "会话与登录",
                "available",
                "可用",
                "本地会话管理，仅在当前运行期间有效。",
            ),
            CapabilityFact(
                "investment_loop",
                "投资闭环",
                "available",
                "可用",
                "组合、研究、计划与进化使用隔离的合成事实。",
            ),
            CapabilityFact(
                "academy_documents",
                "学院文档",
                "available",
                "可用",
                "内置原创静态知识文档与代码原生示意图。",
            ),
            CapabilityFact(
                "persistence",
                "数据持久化",
                "not_enabled",
                "未启用",
                "所有数据仅在内存中，服务重启后清空。",
            ),
            CapabilityFact(
                "cloud_ai",
                "云端 AI",
                "not_connected",
                "未连接",
                "当前演示未连接任何云端模型服务。",
            ),
            CapabilityFact(
                "local_ai",
                "本地模型",
                "not_connected",
                "未连接",
                "当前演示未配置或探测本地模型。",
            ),
        ),
        privacy_boundaries=(
            "只使用内置合成数据",
            "不保存设置或账户信息",
            "不读取本机密钥或环境凭据",
            "不连接券商、行情或 AI 服务",
        ),
    )
