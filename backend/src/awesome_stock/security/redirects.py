"""Allowlisted post-authentication return paths."""


_ALLOWED_ROOTS = frozenset(
    {"academy", "cockpit", "portfolio", "research", "plan", "review", "settings"}
)


def safe_return_path(candidate: object, *, fallback: str = "/cockpit") -> str:
    """Return a safe in-product path or the fixed cockpit fallback."""

    if not isinstance(candidate, str) or not candidate.startswith("/"):
        return fallback
    lowered = candidate.casefold()
    if (
        candidate.startswith("//")
        or "\\" in candidate
        or any(ord(char) < 32 for char in candidate)
        or "%2f" in lowered
        or "%5c" in lowered
    ):
        return fallback
    path = candidate.split("#", 1)[0].split("?", 1)[0]
    root = path.lstrip("/").split("/", 1)[0]
    if root not in _ALLOWED_ROOTS:
        return fallback
    return candidate
