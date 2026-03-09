const { batchDownloadLink } = require("../../utils/http");

Page({
  data: {
    downloadUrl: "",
    taskCount: 0,
    userId: "",
    copied: false
  },

  onLoad() {
    const userId = wx.getStorageSync("userId");
    this.setData({ userId });

    // 获取选中的任务
    const selectedTasks = wx.getStorageSync("selectedTasksForDownload") || [];
    this.setData({ taskCount: selectedTasks.length });

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
    wx.removeStorageSync("pendingTasks");
    wx.removeStorageSync("selectedTasksForDownload");
    wx.reLaunch({
      url: "/pages/home/home"
    });
  },

  // 返回确认页面
  goBack() {
    wx.navigateBack();
  }
});
