const { BASE_URL } = require("../config");
const { ensureLocalUserId } = require("./user");

function withUserId(url, userId = ensureLocalUserId()) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}userId=${encodeURIComponent(userId)}`;
}

function sendRequest({ url, method = "GET", data, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: { "Content-Type": "application/json", ...header },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        reject(res.data || { code: "HTTP_ERROR", message: `HTTP ${res.statusCode}` });
      },
      fail: reject,
    });
  });
}

function request({ url, method = "GET", data, header = {}, withUser = true }) {
  return sendRequest({
    url: withUser ? withUserId(url) : url,
    method,
    data,
    header,
  });
}

function uploadPage({ taskId, filePath, pageIndex, name = "file" }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}${withUserId(`/voucher-tasks/${taskId}/pages`)}`,
      filePath,
      name,
      formData: { pageIndex: String(pageIndex) },
      success: (res) => {
        const data = JSON.parse(res.data || "{}");
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
          return;
        }
        reject(data || { code: "UPLOAD_ERROR", message: `HTTP ${res.statusCode}` });
      },
      fail: reject,
    });
  });
}

function createTask() {
  return sendRequest({
    url: "/voucher-tasks",
    method: "POST",
    data: { userId: ensureLocalUserId() },
  });
}

function finishUpload(taskId) {
  return request({
    url: `/voucher-tasks/${taskId}/finish-upload`,
    method: "POST",
  });
}

function recognize(taskId) {
  return request({
    url: `/voucher-tasks/${taskId}/recognize`,
    method: "POST",
  });
}

function confirmGenerate(taskId, { subject, month, voucherNo }) {
  return request({
    url: `/voucher-tasks/${taskId}/confirm-generate`,
    method: "POST",
    data: { subject, month, voucherNo },
  });
}

function getTask(taskId) {
  return request({
    url: `/voucher-tasks/${taskId}`,
    method: "GET",
  });
}

function getTasks({ limit = 100, offset = 0 } = {}) {
  return request({
    url: `/voucher-tasks?limit=${limit}&offset=${offset}`,
    method: "GET",
  });
}

function clearAllTasks() {
  return request({
    url: "/voucher-tasks",
    method: "DELETE",
  });
}

function batchDownload(taskIds) {
  return request({
    url: "/voucher-tasks/batch-download-link",
    method: "POST",
    data: { taskIds },
  });
}

function getFirstImage(taskId) {
  return request({
    url: `/voucher-tasks/${taskId}/first-image`,
    method: "GET",
  });
}

module.exports = {
  request,
  uploadPage,
  createTask,
  finishUpload,
  recognize,
  confirmGenerate,
  getTask,
  getTasks,
  clearAllTasks,
  batchDownload,
  getFirstImage,
};
