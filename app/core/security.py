import binascii
import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return (
        f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}$"
        f"{_b64url_encode(salt)}${_b64url_encode(derived_key)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected_hash = password_hash.split("$")
        if algorithm != "scrypt":
            return False

        computed_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64url_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=_SCRYPT_DKLEN,
        )
        return hmac.compare_digest(
            computed_hash,
            _b64url_decode(expected_hash),
        )
    except (TypeError, ValueError):
        return False


def _create_token(
    subject: str,
    token_type: str,
    secret_key: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    expire_at = now + expires_delta

    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
    }

    encoded_header = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_payload = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject=subject,
        token_type="access",
        secret_key=settings.jwt_secret_key,
        expires_delta=expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject=subject,
        token_type="refresh",
        secret_key=settings.jwt_refresh_secret_key,
        expires_delta=expires_delta or timedelta(days=settings.refresh_token_expire_days),
    )


def _decode_token(token: str, secret_key: str, expected_type: str) -> dict:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        signature = _b64url_decode(encoded_signature)
        header = json.loads(_b64url_decode(encoded_header))
        payload = json.loads(_b64url_decode(encoded_payload))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid token payload") from exc

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid token signature")

    if header.get("alg") != settings.jwt_algorithm or header.get("typ") != "JWT":
        raise ValueError("Invalid token header")

    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise ValueError("Token is missing a valid exp claim")

    if exp < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token has expired")

    return payload


def decode_access_token(token: str) -> dict:
    return _decode_token(
        token=token,
        secret_key=settings.jwt_secret_key,
        expected_type="access",
    )


def decode_refresh_token(token: str) -> dict:
    return _decode_token(
        token=token,
        secret_key=settings.jwt_refresh_secret_key,
        expected_type="refresh",
    )
