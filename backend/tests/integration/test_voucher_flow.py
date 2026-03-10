from __future__ import annotations

from io import BytesIO
import logging
from urllib.parse import urlparse
from zipfile import ZipFile

from PIL import Image

from app.api.deps import get_ocr_service


def _user_params(user_id: str) -> dict[str, str]:
    return {"userId": user_id}


def _build_rgb_png_bytes(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", size, color=color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _create_generated_task(client, sample_image_bytes: bytes, user_id: str, page_count: int = 2) -> dict:
    create_resp = client.post("/voucher-tasks", json={"userId": user_id})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["taskId"]

    for page_index in range(page_count):
        upload_resp = client.post(
            f"/voucher-tasks/{task_id}/pages",
            params=_user_params(user_id),
            files={"file": (f"page{page_index}.png", sample_image_bytes, "image/png")},
            data={"pageIndex": str(page_index)},
        )
        assert upload_resp.status_code == 200

    finish_resp = client.post(f"/voucher-tasks/{task_id}/finish-upload", params=_user_params(user_id))
    assert finish_resp.status_code == 200

    recognize_resp = client.post(f"/voucher-tasks/{task_id}/recognize", params=_user_params(user_id))
    assert recognize_resp.status_code == 200
    recognize_data = recognize_resp.json()

    confirm_resp = client.post(
        f"/voucher-tasks/{task_id}/confirm-generate",
        params=_user_params(user_id),
        json={
            "subject": recognize_data["subject"],
            "month": recognize_data["month"],
            "voucherNo": recognize_data["voucherNo"],
        },
    )
    assert confirm_resp.status_code == 200

    return {
        "task_id": task_id,
        "recognize": recognize_data,
        "confirm": confirm_resp.json(),
    }


def test_voucher_task_end_to_end_flow(client, sample_image_bytes: bytes) -> None:
    user_id = "user_001"
    created = _create_generated_task(client, sample_image_bytes, user_id=user_id)
    task_id = created["task_id"]
    recognize_data = created["recognize"]
    confirm_data = created["confirm"]

    assert recognize_data["subject"]
    assert recognize_data["month"] == "2022-07"
    assert recognize_data["voucherNo"] == "记470"

    assert confirm_data["status"] == "pdf_generated"
    assert confirm_data["pdfUrl"].startswith("http://testserver/downloads/")

    page_resp = client.get(f"/files/{user_id}/tasks/{task_id}/pages/0.png")
    assert page_resp.status_code == 200

    raw_pdf_resp = client.get(f"/files/{user_id}/tasks/{task_id}/result/{confirm_data['fileName']}")
    assert raw_pdf_resp.status_code == 404

    detail_resp = client.get(f"/voucher-tasks/{task_id}", params=_user_params(user_id))
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["taskId"] == task_id
    assert detail["pageCount"] == 2
    assert len(detail["pages"]) == 2
    assert detail["pdfUrl"].startswith("http://testserver/downloads/")

    list_resp = client.get("/voucher-tasks", params=_user_params(user_id))
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    assert list_resp.json()["items"][0]["pdfUrl"].startswith("http://testserver/downloads/")


def test_single_download_link_returns_pdf_attachment(client, sample_image_bytes: bytes) -> None:
    user_id = "download_user"
    created = _create_generated_task(client, sample_image_bytes, user_id=user_id, page_count=1)
    task_id = created["task_id"]

    link_resp = client.post(f"/voucher-tasks/{task_id}/download-link", params=_user_params(user_id))
    assert link_resp.status_code == 200
    body = link_resp.json()
    assert body["taskId"] == task_id
    assert body["contentType"] == "application/pdf"
    assert body["downloadUrl"].startswith("http://testserver/downloads/")

    download_path = urlparse(body["downloadUrl"]).path
    download_resp = client.get(download_path)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "attachment;" in download_resp.headers["content-disposition"]
    assert download_resp.content.startswith(b"%PDF")


def test_generated_pdf_bytes_follow_uploaded_image_content(client) -> None:
    user_id = "pdf_bytes_user"
    first = _create_generated_task(
        client,
        _build_rgb_png_bytes(size=(600, 900), color=(255, 0, 0)),
        user_id=user_id,
        page_count=1,
    )
    second = _create_generated_task(
        client,
        _build_rgb_png_bytes(size=(600, 900), color=(0, 0, 255)),
        user_id=user_id,
        page_count=1,
    )

    first_resp = client.get(urlparse(first["confirm"]["pdfUrl"]).path)
    second_resp = client.get(urlparse(second["confirm"]["pdfUrl"]).path)

    assert first_resp.status_code == 200
    assert second_resp.status_code == 200
    assert first_resp.content.startswith(b"%PDF")
    assert second_resp.content.startswith(b"%PDF")
    assert first_resp.content != second_resp.content


def test_first_image_endpoint_returns_accessible_image_url(client, sample_image_bytes: bytes) -> None:
    user_id = "preview_user"
    create_resp = client.post("/voucher-tasks", json={"userId": user_id})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        params=_user_params(user_id),
        files={"file": ("page0.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    assert upload_resp.status_code == 200

    first_image_resp = client.get(f"/voucher-tasks/{task_id}/first-image", params=_user_params(user_id))
    assert first_image_resp.status_code == 200
    body = first_image_resp.json()
    assert body["taskId"] == task_id
    assert body["pageIndex"] == 0
    assert body["isFirstPage"] is True
    assert body["imageUrl"].startswith("http://testserver/files/")

    image_path = urlparse(body["imageUrl"]).path
    public_image_resp = client.get(image_path)
    assert public_image_resp.status_code == 200
    assert public_image_resp.headers["content-type"] == "image/png"


def test_recognize_rotates_first_page_until_full_parse_and_persists_result(client, caplog, capsys) -> None:
    class OrientationAwareOCR:
        def __init__(self) -> None:
            self.sizes: list[tuple[int, int]] = []

        async def recognize(self, image_bytes: bytes, image_url: str | None = None) -> str:  # noqa: ARG002
            with Image.open(BytesIO(image_bytes)) as image:
                self.sizes.append(image.size)
                if image.width > image.height:
                    return "核算单位：旋转测试公司\n日期：2024-03-15"
            return "核算单位：旋转测试公司\n日期：2024-03-15\n编号：记 - 77"

    ocr_service = OrientationAwareOCR()
    client.app.dependency_overrides[get_ocr_service] = lambda: ocr_service
    caplog.set_level(logging.INFO, logger="app.services.voucher_task_service")

    try:
        user_id = "rotate_user"
        create_resp = client.post("/voucher-tasks", json={"userId": user_id})
        assert create_resp.status_code == 201
        task_id = create_resp.json()["taskId"]

        image = Image.new("RGB", (1200, 800), color=(255, 255, 255))
        upload_buffer = BytesIO()
        image.save(upload_buffer, format="PNG")

        upload_resp = client.post(
            f"/voucher-tasks/{task_id}/pages",
            params=_user_params(user_id),
            files={"file": ("page0.png", upload_buffer.getvalue(), "image/png")},
            data={"pageIndex": "0"},
        )
        assert upload_resp.status_code == 200

        finish_resp = client.post(f"/voucher-tasks/{task_id}/finish-upload", params=_user_params(user_id))
        assert finish_resp.status_code == 200

        recognize_resp = client.post(f"/voucher-tasks/{task_id}/recognize", params=_user_params(user_id))
        assert recognize_resp.status_code == 200
        recognize_data = recognize_resp.json()

        assert recognize_data["subject"] == "旋转测试公司"
        assert recognize_data["month"] == "2024-03"
        assert recognize_data["voucherNo"] == "记77"
        assert recognize_data["needsUserReview"] is False
        assert ocr_service.sizes == [(1200, 800), (800, 1200)]
        captured = capsys.readouterr()
        assert "[OCR DEBUG] angle=0 raw_text:" in captured.out
        assert "核算单位：旋转测试公司" in captured.out
        assert "OCR attempt angle=0 raw_text:" in caplog.text
        assert "核算单位：旋转测试公司" in caplog.text

        detail_resp = client.get(f"/voucher-tasks/{task_id}", params=_user_params(user_id))
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["pages"][0]["width"] == 800
        assert detail["pages"][0]["height"] == 1200

        image_path = urlparse(detail["pages"][0]["imageUrl"]).path
        rotated_resp = client.get(image_path)
        assert rotated_resp.status_code == 200
        with Image.open(BytesIO(rotated_resp.content)) as rotated_image:
            assert rotated_image.size == (800, 1200)
    finally:
        client.app.dependency_overrides.pop(get_ocr_service, None)


def test_uploaded_page_is_persisted_as_scanned_png(client) -> None:
    user_id = "scanner_user"
    create_resp = client.post("/voucher-tasks", json={"userId": user_id})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["taskId"]

    image = Image.new("RGB", (640, 960), color=(40, 120, 220))
    upload_buffer = BytesIO()
    image.save(upload_buffer, format="JPEG")
    original_bytes = upload_buffer.getvalue()

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        params=_user_params(user_id),
        files={"file": ("page0.jpg", original_bytes, "image/jpeg")},
        data={"pageIndex": "0"},
    )
    assert upload_resp.status_code == 200
    page = upload_resp.json()
    assert page["imageUrl"].endswith("/pages/0.png")

    scanned_path = urlparse(page["imageUrl"]).path
    scanned_resp = client.get(scanned_path)
    assert scanned_resp.status_code == 200
    assert scanned_resp.headers["content-type"] == "image/png"
    assert scanned_resp.content != original_bytes


def test_batch_download_link_returns_zip_attachment(client, sample_image_bytes: bytes) -> None:
    user_id = "batch_user"
    first = _create_generated_task(client, sample_image_bytes, user_id=user_id, page_count=1)
    second = _create_generated_task(client, sample_image_bytes, user_id=user_id, page_count=2)

    link_resp = client.post(
        "/voucher-tasks/batch-download-link",
        params=_user_params(user_id),
        json={"taskIds": [first["task_id"], second["task_id"]]},
    )
    assert link_resp.status_code == 200
    body = link_resp.json()
    assert body["taskIds"] == [first["task_id"], second["task_id"]]
    assert body["contentType"] == "application/zip"
    assert body["downloadUrl"].startswith("http://testserver/downloads/")

    download_path = urlparse(body["downloadUrl"]).path
    download_resp = client.get(download_path)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/zip"
    assert "attachment;" in download_resp.headers["content-disposition"]

    with ZipFile(BytesIO(download_resp.content)) as zip_file:
        names = zip_file.namelist()
        assert len(names) == 2
        assert all(name.endswith(".pdf") for name in names)
        assert all(zip_file.read(name).startswith(b"%PDF") for name in names)


def test_download_route_rejects_invalid_token(client) -> None:
    response = client.get("/downloads/not-a-valid-token")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_first_image_endpoint_is_user_scoped(client, sample_image_bytes: bytes) -> None:
    create_resp = client.post("/voucher-tasks", json={"userId": "owner_user"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        params=_user_params("owner_user"),
        files={"file": ("page0.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    assert upload_resp.status_code == 200

    unauthorized_resp = client.get(f"/voucher-tasks/{task_id}/first-image", params=_user_params("other_user"))
    assert unauthorized_resp.status_code == 404


def test_upload_rejects_missing_user_id(client) -> None:
    create_resp = client.post("/voucher-tasks", json={"userId": "user_missing"})
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        files={"file": ("page0.png", b"abc", "image/png")},
        data={"pageIndex": "0"},
    )

    assert upload_resp.status_code == 400
    body = upload_resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "userId is required"


def test_create_task_rejects_missing_user_id(client) -> None:
    response = client.post("/voucher-tasks")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "userId is required"


def test_upload_rejects_non_image_content_type(client) -> None:
    user_id = "user_002"
    create_resp = client.post("/voucher-tasks", json={"userId": user_id})
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        params=_user_params(user_id),
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"pageIndex": "0"},
    )

    assert upload_resp.status_code == 400
    body = upload_resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "Only image files are supported" in body["message"]


def test_upload_requires_first_page_index_zero(client, sample_image_bytes: bytes) -> None:
    user_id = "user_003"
    create_resp = client.post("/voucher-tasks", json={"userId": user_id})
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        params=_user_params(user_id),
        files={"file": ("page2.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "2"},
    )

    assert upload_resp.status_code == 400
    body = upload_resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "first uploaded page must use pageIndex=0" in body["message"]


def test_user_isolation_and_history_erase(client, sample_image_bytes: bytes) -> None:
    user_a = "user_a"
    user_b = "user_b"

    create_a = client.post("/voucher-tasks", json={"userId": user_a})
    create_b = client.post("/voucher-tasks", json={"userId": user_b})
    assert create_a.status_code == 201
    assert create_b.status_code == 201
    task_a = create_a.json()["taskId"]
    task_b = create_b.json()["taskId"]

    with_open_a = client.post(
        f"/voucher-tasks/{task_a}/pages",
        params=_user_params(user_a),
        files={"file": ("a.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    with_open_b = client.post(
        f"/voucher-tasks/{task_b}/pages",
        params=_user_params(user_b),
        files={"file": ("b.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    assert with_open_a.status_code == 200
    assert with_open_b.status_code == 200

    list_a = client.get("/voucher-tasks", params=_user_params(user_a))
    list_b = client.get("/voucher-tasks", params=_user_params(user_b))
    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert all(item["userId"] == user_a for item in list_a.json()["items"])
    assert all(item["userId"] == user_b for item in list_b.json()["items"])

    unauthorized_detail = client.get(f"/voucher-tasks/{task_a}", params=_user_params(user_b))
    assert unauthorized_detail.status_code == 404

    delete_one = client.delete(f"/voucher-tasks/{task_a}", params=_user_params(user_a))
    assert delete_one.status_code == 200
    assert delete_one.json()["deleted"] is True

    clear_b = client.delete("/voucher-tasks", params=_user_params(user_b))
    assert clear_b.status_code == 200
    assert clear_b.json()["userId"] == user_b
    assert clear_b.json()["deletedCount"] >= 1
