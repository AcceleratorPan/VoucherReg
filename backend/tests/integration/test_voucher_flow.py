def test_voucher_task_end_to_end_flow(client, sample_image_bytes: bytes, auth_headers) -> None:
    user_id = "user_001"
    headers = auth_headers(user_id)
    create_resp = client.post("/voucher-tasks", headers=headers)
    assert create_resp.status_code == 201
    task_id = create_resp.json()["taskId"]

    upload_first = client.post(
        f"/voucher-tasks/{task_id}/pages",
        headers=headers,
        files={"file": ("page0.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    assert upload_first.status_code == 200
    assert upload_first.json()["isFirstPage"] is True

    upload_second = client.post(
        f"/voucher-tasks/{task_id}/pages",
        headers=headers,
        files={"file": ("page1.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "1"},
    )
    assert upload_second.status_code == 200

    finish_resp = client.post(f"/voucher-tasks/{task_id}/finish-upload", headers=headers)
    assert finish_resp.status_code == 200
    assert finish_resp.json()["status"] == "uploaded"
    assert finish_resp.json()["pageCount"] == 2

    recognize_resp = client.post(f"/voucher-tasks/{task_id}/recognize", headers=headers)
    assert recognize_resp.status_code == 200
    recognize_data = recognize_resp.json()
    assert recognize_data["subject"]
    assert recognize_data["month"] == "2022-07"
    assert recognize_data["voucherNo"] == "记470"

    confirm_resp = client.post(
        f"/voucher-tasks/{task_id}/confirm-generate",
        headers=headers,
        json={
            "subject": recognize_data["subject"],
            "month": recognize_data["month"],
            "voucherNo": recognize_data["voucherNo"],
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "pdf_generated"
    assert confirm_resp.json()["pdfUrl"].startswith("/files/")
    assert f"/{user_id}/tasks/{task_id}/" in confirm_resp.json()["pdfUrl"]

    detail_resp = client.get(f"/voucher-tasks/{task_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["taskId"] == task_id
    assert detail["pageCount"] == 2
    assert len(detail["pages"]) == 2

    list_resp = client.get("/voucher-tasks", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


def test_upload_rejects_non_image_content_type(client, auth_headers) -> None:
    user_id = "user_002"
    headers = auth_headers(user_id)
    create_resp = client.post("/voucher-tasks", headers=headers)
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        headers=headers,
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"pageIndex": "0"},
    )

    assert upload_resp.status_code == 400
    body = upload_resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "Only image files are supported" in body["message"]


def test_upload_requires_first_page_index_zero(client, sample_image_bytes: bytes, auth_headers) -> None:
    user_id = "user_003"
    headers = auth_headers(user_id)
    create_resp = client.post("/voucher-tasks", headers=headers)
    task_id = create_resp.json()["taskId"]

    upload_resp = client.post(
        f"/voucher-tasks/{task_id}/pages",
        headers=headers,
        files={"file": ("page2.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "2"},
    )

    assert upload_resp.status_code == 400
    body = upload_resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "first uploaded page must use pageIndex=0" in body["message"]


def test_user_isolation_and_history_erase(client, sample_image_bytes: bytes, auth_headers) -> None:
    user_a = "user_a"
    user_b = "user_b"
    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    create_a = client.post("/voucher-tasks", headers=headers_a)
    create_b = client.post("/voucher-tasks", headers=headers_b)
    assert create_a.status_code == 201
    assert create_b.status_code == 201
    task_a = create_a.json()["taskId"]
    task_b = create_b.json()["taskId"]

    with_open_a = client.post(
        f"/voucher-tasks/{task_a}/pages",
        headers=headers_a,
        files={"file": ("a.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    with_open_b = client.post(
        f"/voucher-tasks/{task_b}/pages",
        headers=headers_b,
        files={"file": ("b.png", sample_image_bytes, "image/png")},
        data={"pageIndex": "0"},
    )
    assert with_open_a.status_code == 200
    assert with_open_b.status_code == 200

    list_a = client.get("/voucher-tasks", headers=headers_a)
    list_b = client.get("/voucher-tasks", headers=headers_b)
    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert all(item["userId"] == user_a for item in list_a.json()["items"])
    assert all(item["userId"] == user_b for item in list_b.json()["items"])

    unauthorized_detail = client.get(f"/voucher-tasks/{task_a}", headers=headers_b)
    assert unauthorized_detail.status_code == 404

    delete_one = client.delete(f"/voucher-tasks/{task_a}", headers=headers_a)
    assert delete_one.status_code == 200
    assert delete_one.json()["deleted"] is True

    clear_b = client.delete("/voucher-tasks", headers=headers_b)
    assert clear_b.status_code == 200
    assert clear_b.json()["userId"] == user_b
    assert clear_b.json()["deletedCount"] >= 1
