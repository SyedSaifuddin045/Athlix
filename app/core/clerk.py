import json
import logging
import time as time_module

import jwt
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None

# Allow up to 30 seconds of clock skew between server and Clerk
JWT_LEEWAY_SECONDS = 30


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.clerk_jwks_url,
            cache_keys=True,
            max_cached_keys=5,
        )
    return _jwks_client


def verify_clerk_token(token: str) -> dict:
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except Exception as exc:
        logger.error("JWKS key fetch failed: %s", exc)
        raise

    server_now = int(time_module.time())

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
            leeway=JWT_LEEWAY_SECONDS,
        )
    except jwt.ExpiredSignatureError:
        # Log diagnostic info before re-raising
        try:
            header = jwt.get_unverified_header(token)
            body = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
            exp_claim = body.get("exp", "missing")
            iat_claim = body.get("iat", "missing")
            logger.error(
                "JWT expired. server_time=%d exp=%s iat=%s exp_diff=%s kid=%s sub=%s",
                server_now,
                exp_claim,
                iat_claim,
                exp_claim - server_now if isinstance(exp_claim, int) else "N/A",
                header.get("kid", "missing"),
                body.get("sub", "missing"),
            )
        except Exception as log_err:
            logger.error("JWT expired (could not decode claims for diagnostics): %s", log_err)
        raise
    except Exception as exc:
        logger.error("JWT decode failed: %s", exc)
        raise

    logger.info("Clerk token verified: sub=%s", payload.get("sub"))
    return payload


def verify_clerk_webhook(payload: bytes, svix_signature: str) -> dict:
    import hashlib
    import hmac

    parts = {}
    for part in svix_signature.split(","):
        kv = part.split("=", 1)
        if len(kv) == 2:
            parts[kv[0].strip()] = kv[1].strip()

    expected_sig = parts.get("v1", "")
    secret = settings.clerk_secret_key.encode("utf-8")
    to_sign = f"{parts.get('ts', '')}.{payload.decode('utf-8')}".encode("utf-8")
    computed = hmac.new(secret, to_sign, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, expected_sig):
        raise ValueError("Invalid webhook signature")

    return json.loads(payload)
