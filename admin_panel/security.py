from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover - dev fallback when optional dependency is absent
    bcrypt = None


SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
BUILD_ACCESS_MAX_AGE_SECONDS = 60 * 20


def hash_password(password: str) -> str:
    if bcrypt is not None:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return "bcrypt$" + hashed.decode("utf-8")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 240_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("bcrypt$") and bcrypt is not None:
        expected = stored_hash.removeprefix("bcrypt$").encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), expected)

    if stored_hash.startswith("pbkdf2$"):
        try:
            _, salt, digest = stored_hash.split("$", 2)
        except ValueError:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 240_000)
        return hmac.compare_digest(actual.hex(), digest)

    return False


def create_session_token(username: str, secret: str, *, now: int | None = None) -> str:
    issued_at = int(now or time.time())
    payload = f"{username}:{issued_at}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def verify_session_token(token: str, secret: str, *, now: int | None = None) -> str:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, issued_at_text, signature = decoded.rsplit(":", 2)
        issued_at = int(issued_at_text)
    except Exception:
        return ""

    payload = f"{username}:{issued_at}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return ""
    if int(now or time.time()) - issued_at > SESSION_MAX_AGE_SECONDS:
        return ""
    return username


def create_build_access_token(project: str, build_id: str, secret: str, *, now: int | None = None) -> str:
    expires_at = int(now or time.time()) + BUILD_ACCESS_MAX_AGE_SECONDS
    payload = f"{project}:{build_id}:{expires_at}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def verify_build_access_token(
    token: str,
    project: str,
    build_id: str,
    secret: str,
    *,
    now: int | None = None,
) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        token_project, token_build_id, expires_at_text, signature = decoded.rsplit(":", 3)
        expires_at = int(expires_at_text)
    except Exception:
        return False

    if token_project != project or token_build_id != build_id:
        return False
    if int(now or time.time()) > expires_at:
        return False

    payload = f"{token_project}:{token_build_id}:{expires_at}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def generate_password(length: int = 18) -> str:
    return secrets.token_urlsafe(length)
