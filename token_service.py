import base64
import hashlib
import hmac
import json
import secrets
import time


def _urlsafe_encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign_payload(payload, secret_key):
    if not secret_key:
        raise ValueError("A secret key is required.")

    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_encoded = _urlsafe_encode(payload_json)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_encoded}.{_urlsafe_encode(signature)}"


def _verify_signed_payload(token, secret_key, expected_action, now=None):
    if (
        not isinstance(token, str)
        or not isinstance(secret_key, str)
        or not token
        or not secret_key
        or token.count(".") != 1
    ):
        return None

    try:
        payload_encoded, signature_encoded = token.split(".", 1)
        supplied_signature = _urlsafe_decode(signature_encoded)
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            payload_encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None

        payload = json.loads(_urlsafe_decode(payload_encoded).decode("utf-8"))
        expires_at = int(payload["exp"])
        current_time = int(time.time() if now is None else now)
        if current_time >= expires_at:
            return None
        if payload.get("action") != expected_action:
            return None
        return payload
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def generate_auth_token(user_id, secret_key, expires_in=3600, now=None):
    issued_at = int(time.time() if now is None else now)
    return _sign_payload(
        {
            "action": "authenticate",
            "exp": issued_at + int(expires_in),
            "user_id": int(user_id),
        },
        secret_key,
    )


def verify_auth_token(token, secret_key, now=None):
    payload = _verify_signed_payload(token, secret_key, "authenticate", now=now)
    if payload is None or not isinstance(payload.get("user_id"), int):
        return None
    return payload


def generate_recovery_token(user_id, secret_key, expires_in=900, now=None):
    issued_at = int(time.time() if now is None else now)
    return _sign_payload(
        {
            "action": "password_recovery",
            "exp": issued_at + int(expires_in),
            "nonce": secrets.token_urlsafe(16),
            "user_id": int(user_id),
        },
        secret_key,
    )


def verify_recovery_token(token, secret_key, now=None):
    payload = _verify_signed_payload(token, secret_key, "password_recovery", now=now)
    if payload is None or not isinstance(payload.get("user_id"), int):
        return None
    if not isinstance(payload.get("nonce"), str) or not payload["nonce"]:
        return None
    return payload


def hash_token(token):
    if not isinstance(token, str) or not token:
        raise ValueError("A token is required.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches_hash(token, expected_hash):
    if not token or not expected_hash:
        return False
    return hmac.compare_digest(hash_token(token), expected_hash)
