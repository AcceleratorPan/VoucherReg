# WeChat Mini Program Integration README

This document is for the WeChat Mini Program developer integrating with the FastAPI backend in this repository.

## 1. Goal

Implement the voucher workflow in Mini Program:

1. Create voucher task.
2. Upload images in order (`1st image = main voucher page`, others = attachments).
3. Finish upload.
4. Trigger OCR recognition.
5. Let user confirm/edit `subject`, `month`, `voucherNo`.
6. Confirm and generate PDF.
7. Show PDF result and history.
8. Erase single history item or clear all history for current user.

## 2. Backend Base Info

- Base URL (dev): `http://127.0.0.1:8000`
- API prefix: none (already included in paths below)
- Response field style: `camelCase`
- Error envelope:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "error message",
  "detail": {}
}
```

## 3. Required API Sequence

1. `POST /voucher-tasks`
2. `POST /voucher-tasks/{taskId}/pages` (upload all pages)
3. `POST /voucher-tasks/{taskId}/finish-upload`
4. `POST /voucher-tasks/{taskId}/recognize`
5. `POST /voucher-tasks/{taskId}/confirm-generate`
6. Optional reads:
   - `GET /voucher-tasks/{taskId}`
   - `GET /voucher-tasks`
7. Optional erase:
   - `DELETE /voucher-tasks/{taskId}`
   - `DELETE /voucher-tasks`

Do not call `recognize` before `finish-upload`.
Do not call `confirm-generate` before `recognize`.

## 4. API Contract (Mini Program Side)

### 4.1 Create Task

- Endpoint: `POST /voucher-tasks`
- Body:

```json
{
  "userId": "wx_user_123"
}
```

- Use returned `taskId` for all next API calls.
- Use the same `userId` for all next API calls (as query parameter).

### 4.2 Upload Page

- Endpoint: `POST /voucher-tasks/{taskId}/pages?userId={userId}`
- Content type: `multipart/form-data`
- Fields:
  - `file`: image file
  - `pageIndex`: integer string

Rules:

1. First page must be `pageIndex=0`.
2. Upload order should be deterministic (`0,1,2...`).
3. First image is the OCR source.

### 4.3 Finish Upload

- Endpoint: `POST /voucher-tasks/{taskId}/finish-upload?userId={userId}`
- No request body.

### 4.4 Recognize

- Endpoint: `POST /voucher-tasks/{taskId}/recognize?userId={userId}`
- Use response to pre-fill confirmation form:

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

### 4.5 Confirm And Generate

- Endpoint: `POST /voucher-tasks/{taskId}/confirm-generate?userId={userId}`
- Body:

```json
{
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470"
}
```

- Success response includes:
  - `status` (`pdf_generated`)
  - `fileName`
  - `pdfUrl`

## 5. WeChat Mini Request Helpers

Use Promise wrappers for stable async flow.

```javascript
// utils/http.js
const BASE_URL = "http://127.0.0.1:8000";
const q = (userId) => `?userId=${encodeURIComponent(userId)}`;

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

export function uploadPage({ userId, taskId, filePath, pageIndex, name = "file" }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/voucher-tasks/${taskId}/pages${q(userId)}`,
      filePath,
      name,
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
export function clearHistory(userId) {
  return request({
    url: `/voucher-tasks${q(userId)}`,
    method: "DELETE",
  });
}

export function deleteTask(userId, taskId) {
  return request({
    url: `/voucher-tasks/${taskId}${q(userId)}`,
    method: "DELETE",
  });
}
```

## 6. Suggested Integration Flow (Frontend)

```javascript
import { request, uploadPage } from "../../utils/http";

export async function runVoucherFlow({ userId, imagePaths }) {
  const task = await request({
    url: "/voucher-tasks",
    method: "POST",
    data: { userId },
  });

  for (let i = 0; i < imagePaths.length; i += 1) {
    await uploadPage({
      userId,
      taskId: task.taskId,
      filePath: imagePaths[i],
      pageIndex: i,
    });
  }

  await request({
    url: `/voucher-tasks/${task.taskId}/finish-upload?userId=${encodeURIComponent(userId)}`,
    method: "POST",
  });

  const recognized = await request({
    url: `/voucher-tasks/${task.taskId}/recognize?userId=${encodeURIComponent(userId)}`,
    method: "POST",
  });

  // Show recognized fields in manual confirmation page.
  // User can edit subject/month/voucherNo before final submission.
  const confirmed = await request({
    url: `/voucher-tasks/${task.taskId}/confirm-generate?userId=${encodeURIComponent(userId)}`,
    method: "POST",
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

Use backend task status as source of truth:

- `draft`: creating task / uploading pages
- `uploaded`: waiting for recognition
- `recognized`: show confirmation form
- `confirmed`: backend internal transition
- `pdf_generated`: show PDF result
- `failed`: show retry or support flow

## 8. Error Handling Strategy

1. Handle 4xx as user-action errors:
   - invalid upload order
   - duplicate `pageIndex`
   - bad image format
2. Handle 5xx/502 as system errors:
   - OCR runtime issue
   - service dependency/runtime issue
3. Always show backend `message` to user-friendly toast/dialog.
4. Log full `detail` for debugging (dev build).

## 9. File URL Handling

Backend returns relative file URLs like:

- `/files/{userId}/tasks/{taskId}/result/{fileName}.pdf`

Mini Program should build absolute URL:

- `${BASE_URL}${pdfUrl}`

## 10. Partner Checklist

1. Build `http` and `upload` wrappers.
2. Implement strict upload ordering (`pageIndex` from `0`).
3. Implement confirmation page with editable fields.
4. Persist `taskId` in page state/global state.
5. Add retry UI for `recognize` and `confirm-generate` failures.
6. Add history page using `GET /voucher-tasks?userId=...`.
7. Add detail page using `GET /voucher-tasks/{taskId}?userId=...`.
8. Add erase actions using `DELETE /voucher-tasks/{taskId}?userId=...` and `DELETE /voucher-tasks?userId=...`.

## 11. Reference

- Contract details: `API_CONTRACT.md`
- Architecture details: `ARCHITECTURE.md`
- Scope details: `MVP_SCOPE.md`
