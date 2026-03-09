const PENDING_RESULT_TASK_IDS_KEY = "pendingResultTaskIds";
const ACTIVE_RESULT_TASK_IDS_KEY = "activeResultTaskIds";
const SELECTED_DOWNLOAD_TASKS_KEY = "selectedTasksForDownload";

function uniqueTaskIds(taskIds) {
  return [...new Set((taskIds || []).filter((taskId) => typeof taskId === "string" && taskId))];
}

function getPendingResultTaskIds() {
  return uniqueTaskIds(wx.getStorageSync(PENDING_RESULT_TASK_IDS_KEY) || []);
}

function addPendingResultTaskId(taskId) {
  const taskIds = getPendingResultTaskIds();
  if (!taskIds.includes(taskId)) {
    taskIds.push(taskId);
    wx.setStorageSync(PENDING_RESULT_TASK_IDS_KEY, taskIds);
  }
  return taskIds;
}

function getPendingResultCount() {
  return getPendingResultTaskIds().length;
}

function getActiveResultTaskIds() {
  return uniqueTaskIds(wx.getStorageSync(ACTIVE_RESULT_TASK_IDS_KEY) || []);
}

function startResultSession() {
  const activeTaskIds = getActiveResultTaskIds();
  if (activeTaskIds.length > 0) {
    return activeTaskIds;
  }

  const pendingTaskIds = getPendingResultTaskIds();
  wx.setStorageSync(ACTIVE_RESULT_TASK_IDS_KEY, pendingTaskIds);
  wx.removeStorageSync(PENDING_RESULT_TASK_IDS_KEY);
  return pendingTaskIds;
}

function clearResultSession() {
  wx.removeStorageSync(ACTIVE_RESULT_TASK_IDS_KEY);
}

function setSelectedDownloadTasks(tasks) {
  wx.setStorageSync(SELECTED_DOWNLOAD_TASKS_KEY, tasks || []);
}

function getSelectedDownloadTasks() {
  return wx.getStorageSync(SELECTED_DOWNLOAD_TASKS_KEY) || [];
}

function clearSelectedDownloadTasks() {
  wx.removeStorageSync(SELECTED_DOWNLOAD_TASKS_KEY);
}

function clearAllResultState() {
  wx.removeStorageSync(PENDING_RESULT_TASK_IDS_KEY);
  clearResultSession();
  clearSelectedDownloadTasks();
}

module.exports = {
  addPendingResultTaskId,
  getPendingResultTaskIds,
  getPendingResultCount,
  getActiveResultTaskIds,
  startResultSession,
  clearResultSession,
  setSelectedDownloadTasks,
  getSelectedDownloadTasks,
  clearSelectedDownloadTasks,
  clearAllResultState,
};
