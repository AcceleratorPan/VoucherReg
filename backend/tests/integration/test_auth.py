from __future__ import annotations

from app.api.deps import get_wechat_auth_service


def test_protected_endpoints_require_bearer_token(client) -> None:
    response = client.post("/voucher-tasks")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "UNAUTHORIZED"


def test_invalid_bearer_token_is_rejected(client) -> None:
    response = client.post("/voucher-tasks", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "UNAUTHORIZED"


def test_wechat_login_route_returns_token_payload(client) -> None:
    class _FakeWeChatAuthService:
        async def login(self, code: str) -> dict:
            assert code == "test-code"
            return {
                "user_id": "wx_openid_demo",
                "access_token": "token-demo",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

    client.app.dependency_overrides[get_wechat_auth_service] = lambda: _FakeWeChatAuthService()
    try:
        response = client.post("/auth/wechat/login", json={"code": "test-code"})
    finally:
        client.app.dependency_overrides.pop(get_wechat_auth_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == "wx_openid_demo"
    assert body["accessToken"] == "token-demo"
    assert body["tokenType"] == "Bearer"
    assert body["expiresIn"] == 3600
