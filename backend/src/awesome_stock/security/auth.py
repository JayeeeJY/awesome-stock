"""Credential contracts with generic failures and no default account path."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac


PBKDF2_ITERATIONS = 600_000
MIN_PASSWORD_LENGTH = 12
_DUMMY_SALT = bytes.fromhex("17d8f1c5b57afcfcb4567b42f690572a")
_DUMMY_DIGEST = bytes(32)


class AuthenticationError(ValueError):
    """A user-safe authentication failure that does not reveal account state."""

    code = "invalid_credentials"

    def __init__(self) -> None:
        super().__init__("用户名或密码不正确")


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


def _text(value: object, field: str) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


@dataclass(frozen=True)
class PasswordCredential:
    """Versioned PBKDF2 credential; plaintext is never retained."""

    salt_hex: str
    digest_hex: str
    iterations: int = PBKDF2_ITERATIONS
    algorithm: str = "pbkdf2_sha256"

    def __post_init__(self) -> None:
        if self.algorithm != "pbkdf2_sha256":
            raise ValueError("unsupported credential algorithm")
        if isinstance(self.iterations, bool) or self.iterations < PBKDF2_ITERATIONS:
            raise ValueError("credential iteration count is below policy")
        try:
            salt = bytes.fromhex(self.salt_hex)
            digest = bytes.fromhex(self.digest_hex)
        except ValueError as exc:
            raise ValueError("credential encoding is invalid") from exc
        if len(salt) < 16 or len(digest) != 32:
            raise ValueError("credential material has an invalid length")


@dataclass(frozen=True)
class UserRecord:
    """Server-owned identity record without plaintext credentials."""

    user_id: str
    username: str
    credential: PasswordCredential
    status: UserStatus | str = UserStatus.ACTIVE

    def __post_init__(self) -> None:
        try:
            status = self.status if isinstance(self.status, UserStatus) else UserStatus(self.status)
        except ValueError as exc:
            raise ValueError("unsupported user status") from exc
        object.__setattr__(self, "user_id", _text(self.user_id, "user_id"))
        object.__setattr__(self, "username", _text(self.username, "username").casefold())
        object.__setattr__(self, "status", status)


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    if not isinstance(password, str):
        password = ""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def make_password_credential(password: str, *, salt: bytes) -> PasswordCredential:
    """Create a credential using caller-supplied cryptographic entropy."""

    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must contain at least {MIN_PASSWORD_LENGTH} characters")
    if not isinstance(salt, bytes) or len(salt) < 16:
        raise ValueError("salt must contain at least 16 bytes")
    digest = _derive(password, salt, PBKDF2_ITERATIONS)
    return PasswordCredential(salt.hex(), digest.hex())


def authenticate(user: UserRecord | None, password: str) -> str:
    """Return a user id on success; every other state has one public error."""

    if user is None:
        candidate = _derive(password, _DUMMY_SALT, PBKDF2_ITERATIONS)
        hmac.compare_digest(candidate, _DUMMY_DIGEST)
        raise AuthenticationError()
    candidate = _derive(password, bytes.fromhex(user.credential.salt_hex), user.credential.iterations)
    valid = hmac.compare_digest(candidate, bytes.fromhex(user.credential.digest_hex))
    if not valid or user.status is not UserStatus.ACTIVE:
        raise AuthenticationError()
    return user.user_id
