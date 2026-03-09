# API Contract

Base URL: `http://localhost:8000`

## Conventions
- JSON fields use camelCase.
- Error envelope:
```json
{
  "code": "OCR_FAILED",
  "message": "OCR recognition failed",
  "detail": {}
}
```

## Identity

All `/voucher-tasks` APIs require explicit `userId`.

- `POST /voucher-tasks`: send `userId` in JSON body.
- All other `/voucher-tasks` APIs: send `userId` as query parameter.

Example:

`GET /voucher-tasks?userId=user_001&limit=20&offset=0`

## Voucher Workflow APIs

### 1) Create Task
`POST /voucher-tasks`

Request:
```json
{
  "userId": "user_001"
}
```

Response `201`:
```json
{
  "taskId": "vt_xxxxx",
  "userId": "user_001",
  "subject": null,
  "month": null,
  "voucherNo": null,
  "fileName": null,
  "pdfUrl": null,
  "status": "draft",
  "pageCount": 0,
  "confidence": null,
  "createdAt": "2026-03-02T09:00:00Z",
  "updatedAt": "2026-03-02T09:00:00Z"
}
```

### 2) Upload Page
`POST /voucher-tasks/{taskId}/pages?userId={userId}`

Content-Type: `multipart/form-data`
- `file`: binary image
- `pageIndex`: integer (optional; server auto-assigns next index if missing)

Validation rules:
- `file` must be an image MIME type (`image/*`).
- Upload must be non-empty and decodable as an image.
- First upload for a task must use `pageIndex=0` (or omit `pageIndex` and let server assign 0).

Response `200`:
```json
{
  "pageId": "vp_xxxxx",
  "taskId": "vt_xxxxx",
  "pageIndex": 0,
  "imageUrl": "/files/user_001/tasks/vt_xxxxx/pages/0.png",
  "thumbUrl": null,
  "isFirstPage": true,
  "width": 1242,
  "height": 1660,
  "createdAt": "2026-03-02T09:01:00Z",
  "updatedAt": "2026-03-02T09:01:00Z"
}
```

### 2A) Get First Uploaded Image
`GET /voucher-tasks/{taskId}/first-image?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_xxxxx",
  "pageId": "vp_xxxxx",
  "pageIndex": 0,
  "imageUrl": "http://localhost:8000/files/user_001/tasks/vt_xxxxx/pages/0.png",
  "thumbUrl": null,
  "isFirstPage": true
}
```

Behavior:
- Returns the first uploaded page for the current user’s task.
- `imageUrl` is an absolute URL so the frontend can preview it directly.
- If the task exists but has no uploaded page yet, backend returns `400 VALIDATION_ERROR`.

### 3) Finish Upload
`POST /voucher-tasks/{taskId}/finish-upload?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_xxxxx",
  "status": "uploaded",
  "pageCount": 3
}
```

### 4) Recognize
`POST /voucher-tasks/{taskId}/recognize?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileNamePreview": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "confidence": 0.93,
  "needsUserReview": true
}
```

### 5) Confirm And Generate PDF
`POST /voucher-tasks/{taskId}/confirm-generate?userId={userId}`

Request:
```json
{
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470"
}
```

Response `200`:
```json
{
  "taskId": "vt_123",
  "status": "pdf_generated",
  "fileName": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "pdfUrl": "http://localhost:8000/downloads/v1.xxxxx.yyyyy"
}
```

Notes:
- `pdfUrl` is now a temporary download URL, not a raw storage path.
- The underlying generated PDF is no longer exposed via `/files/.../result/...`.

### 6) Create Temporary Single-PDF Download Link
`POST /voucher-tasks/{taskId}/download-link?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "fileName": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "contentType": "application/pdf",
  "downloadUrl": "http://localhost:8000/downloads/v1.xxxxx.yyyyy",
  "expiresAt": "2026-03-09T10:30:00Z"
}
```

Behavior:
- Only allowed after task status becomes `pdf_generated`.
- Returned `downloadUrl` is temporary and can be visited directly without `userId`.
- The download response is served as an attachment.

### 7) Create Temporary Batch-Zip Download Link
`POST /voucher-tasks/batch-download-link?userId={userId}`

Request:
```json
{
  "taskIds": ["vt_123", "vt_456"]
}
```

Response `200`:
```json
{
  "taskIds": ["vt_123", "vt_456"],
  "fileName": "voucher-pdfs-20260309100000.zip",
  "contentType": "application/zip",
  "downloadUrl": "http://localhost:8000/downloads/v1.xxxxx.yyyyy",
  "expiresAt": "2026-03-09T10:30:00Z"
}
```

Behavior:
- Only `pdf_generated` tasks owned by the current user are allowed.
- The zip file is assembled on demand when the temporary URL is visited.
- Duplicate `taskIds` are de-duplicated in request order.
- Maximum task count is controlled by `BATCH_DOWNLOAD_MAX_TASKS`.

### 8) Consume Temporary Download Link
`GET /downloads/{downloadToken}`

Response `200`:
- Binary file download.
- `Content-Type` is `application/pdf` for a single voucher and `application/zip` for a batch download.
- `Content-Disposition` is `attachment`.

This endpoint does not require `userId` because the temporary token in the URL is the authorization.

### 9) List Tasks
`GET /voucher-tasks?userId={userId}&limit=20&offset=0`

Response `200`:
```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 20
}
```

### 10) Get Task Detail
`GET /voucher-tasks/{taskId}?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "userId": "user_001",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileName": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "pdfUrl": "http://localhost:8000/downloads/v1.xxxxx.yyyyy",
  "status": "pdf_generated",
  "pageCount": 3,
  "confidence": 0.93,
  "rawOcrText": "...",
  "pages": []
}
```

### 11) Delete One Task
`DELETE /voucher-tasks/{taskId}?userId={userId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "deleted": true
}
```

### 12) Clear All History For Current User
`DELETE /voucher-tasks?userId={userId}`

Response `200`:
```json
{
  "userId": "user_001",
  "deletedCount": 5
}
```

### 13) Health
`GET /health`

Response `200`:
```json
{
  "status": "ok"
}
```

## Error Scenarios (Examples)
- `401 UNAUTHORIZED`: invalid/expired temporary download token.
- `400 VALIDATION_ERROR`: invalid state input, missing required fields.
- `400 VALIDATION_ERROR`: missing `userId`.
- `400 VALIDATION_ERROR`: non-image upload, invalid first `pageIndex`, oversized upload.
- `400 VALIDATION_ERROR`: unsupported temporary download payload.
- `404 NOT_FOUND`: task or page not found.
- `409 CONFLICT`: illegal state transition or duplicate `pageIndex`.
- `409 CONFLICT`: requested download for task without generated PDF.
- `422 REQUEST_VALIDATION_ERROR`: request schema/form invalid.
- `500 OCR_DEPENDENCY_MISSING`: RapidOCR dependency is not installed in runtime.
- `502 OCR_PROVIDER_ERROR`: RapidOCR execution failed on provider/model side.
- `502 OCR_EMPTY_RESULT`: OCR result returned no text.
- `500 INTERNAL_ERROR`: unhandled server error.
