const { getTask } = require("../../utils/http");

Page({
  data: {
    taskId: "",
    task: null,
    loading: false
  },

  onLoad(options) {
    const { taskId } = options;
    if (!taskId) {
      wx.showToast({
        title: "参数错误",
        icon: "none"
      });
      wx.navigateBack();
      return;
    }
    this.setData({ taskId });
    this.loadTaskDetail();
  },

  onPullDownRefresh() {
    this.loadTaskDetail().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadTaskDetail() {
    this.setData({ loading: true });

    try {
      const userId = wx.getStorageSync("userId");
      if (!userId) {
        this.setData({ loading: false });
        return;
      }
      
      const task = await getTask(this.data.taskId, userId);
      const confidencePercent = task.confidence ? (task.confidence * 100).toFixed(0) : "0";
      this.setData({
        task: task,
        confidencePercent: confidencePercent,
        loading: false
      });
    } catch (error) {
      console.error("加载任务详情失败:", error);
      wx.showToast({
        title: error.message || "加载失败",
        icon: "none"
      });
      this.setData({ loading: false });
    }
  },

  onViewPDF() {
    const { task } = this.data;
    if (task && task.status === "pdf_generated" && task.pdfUrl) {
      wx.navigateTo({
        url: `/pages/pdf-preview/pdf-preview?pdfUrl=${encodeURIComponent(task.pdfUrl)}&fileName=${encodeURIComponent(task.fileName || "")}`
      });
    } else {
      wx.showToast({
        title: "PDF尚未生成",
        icon: "none"
      });
    }
  },

  onRetry() {
    const { task } = this.data;
    if (task && task.status === "failed") {
      wx.showModal({
        title: "重试任务",
        content: "确定要重新处理此任务吗？",
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: `/pages/index/index?retryTaskId=${this.data.taskId}`
            });
          }
        }
      });
    }
  },

  getStatusText(status) {
    const statusMap = {
      draft: "草稿",
      uploaded: "已上传",
      recognized: "已识别",
      confirmed: "已确认",
      pdf_generated: "已完成",
      failed: "失败"
    };
    return statusMap[status] || status;
  },

  getStatusColor(status) {
    const colorMap = {
      draft: "#999",
      uploaded: "#1890ff",
      recognized: "#faad14",
      confirmed: "#722ed1",
      pdf_generated: "#52c41a",
      failed: "#f5222d"
    };
    return colorMap[status] || "#999";
  },

  formatDate(dateString) {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleString("zh-CN");
  },

  goHome() {
    // 清理所有相关存储
    wx.removeStorageSync("pendingTasks");
    wx.removeStorageSync("recreateTask");
    wx.removeStorageSync("shouldResetIndex");
    wx.removeStorageSync("selectedTasksForDownload");

    wx.reLaunch({
      url: "/pages/home/home"
    });
  }
});
