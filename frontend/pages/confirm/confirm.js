const { batchDownload, confirmGenerate, getFirstImage, getTasks } = require("../../utils/http");
const {
  clearAllResultState,
  clearResultSession,
  getActiveResultTaskIds,
  startResultSession,
} = require("../../utils/result-session");

const POLL_INTERVAL_MS = 2500;

Page({
  data: {
    taskList: [],
    sessionTaskIds: [],
    loading: false,
    refreshing: false,
    selectionMode: false,
    selectedTasks: [],
    selectedCount: 0,
    processingCount: 0,
    readyCount: 0,
    generatedCount: 0,
    manualFillCount: 0,
    emptyState: false,
  },

  onLoad() {
    this.taskEdits = {};
    this.selectedTaskState = {};
    this.pollTimer = null;
    const sessionTaskIds = startResultSession();
    this.setData({ sessionTaskIds });
    this.loadTaskBatch(true);
  },

  onShow() {
    if (!this.data.sessionTaskIds.length) {
      const sessionTaskIds = getActiveResultTaskIds();
      if (sessionTaskIds.length) {
        this.setData({ sessionTaskIds });
      }
    }
    this.loadTaskBatch();
    this.startPolling();
  },

  onHide() {
    this.stopPolling();
  },

  onUnload() {
    this.stopPolling();
  },

  onPullDownRefresh() {
    this.loadTaskBatch(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadTaskBatch(showRefreshing = false) {
    const sessionTaskIds = this.data.sessionTaskIds.length ? this.data.sessionTaskIds : startResultSession();
    if (!sessionTaskIds.length) {
      this.selectedTaskState = {};
      this.setData({
        taskList: [],
        emptyState: true,
        refreshing: false,
        selectionMode: false,
        processingCount: 0,
        readyCount: 0,
        generatedCount: 0,
        manualFillCount: 0,
        selectedTasks: [],
        selectedCount: 0,
      });
      this.stopPolling();
      return;
    }

    if (showRefreshing) {
      this.setData({ refreshing: true });
    }

    try {
      const result = await getTasks({ limit: 100, offset: 0 });
      const items = result.items || [];
      const taskMap = new Map(items.map((item) => [item.taskId, item]));
      const taskList = sessionTaskIds.map((taskId, index) => this.normalizeTask(taskMap.get(taskId), taskId, index));
      const { processingCount } = this.setTaskListState(taskList, { refreshing: false });

      if (processingCount > 0) {
        this.startPolling();
      } else {
        this.stopPolling();
      }
    } catch (error) {
      console.error("加载结果批次失败:", error);
      this.setData({ refreshing: false });
      wx.showToast({
        title: error.message || "加载结果失败",
        icon: "none",
      });
    }
  },

  normalizeTask(rawTask, taskId, index) {
    const placeholder = {
      taskId,
      status: "uploaded",
      subject: "",
      month: "",
      voucherNo: "",
      fileName: "",
      fileNamePreview: "",
      confidence: 0,
      pdfUrl: "",
      createdAt: "",
      updatedAt: "",
    };

    const task = rawTask || placeholder;
    const edits = this.taskEdits[taskId] || {};
    const status = task.status || "uploaded";
    const canEdit = status === "recognized";
    const subject = canEdit && edits.subject !== undefined ? edits.subject : (task.subject || "");
    const month = canEdit && edits.month !== undefined ? edits.month : (task.month || "");
    const voucherNo = canEdit && edits.voucherNo !== undefined ? edits.voucherNo : (task.voucherNo || "");
    const missingFields = this.getMissingFields({ subject, month, voucherNo });

    const needsManualFill = status === "recognized" && missingFields.length > 0;
    const manualFillText = needsManualFill ? this.getManualFillText(missingFields) : "";

    return {
      ...task,
      taskId,
      batchOrder: index + 1,
      subject,
      month,
      voucherNo,
      fileName: task.fileName || "",
      fileNamePreview: task.fileNamePreview || task.fileName || "",
      confidencePercent: task.confidence ? (task.confidence * 100).toFixed(0) : "0",
      isProcessing: ["draft", "uploaded", "confirmed"].includes(status),
      isDownloadable: status === "pdf_generated" && !!task.pdfUrl,
      canEdit,
      needsManualFill,
      manualFillText,
      statusText: this.getStatusText(status),
      statusClass: this.getStatusClass(status),
    };
  },

  getMissingFields(task) {
    const missingFields = [];
    if (!task.subject) missingFields.push("科目名称");
    if (!task.month) missingFields.push("月份");
    if (!task.voucherNo) missingFields.push("凭证号");
    return missingFields;
  },

  getManualFillText(missingFields) {
    if (!missingFields.length) {
      return "";
    }

    return missingFields.length === 3
      ? "三项关键信息均未识别，请手动填写，并可先回看OCR首页。"
      : `请补全以下字段：${missingFields.join("、")}`;
  },

  prioritizeTasks(taskList) {
    const pinnedTasks = [];
    const regularTasks = [];

    taskList.forEach((task) => {
      if (task.needsManualFill) {
        pinnedTasks.push(task);
      } else {
        regularTasks.push(task);
      }
    });

    return [...pinnedTasks, ...regularTasks];
  },

  syncSelectionState(taskList) {
    if (!this.data.selectionMode) {
      return {
        selectedTasks: [],
        selectedCount: 0,
      };
    }

    const selectedTasks = taskList.map((task) => !!this.selectedTaskState[task.taskId] && task.isDownloadable);
    return {
      selectedTasks,
      selectedCount: selectedTasks.filter(Boolean).length,
    };
  },

  setTaskListState(taskList, extraData = {}) {
    const prioritizedTaskList = this.prioritizeTasks(taskList);
    const processingCount = prioritizedTaskList.filter((task) => task.isProcessing).length;
    const readyCount = prioritizedTaskList.filter((task) => task.status === "recognized").length;
    const generatedCount = prioritizedTaskList.filter((task) => task.isDownloadable).length;
    const manualFillCount = prioritizedTaskList.filter((task) => task.needsManualFill).length;
    const selectionState = this.syncSelectionState(prioritizedTaskList);

    this.setData({
      taskList: prioritizedTaskList,
      emptyState: prioritizedTaskList.length === 0,
      processingCount,
      readyCount,
      generatedCount,
      manualFillCount,
      ...selectionState,
      ...extraData,
    });

    return {
      processingCount,
      readyCount,
      generatedCount,
      manualFillCount,
    };
  },

  startPolling() {
    if (this.pollTimer || !this.data.sessionTaskIds.length) {
      return;
    }
    this.pollTimer = setInterval(() => {
      if (!this.data.loading) {
        this.loadTaskBatch();
      }
    }, POLL_INTERVAL_MS);
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  },

  onSubjectInput(e) {
    this.updateDraftField(e.currentTarget.dataset.taskid, "subject", e.detail.value);
  },

  onMonthInput(e) {
    this.updateDraftField(e.currentTarget.dataset.taskid, "month", e.detail.value);
  },

  onVoucherNoInput(e) {
    this.updateDraftField(e.currentTarget.dataset.taskid, "voucherNo", e.detail.value);
  },

  updateDraftField(taskId, field, value) {
    if (!this.taskEdits[taskId]) {
      this.taskEdits[taskId] = {};
    }
    this.taskEdits[taskId][field] = value;

    const taskList = this.data.taskList.map((task) => {
      if (task.taskId !== taskId) {
        return task;
      }
      const nextTask = { ...task, [field]: value };
      const missingFields = this.getMissingFields(nextTask);
      nextTask.needsManualFill = nextTask.status === "recognized" && missingFields.length > 0;
      nextTask.manualFillText = nextTask.needsManualFill ? this.getManualFillText(missingFields) : "";
      return nextTask;
    });

    this.setTaskListState(taskList);
  },

  async viewFirstImage(e) {
    const taskId = e.currentTarget.dataset.taskid;
    wx.showLoading({ title: "加载中..." });

    try {
      const result = await getFirstImage(taskId);
      wx.hideLoading();
      if (!result.imageUrl) {
        wx.showToast({
          title: "无法获取图片",
          icon: "none",
        });
        return;
      }
      wx.previewImage({
        urls: [result.imageUrl],
      });
    } catch (error) {
      wx.hideLoading();
      console.error("获取OCR首页失败:", error);
      wx.showToast({
        title: "获取图片失败",
        icon: "none",
      });
    }
  },

  async onBatchConfirm() {
    const readyTasks = this.data.taskList.filter((task) => task.status === "recognized");
    if (!readyTasks.length) {
      wx.showToast({
        title: this.data.processingCount > 0 ? "任务仍在识别中" : "暂无可生成任务",
        icon: "none",
      });
      return;
    }

    const incompleteTasks = readyTasks.filter((task) => !task.subject || !task.month || !task.voucherNo);
    if (incompleteTasks.length > 0) {
      wx.showToast({
        title: "请先补全空白识别项",
        icon: "none",
      });
      return;
    }

    this.setData({ loading: true });

    try {
      let successCount = 0;

      for (const task of readyTasks) {
        await this.retryWithBackoff(() =>
          confirmGenerate(task.taskId, {
            subject: task.subject,
            month: task.month,
            voucherNo: task.voucherNo,
          })
        );
        delete this.taskEdits[task.taskId];
        successCount += 1;
      }

      await this.loadTaskBatch();
      this.setData({ loading: false });
      wx.showToast({
        title: `已生成 ${successCount} 个PDF`,
        icon: "success",
      });
    } catch (error) {
      console.error("批量生成PDF失败:", error);
      this.setData({ loading: false });
      wx.showToast({
        title: error.message || "生成失败",
        icon: "none",
      });
    }
  },

  enterSelectionMode() {
    if (!this.data.generatedCount) {
      wx.showToast({
        title: "暂无可下载PDF",
        icon: "none",
      });
      return;
    }

    this.selectedTaskState = {};
    this.setData({
      selectionMode: true,
      selectedTasks: new Array(this.data.taskList.length).fill(false),
      selectedCount: 0,
    });
  },

  cancelSelectionMode() {
    this.selectedTaskState = {};
    this.setData({
      selectionMode: false,
      selectedTasks: [],
      selectedCount: 0,
    });
  },

  toggleSelection(e) {
    const index = e.currentTarget.dataset.index;
    const task = this.data.taskList[index];
    if (!task || !task.isDownloadable) {
      wx.showToast({
        title: "仅已生成PDF的任务可下载",
        icon: "none",
      });
      return;
    }

    if (this.selectedTaskState[task.taskId]) {
      delete this.selectedTaskState[task.taskId];
    } else {
      this.selectedTaskState[task.taskId] = true;
    }

    const selectionState = this.syncSelectionState(this.data.taskList);
    this.setData(selectionState);
  },

  selectAll() {
    this.selectedTaskState = {};
    this.data.taskList.forEach((task) => {
      if (task.isDownloadable) {
        this.selectedTaskState[task.taskId] = true;
      }
    });
    const selectionState = this.syncSelectionState(this.data.taskList);
    this.setData(selectionState);
  },

  async downloadSelected() {
    const selectedList = this.data.taskList.filter((task, index) => this.data.selectedTasks[index] && task.isDownloadable);
    if (!selectedList.length) {
      wx.showToast({
        title: "请选择要下载的任务",
        icon: "none",
      });
      return;
    }

    this.setData({ loading: true });

    try {
      const result = await batchDownload(selectedList.map((task) => task.taskId));
      if (!result.downloadUrl) {
        throw new Error("未获取到下载链接");
      }

      await this.downloadZip(result.downloadUrl);
      this.setData({ loading: false });
      this.cancelSelectionMode();
    } catch (error) {
      console.error("批量下载失败:", error);
      this.setData({ loading: false });
      wx.showToast({
        title: error.message || "下载失败",
        icon: "none",
      });
    }
  },

  downloadZip(downloadUrl) {
    return new Promise((resolve, reject) => {
      wx.downloadFile({
        url: downloadUrl,
        success: (res) => {
          if (res.statusCode !== 200) {
            reject(new Error(`下载失败: HTTP ${res.statusCode}`));
            return;
          }

          wx.saveFile({
            tempFilePath: res.tempFilePath || res.filePath,
            success: () => {
              wx.showToast({
                title: "下载成功",
                icon: "success",
              });
              resolve();
            },
            fail: reject,
          });
        },
        fail: reject,
      });
    });
  },

  async retryWithBackoff(fn, maxRetries = 3, delay = 800) {
    for (let i = 0; i < maxRetries; i += 1) {
      try {
        return await fn();
      } catch (error) {
        if (i === maxRetries - 1) {
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, delay * Math.pow(2, i)));
      }
    }
  },

  onCancel() {
    clearResultSession();
    wx.navigateBack();
  },

  goHome() {
    clearAllResultState();
    wx.reLaunch({
      url: "/pages/home/home",
    });
  },

  getStatusText(status) {
    const statusMap = {
      draft: "待上传",
      uploaded: "识别中",
      recognized: "待确认",
      confirmed: "生成中",
      pdf_generated: "已生成",
      failed: "识别失败",
    };
    return statusMap[status] || status;
  },

  getStatusClass(status) {
    const statusMap = {
      draft: "status-draft",
      uploaded: "status-processing",
      recognized: "status-recognized",
      confirmed: "status-processing",
      pdf_generated: "status-done",
      failed: "status-failed",
    };
    return statusMap[status] || "status-draft";
  },
});
