const { BASE_URL } = require("../config");

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

function uploadPage({ taskId, filePath, pageIndex, userId, name = "file" }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/voucher-tasks/${taskId}/pages?userId=${userId}`,
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

function createTask(userId) {
  return request({
    url: "/voucher-tasks",
    method: "POST",
    data: { userId },
  });
}

function finishUpload(taskId, userId) {
  return request({
    url: `/voucher-tasks/${taskId}/finish-upload?userId=${userId}`,
    method: "POST",
  });
}

function recognize(taskId, userId) {
  return request({
    url: `/voucher-tasks/${taskId}/recognize?userId=${userId}`,
    method: "POST",
  });
}

function confirmGenerate(taskId, { subject, month, voucherNo }, userId) {
  return request({
    url: `/voucher-tasks/${taskId}/confirm-generate?userId=${userId}`,
    method: "POST",
    data: { subject, month, voucherNo },
  });
}

function getTask(taskId, userId) {
  return request({
    url: `/voucher-tasks/${taskId}?userId=${userId}`,
    method: "GET",
  });
}

function getTasks(userId) {
  return request({
    url: `/voucher-tasks?userId=${userId}`,
    method: "GET",
  });
}

function clearAllTasks(userId) {
  return request({
    url: `/voucher-tasks?userId=${userId}`,
    method: "DELETE",
  });
}

function batchDownload(taskIds, userId) {
  return request({
    url: `/voucher-tasks/batch-download?userId=${userId}`,
    method: "POST",
    data: { taskIds },
  });
}

function getFirstImage(taskId, userId) {
  return request({
    url: `/voucher-tasks/${taskId}/first-image?userId=${userId}`,
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
  getFirstImage
};
