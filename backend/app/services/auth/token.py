from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.exceptions import UnauthorizedException

TOKEN_VERSION = "v1"
DOWNLOAD_TOKEN_TYPE = "download"


class TokenService:
    def __init__(self, secret_key: str, issuer: str) -> None:
        if not secret_key:
            raise ValueError("auth secret key must not be empty")
        self._secret_key = secret_key.encode("utf-8")
        self._issuer = issuer

    def create_download_token(
        self,
        user_id: str,
        claims: dict[str, Any],
        expires_in_seconds: int,
    ) -> str:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            raise ValueError("user_id must not be empty")
        if expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be > 0")

        now = int(time.time())
        payload = {
            "sub": normalized_user_id,
            "iat": now,
            "exp": now + expires_in_seconds,
            "iss": self._issuer,
            "typ": DOWNLOAD_TOKEN_TYPE,
        }
        payload.update(claims)
        return self._encode_token(payload)

    def verify_download_token(self, token: str) -> dict[str, Any]:
        if not token:
            raise UnauthorizedException(message="Missing download token")

        payload = self._verify_signed_token(token)
        if payload.get("typ") != DOWNLOAD_TOKEN_TYPE:
            raise UnauthorizedException(message="Invalid download token type")

        self._validate_common_claims(payload, expired_message="Download link expired")
        return payload

    def _encode_token(self, payload: dict[str, Any]) -> str:
        payload_segment = self._encode_payload(payload)
        signed_part = f"{TOKEN_VERSION}.{payload_segment}"
        signature_segment = self._sign(signed_part)
        return f"{signed_part}.{signature_segment}"

    def _verify_signed_token(self, token: str) -> dict[str, Any]:
        try:
            version, payload_segment, signature_segment = token.split(".", 2)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid token format") from exc

        if version != TOKEN_VERSION:
            raise UnauthorizedException(message="Unsupported token version")

        signed_part = f"{version}.{payload_segment}"
        expected_signature = self._sign(signed_part)
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise UnauthorizedException(message="Invalid token signature")

        return self._decode_payload(payload_segment)

    def _validate_common_claims(self, payload: dict[str, Any], expired_message: str) -> str:
        subject = payload.get("sub")
        exp = payload.get("exp")
        issuer = payload.get("iss")

        if not isinstance(subject, str) or not subject.strip():
            raise UnauthorizedException(message="Invalid token subject")
        if not isinstance(exp, int):
            raise UnauthorizedException(message="Invalid token expiry")
        if exp < int(time.time()):
            raise UnauthorizedException(message=expired_message)
        if issuer != self._issuer:
            raise UnauthorizedException(message="Invalid token issuer")

        return subject.strip()

    def _sign(self, signed_part: str) -> str:
        digest = hmac.new(self._secret_key, signed_part.encode("utf-8"), hashlib.sha256).digest()
        return self._urlsafe_b64encode(digest)

    @classmethod
    def _encode_payload(cls, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return cls._urlsafe_b64encode(raw)

    @classmethod
    def _decode_payload(cls, payload_segment: str) -> dict[str, Any]:
        try:
            raw = cls._urlsafe_b64decode(payload_segment)
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise UnauthorizedException(message="Invalid token payload") from exc

        if not isinstance(value, dict):
            raise UnauthorizedException(message="Invalid token payload")
        return value

    @staticmethod
    def _urlsafe_b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _urlsafe_b64decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
