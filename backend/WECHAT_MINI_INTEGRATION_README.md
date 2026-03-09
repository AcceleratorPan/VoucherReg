# WeChat Mini Program Integration README

This document is for the WeChat Mini Program developer integrating with this FastAPI backend.

## 1. Goal

Implement voucher flow:
1. WeChat login and backend token fetch.
2. Create task.
3. Upload ordered images (`1st image = main voucher page`, others are attachments).
4. Finish upload.
5. Trigger OCR recognition.
6. Let user confirm/edit `subject`, `month`, `voucherNo`.
7. Confirm and generate PDF.
8. Show history/detail and support erase operations.

## 2. Backend Base Info

- Base URL (dev): `http://127.0.0.1:8000`
- API prefix: none
- Response field style: `camelCase`
- Protected endpoints: all `/voucher-tasks/*`
- Auth header: `Authorization: Bearer <accessToken>`

Error envelope:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "error message",
  "detail": {}
}
```

## 3. Required API Sequence

1. `wx.login()` -> get code
2. `POST /auth/wechat/login`
3. `POST /voucher-tasks`
4. `POST /voucher-tasks/{taskId}/pages` (upload all pages)
5. `POST /voucher-tasks/{taskId}/finish-upload`
6. `POST /voucher-tasks/{taskId}/recognize`
7. `POST /voucher-tasks/{taskId}/confirm-generate`
8. Optional reads:
   - `GET /voucher-tasks/{taskId}`
   - `GET /voucher-tasks`
9. Optional erase:
   - `DELETE /voucher-tasks/{taskId}`
   - `DELETE /voucher-tasks`

Do not call `recognize` before `finish-upload`.
Do not call `confirm-generate` before `recognize`.

## 4. API Contract (Mini Program Side)

### 4.1 Login And Get Access Token

- Step A: call `wx.login()` and get `code`.
- Step B: call backend `POST /auth/wechat/login`:

```json
{
  "code": "wx-login-code"
}
```

Response:

```json
{
  "userId": "wx_openid_xxx",
  "accessToken": "v1.xxxxx.yyyyy",
  "tokenType": "Bearer",
  "expiresIn": 86400
}
```

- Persist `accessToken` and `userId` in Mini Program storage.
- Add `Authorization` header for every `/voucher-tasks` request.

### 4.2 Create Task

- Endpoint: `POST /voucher-tasks`
- Body: none
- Must include `Authorization` header.

### 4.3 Upload Page

- Endpoint: `POST /voucher-tasks/{taskId}/pages`
- Content type: `multipart/form-data`
- Fields:
  - `file`: image file
  - `pageIndex`: integer string
- Must include `Authorization` header.

Rules:
1. First page must be `pageIndex=0`.
2. Upload order should be deterministic (`0,1,2...`).
3. First image is OCR source.

### 4.4 Finish Upload

- Endpoint: `POST /voucher-tasks/{taskId}/finish-upload`
- No body
- Must include `Authorization` header.

### 4.5 Recognize

- Endpoint: `POST /voucher-tasks/{taskId}/recognize`
- Must include `Authorization` header.

Use response to pre-fill confirmation form:

```json
{
  "taskId": "vt_xxx",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileNamePreview": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "confidence": 0.93,
  "needsUserReview": true
}
```

### 4.6 Confirm And Generate

- Endpoint: `POST /voucher-tasks/{taskId}/confirm-generate`
- Must include `Authorization` header.
- Body:

```json
{
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470"
}
```

Success response includes `status`, `fileName`, `pdfUrl`.

## 5. WeChat Mini Request Helpers

```javascript
// utils/http.js
const BASE_URL = "http://127.0.0.1:8000";

export function request({ url, method = "GET", data, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: { "Content-Type": "application/json", ...header },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data);
        reject(res.data || { code: "HTTP_ERROR", message: `HTTP ${res.statusCode}` });
      },
      fail: reject,
    });
  });
}

export async function loginByWeChat() {
  const wxLoginRes = await new Promise((resolve, reject) => {
    wx.login({ success: resolve, fail: reject });
  });
  const auth = await request({
    url: "/auth/wechat/login",
    method: "POST",
    data: { code: wxLoginRes.code },
  });
  wx.setStorageSync("accessToken", auth.accessToken);
  wx.setStorageSync("userId", auth.userId);
  return auth;
}

export function buildAuthHeader() {
  const token = wx.getStorageSync("accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function uploadPage({ taskId, filePath, pageIndex, name = "file" }) {
  const token = wx.getStorageSync("accessToken");
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/voucher-tasks/${taskId}/pages`,
      filePath,
      name,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      formData: { pageIndex: String(pageIndex) },
      success: (res) => {
        const data = JSON.parse(res.data || "{}");
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(data);
        reject(data || { code: "UPLOAD_ERROR", message: `HTTP ${res.statusCode}` });
      },
      fail: reject,
    });
  });
}

export function deleteTask(taskId) {
  return request({
    url: `/voucher-tasks/${taskId}`,
    method: "DELETE",
    header: buildAuthHeader(),
  });
}

export function clearHistory() {
  return request({
    url: "/voucher-tasks",
    method: "DELETE",
    header: buildAuthHeader(),
  });
}
```

## 6. Suggested Integration Flow

```javascript
import { buildAuthHeader, request, uploadPage } from "../../utils/http";

export async function runVoucherFlow({ imagePaths }) {
  const headers = buildAuthHeader();

  const task = await request({
    url: "/voucher-tasks",
    method: "POST",
    header: headers,
  });

  for (let i = 0; i < imagePaths.length; i += 1) {
    await uploadPage({
      taskId: task.taskId,
      filePath: imagePaths[i],
      pageIndex: i,
    });
  }

  await request({
    url: `/voucher-tasks/${task.taskId}/finish-upload`,
    method: "POST",
    header: headers,
  });

  const recognized = await request({
    url: `/voucher-tasks/${task.taskId}/recognize`,
    method: "POST",
    header: headers,
  });

  const confirmed = await request({
    url: `/voucher-tasks/${task.taskId}/confirm-generate`,
    method: "POST",
    header: headers,
    data: {
      subject: recognized.subject,
      month: recognized.month,
      voucherNo: recognized.voucherNo,
    },
  });

  return { task, recognized, confirmed };
}
```

## 7. UI State Mapping

- `draft`: creating task / uploading pages
- `uploaded`: waiting for recognition
- `recognized`: show confirmation form
- `confirmed`: backend internal transition
- `pdf_generated`: show PDF result
- `failed`: show retry or support flow

## 8. Error Handling Strategy

1. Handle `401` by re-login (`wx.login` + `/auth/wechat/login`) and retry once.
2. Handle `4xx` as user-action errors:
   - invalid upload order
   - duplicate `pageIndex`
   - bad image format
3. Handle `5xx/502` as system errors:
   - OCR runtime issue
   - external dependency issue
4. Show backend `message` in toast/dialog.
5. Log `detail` in dev mode.

## 9. File URL Handling

Backend returns relative file URLs like:

- `/files/{userId}/tasks/{taskId}/result/{fileName}.pdf`

Mini Program should build absolute URL:

- `${BASE_URL}${pdfUrl}`

## 10. Partner Checklist

1. Add login bootstrap (`wx.login` + `/auth/wechat/login`).
2. Persist and refresh `accessToken`.
3. Add global auth header helper.
4. Build request/upload wrappers with auth header.
5. Implement strict upload ordering (`pageIndex` from `0`).
6. Implement confirmation page with editable fields.
7. Add history page via `GET /voucher-tasks`.
8. Add detail page via `GET /voucher-tasks/{taskId}`.
9. Add erase actions via `DELETE /voucher-tasks/{taskId}` and `DELETE /voucher-tasks`.

## 11. Reference

- Contract: `API_CONTRACT.md`
- Architecture: `ARCHITECTURE.md`
- Scope: `MVP_SCOPE.md`
