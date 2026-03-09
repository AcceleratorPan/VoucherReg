from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import UnauthorizedException

TOKEN_VERSION = "v1"


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str


class TokenService:
    def __init__(self, secret_key: str, issuer: str, expires_in_seconds: int) -> None:
        if not secret_key:
            raise ValueError("auth secret key must not be empty")
        self._secret_key = secret_key.encode("utf-8")
        self._issuer = issuer
        self._expires_in_seconds = expires_in_seconds

    @property
    def expires_in_seconds(self) -> int:
        return self._expires_in_seconds

    def create_access_token(self, user_id: str) -> str:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            raise ValueError("user_id must not be empty")

        now = int(time.time())
        payload = {
            "sub": normalized_user_id,
            "iat": now,
            "exp": now + self._expires_in_seconds,
            "iss": self._issuer,
        }
        payload_segment = self._encode_payload(payload)
        signed_part = f"{TOKEN_VERSION}.{payload_segment}"
        signature_segment = self._sign(signed_part)
        return f"{signed_part}.{signature_segment}"

    def verify_access_token(self, token: str) -> AuthenticatedUser:
        if not token:
            raise UnauthorizedException(message="Missing access token")

        try:
            version, payload_segment, signature_segment = token.split(".", 2)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid access token format") from exc

        if version != TOKEN_VERSION:
            raise UnauthorizedException(message="Unsupported access token version")

        signed_part = f"{version}.{payload_segment}"
        expected_signature = self._sign(signed_part)
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise UnauthorizedException(message="Invalid access token signature")

        payload = self._decode_payload(payload_segment)
        subject = payload.get("sub")
        exp = payload.get("exp")
        issuer = payload.get("iss")

        if not isinstance(subject, str) or not subject.strip():
            raise UnauthorizedException(message="Invalid access token subject")
        if not isinstance(exp, int):
            raise UnauthorizedException(message="Invalid access token expiry")
        if exp < int(time.time()):
            raise UnauthorizedException(message="Access token expired")
        if issuer != self._issuer:
            raise UnauthorizedException(message="Invalid access token issuer")

        return AuthenticatedUser(user_id=subject.strip())

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
            raise UnauthorizedException(message="Invalid access token payload") from exc

        if not isinstance(value, dict):
            raise UnauthorizedException(message="Invalid access token payload")
        return value

    @staticmethod
    def _urlsafe_b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _urlsafe_b64decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
