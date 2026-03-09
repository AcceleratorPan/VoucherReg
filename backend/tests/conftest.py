from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_ocr_service, get_storage_service, get_token_service
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.services.auth.token import TokenService
from app.services.ocr.mock import MockOCRService
from app.services.storage.local import LocalStorageService


@pytest.fixture
def sample_image_bytes() -> bytes:
    image = Image.new("RGB", (800, 1200), color=(255, 255, 255))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def token_service() -> TokenService:
    return TokenService(secret_key="test-secret-key", issuer="voucher-backend")


@pytest.fixture
def client(tmp_path: Path, token_service: TokenService) -> TestClient:
    app = create_app()

    test_db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = lambda: LocalStorageService(tmp_path / "storage")
    app.dependency_overrides[get_ocr_service] = lambda: MockOCRService()
    app.dependency_overrides[get_token_service] = lambda: token_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
