from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_wechat_auth_service
from app.schemas.auth import WeChatLoginRequest, WeChatLoginResponse
from app.services.auth import WeChatAuthService

router = APIRouter(prefix="/auth")


@router.post("/wechat/login", response_model=WeChatLoginResponse)
async def wechat_login(
    payload: WeChatLoginRequest,
    auth_service: WeChatAuthService = Depends(get_wechat_auth_service),
) -> WeChatLoginResponse:
    result = await auth_service.login(payload.code)
    return WeChatLoginResponse.model_validate(result)
