from __future__ import annotations

from app.schemas.base import APIModel


class WeChatLoginRequest(APIModel):
    code: str


class WeChatLoginResponse(APIModel):
    user_id: str
    access_token: str
    token_type: str
    expires_in: int
