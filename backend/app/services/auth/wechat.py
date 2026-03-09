from __future__ import annotations

import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from anyio import to_thread

from app.core.config import Settings
from app.core.exceptions import AppException, ValidationException
from app.services.auth.token import TokenService


class WeChatAuthService:
    def __init__(self, settings: Settings, token_service: TokenService) -> None:
        self.settings = settings
        self.token_service = token_service

    async def login(self, code: str) -> dict:
        normalized_code = code.strip()
        if not normalized_code:
            raise ValidationException(message="WeChat login code is required")

        print(f"Attempting WeChat login with code: {normalized_code}")
        openid = await to_thread.run_sync(self._resolve_openid, normalized_code)
        print(f"Successfully logged in with openid: {openid}")
        access_token = self.token_service.create_access_token(openid)
        print(f"Successfully created access token for access_token: {access_token}")
        return {
            "user_id": openid,
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_service.expires_in_seconds,
        }

    def _resolve_openid(self, code: str) -> str:
        if self.settings.wechat_login_mock_enabled and code.startswith(self.settings.wechat_login_mock_prefix):
            return self._mock_openid(code)
        return self._fetch_openid_from_wechat(code)

    def _fetch_openid_from_wechat(self, code: str) -> str:
        app_id = (self.settings.wechat_app_id or "").strip()
        app_secret = (self.settings.wechat_app_secret or "").strip()
        if not app_id or not app_secret:
            raise AppException(
                status_code=500,
                code="WECHAT_AUTH_NOT_CONFIGURED",
                message="WeChat auth is not configured",
            )

        query = urlencode(
            {
                "appid": app_id,
                "secret": app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            }
        )
        url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"

        try:
            with urlopen(url, timeout=self.settings.wechat_login_timeout_seconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AppException(
                status_code=502,
                code="WECHAT_API_ERROR",
                message="Failed to call WeChat login API",
                detail={"error": str(exc)},
            ) from exc
        except json.JSONDecodeError as exc:
            raise AppException(
                status_code=502,
                code="WECHAT_API_ERROR",
                message="Invalid response from WeChat login API",
                detail={"error": str(exc)},
            ) from exc

        if int(data.get("errcode", 0)) != 0:
            raise AppException(
                status_code=401,
                code="WECHAT_LOGIN_FAILED",
                message="WeChat login failed",
                detail={"errcode": data.get("errcode"), "errmsg": data.get("errmsg")},
            )

        openid = data.get("openid")
        if not isinstance(openid, str) or not openid.strip():
            raise AppException(
                status_code=401,
                code="WECHAT_LOGIN_FAILED",
                message="WeChat login did not return openid",
            )
        return openid.strip()

    @staticmethod
    def _mock_openid(code: str) -> str:
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]
        return f"mock_{digest}"
