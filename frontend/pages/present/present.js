const { batchDownloadLink } = require("../../utils/http");
const { goHomeWithConfirm } = require("../../utils/navigation");

Page({
  data: {
    downloadUrl: "",
    taskCount: 0,
    userId: "",
    copied: false,
    fileNames: []
  },

  onLoad() {
    const userId = wx.getStorageSync("userId");
    this.setData({ userId });

    // 获取选中的任务
    const selectedTasks = wx.getStorageSync("selectedTasksForDownload") || [];
    const fileNames = selectedTasks.map(t => t.pdfName).filter(Boolean);
    this.setData({
      taskCount: selectedTasks.length,
      fileNames
    });

    // 获取下载链接
    this.getDownloadLink(selectedTasks);
  },

  async getDownloadLink(selectedTasks) {
    if (selectedTasks.length === 0) {
      wx.showToast({
        title: "没有可下载的任务",
        icon: "none"
      });
      return;
    }

    wx.showLoading({ title: "获取下载链接..." });

    try {
      const taskIds = selectedTasks.map(t => t.taskId);
      const result = await batchDownloadLink(taskIds, this.data.userId);

      wx.hideLoading();

      if (result.downloadUrl) {
        // 获取成功，从 pendingTasks 中移除已选中的任务（标记为已完成）
        const pendingTasks = wx.getStorageSync("pendingTasks") || [];
        const selectedIds = new Set(selectedTasks.map(t => t.taskId));
        const remainingTasks = pendingTasks.filter(t => !selectedIds.has(t.taskId));
        wx.setStorageSync("pendingTasks", remainingTasks);

        // 保留 selectedTasksForDownload 用于显示任务数量
        this.setData({ downloadUrl: result.downloadUrl });
      } else {
        wx.showToast({
          title: "获取链接失败",
          icon: "none"
        });
      }
    } catch (error) {
      wx.hideLoading();
      console.error("获取下载链接失败:", error);
      wx.showToast({
        title: "获取链接失败",
        icon: "none"
      });
    }
  },

  // 复制链接到剪切板
  copyLink() {
    if (!this.data.downloadUrl) {
      wx.showToast({
        title: "没有链接可复制",
        icon: "none"
      });
      return;
    }

    wx.setClipboardData({
      data: this.data.downloadUrl,
      success: () => {
        this.setData({ copied: true });
        wx.showToast({
          title: "已复制到剪切板",
          icon: "success"
        });
      }
    });
  },

  // 重新获取链接
  refreshLink() {
    const selectedTasks = wx.getStorageSync("selectedTasksForDownload") || [];
    this.setData({ copied: false, downloadUrl: "" });
    this.getDownloadLink(selectedTasks);
  },

  // 返回首页
  goHome() {
    // 检查 pendingTasks 中已生成 PDF 但未下载的任务
    const pendingTasks = wx.getStorageSync("pendingTasks") || [];
    const pendingPDFCount = pendingTasks.filter(t => t.status === "pdf_generated").length;

    goHomeWithConfirm({
      getPendingCount: () => pendingPDFCount
    });
  },

  // 返回确认页面
  goBack() {
    wx.navigateBack();
  }
});
