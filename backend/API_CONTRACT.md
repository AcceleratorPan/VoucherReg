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

## Authentication

### 1) WeChat Login
`POST /auth/wechat/login`

Request:
```json
{
  "code": "wx.login code"
}
```

Response `200`:
```json
{
  "userId": "wx_openid_xxx",
  "accessToken": "v1.xxxxx.yyyyy",
  "tokenType": "Bearer",
  "expiresIn": 86400
}
```

### 2) Bearer Token For Protected APIs
All `/voucher-tasks` APIs require:

`Authorization: Bearer <accessToken>`

No `userId` query parameter is needed anymore. Backend resolves user from token.

## Voucher Workflow APIs

### 3) Create Task
`POST /voucher-tasks`

Request body: none

Response `201`:
```json
{
  "taskId": "vt_xxxxx",
  "userId": "wx_openid_xxx",
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

### 4) Upload Page
`POST /voucher-tasks/{taskId}/pages`

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
  "imageUrl": "/files/wx_openid_xxx/tasks/vt_xxxxx/pages/0.png",
  "thumbUrl": null,
  "isFirstPage": true,
  "width": 1242,
  "height": 1660,
  "createdAt": "2026-03-02T09:01:00Z",
  "updatedAt": "2026-03-02T09:01:00Z"
}
```

### 5) Finish Upload
`POST /voucher-tasks/{taskId}/finish-upload`

Response `200`:
```json
{
  "taskId": "vt_xxxxx",
  "status": "uploaded",
  "pageCount": 3
}
```

### 6) Recognize
`POST /voucher-tasks/{taskId}/recognize`

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

### 7) Confirm And Generate PDF
`POST /voucher-tasks/{taskId}/confirm-generate`

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
  "pdfUrl": "/files/wx_openid_xxx/tasks/vt_123/result/海南百迈科医疗科技股份有限公司-2022-07-记470.pdf"
}
```

### 8) List Tasks
`GET /voucher-tasks?limit=20&offset=0`

Response `200`:
```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 20
}
```

### 9) Get Task Detail
`GET /voucher-tasks/{taskId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "userId": "wx_openid_xxx",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileName": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "pdfUrl": "/files/wx_openid_xxx/tasks/vt_123/result/海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "status": "pdf_generated",
  "pageCount": 3,
  "confidence": 0.93,
  "rawOcrText": "...",
  "pages": []
}
```

### 10) Delete One Task
`DELETE /voucher-tasks/{taskId}`

Response `200`:
```json
{
  "taskId": "vt_123",
  "deleted": true
}
```

### 11) Clear All History For Current User
`DELETE /voucher-tasks`

Response `200`:
```json
{
  "userId": "wx_openid_xxx",
  "deletedCount": 5
}
```

### 12) Health
`GET /health`

Response `200`:
```json
{
  "status": "ok"
}
```

## Error Scenarios (Examples)
- `401 UNAUTHORIZED`: missing/invalid/expired bearer token.
- `400 VALIDATION_ERROR`: invalid state input, missing required fields.
- `400 VALIDATION_ERROR`: non-image upload, invalid first `pageIndex`, oversized upload.
- `404 NOT_FOUND`: task or page not found.
- `409 CONFLICT`: illegal state transition or duplicate `pageIndex`.
- `422 REQUEST_VALIDATION_ERROR`: request schema/form invalid.
- `500 OCR_DEPENDENCY_MISSING`: RapidOCR dependency is not installed in runtime.
- `502 OCR_PROVIDER_ERROR`: RapidOCR execution failed on provider/model side.
- `502 OCR_EMPTY_RESULT`: OCR result returned no text.
- `500 INTERNAL_ERROR`: unhandled server error.
