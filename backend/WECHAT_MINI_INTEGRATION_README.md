# WeChat Mini Program Integration README

This document describes the current Mini Program integration contract for this FastAPI backend.

## 1. Identity Model

The backend no longer uses WeChat login or bearer auth.

- Every voucher workflow request is scoped by `userId`.
- `POST /voucher-tasks`: send `userId` in JSON body.
- All other `/voucher-tasks/*` requests: send `userId` as query parameter.
- Frontend should persist one stable local `userId` and reuse it across sessions.

## 2. Required API Sequence

1. `POST /voucher-tasks`
2. `POST /voucher-tasks/{taskId}/pages?userId={userId}`
3. `POST /voucher-tasks/{taskId}/finish-upload?userId={userId}`
4. `POST /voucher-tasks/{taskId}/recognize?userId={userId}`
5. `POST /voucher-tasks/{taskId}/confirm-generate?userId={userId}`
6. Optional reads:
   - `GET /voucher-tasks?userId={userId}`
   - `GET /voucher-tasks/{taskId}?userId={userId}`
   - `GET /voucher-tasks/{taskId}/first-image?userId={userId}`
7. Optional downloads:
   - `POST /voucher-tasks/{taskId}/download-link?userId={userId}`
   - `POST /voucher-tasks/batch-download-link?userId={userId}`
8. Optional erase:
   - `DELETE /voucher-tasks/{taskId}?userId={userId}`
   - `DELETE /voucher-tasks?userId={userId}`

## 3. Request Helpers

```javascript
const BASE_URL = "http://127.0.0.1:8000";

function withUserId(url, userId) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}userId=${encodeURIComponent(userId)}`;
}

function request({ url, method = "GET", data, header = {} }) {
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

function uploadPage({ userId, taskId, filePath, pageIndex, name = "file" }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}${withUserId(`/voucher-tasks/${taskId}/pages`, userId)}`,
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
```

## 4. Download Behavior

- Generated PDFs are not publicly exposed under `/files/.../result/...`.
- API responses return temporary absolute `pdfUrl` values pointing at `/downloads/{token}`.
- Those URLs can be visited directly without `userId`.
- Batch downloads return a temporary zip link built from selected task ids.

## 5. First OCR Image Preview

- Endpoint: `GET /voucher-tasks/{taskId}/first-image?userId={userId}`
- Response contains absolute `imageUrl`.
- Intended for result-page preview when OCR fields are incomplete.

## 6. Error Notes

- Missing `userId`: `400 VALIDATION_ERROR`
- Invalid task ownership: `404 NOT_FOUND`
- Temporary download token invalid/expired: `401 UNAUTHORIZED`
- Illegal workflow step: `409 CONFLICT`
