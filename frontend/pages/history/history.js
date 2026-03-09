const { getTasks, clearAllTasks } = require("../../utils/http");

Page({
  data: {
    tasks: [],
    loading: false,
    refreshing: false,
    // 批量选择模式
    selectionMode: false,
    selectedTasks: [],
    selectedCount: 0
  },

  onLoad() {
    this.loadTasks();
  },

  onShow() {
    this.loadTasks();
  },

  onPullDownRefresh() {
    this.loadTasks(true);
  },

  async loadTasks(isRefresh = false) {
    if (isRefresh) {
      this.setData({ refreshing: true });
    } else {
      this.setData({ loading: true });
    }

    try {
      const userId = wx.getStorageSync("userId");
      const result = await getTasks(userId);
      // 只显示 pdf_generated 状态的任务（已完成的任务）
      const allTasks = result.items || result || [];
      const validTasks = allTasks.filter(task => task.status === 'pdf_generated');
      this.setData({
        tasks: validTasks,
        loading: false,
        refreshing: false,
        selectionMode: false,
        selectedTasks: [],
        selectedCount: 0
      });
    } catch (error) {
      console.error("加载历史记录失败:", error);
      wx.showToast({
        title: error.message || "加载失败",
        icon: "none"
      });
      this.setData({
        loading: false,
        refreshing: false
      });
    } finally {
      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    }
  },

  onTaskTap(e) {
    // 如果在选择模式下，不响应点击
    if (this.data.selectionMode) {
      return;
    }
    const task = e.currentTarget.dataset.task;
    wx.navigateTo({
      url: `/pages/detail/detail?taskId=${task.taskId}`
    });
  },

  // 进入批量选择模式
  enterSelectionMode() {
    this.setData({
      selectionMode: true,
      selectedTasks: new Array(this.data.tasks.length).fill(false),
      selectedCount: 0
    });
  },

  // 切换选中状态
  toggleSelection(e) {
    const index = e.currentTarget.dataset.index;
    const selectedTasks = [...this.data.selectedTasks];
    selectedTasks[index] = !selectedTasks[index];
    const selectedCount = selectedTasks.filter(s => s).length;
    this.setData({ selectedTasks, selectedCount });
  },

  // 全选
  selectAll() {
    const selectedTasks = new Array(this.data.tasks.length).fill(true);
    this.setData({ selectedTasks, selectedCount: this.data.tasks.length });
  },

  // 取消选择模式
  cancelSelectionMode() {
    this.setData({
      selectionMode: false,
      selectedTasks: [],
      selectedCount: 0
    });
  },

  // 批量下载选中任务
  onBatchDownload() {
    const { tasks, selectedTasks } = this.data;
    const selectedList = tasks.filter((task, index) => selectedTasks[index]);

    if (selectedList.length === 0) {
      wx.showToast({
        title: "请选择要下载的任务",
        icon: "none"
      });
      return;
    }

    // 构造任务数据用于下载页面
    const downloadTasks = selectedList.map(task => ({
      taskId: task.taskId,
      pdfName: task.fileName || task.subject || "凭证.pdf",
      pdfUrl: task.pdfUrl || ""
    })).filter(t => t.pdfUrl);

    if (downloadTasks.length === 0) {
      wx.showToast({
        title: "所选任务无可下载文件",
        icon: "none"
      });
      return;
    }

    wx.setStorageSync("selectedTasksForDownload", downloadTasks);
    wx.navigateTo({
      url: "/pages/download/download"
    });
  },

  onClearHistory() {
    wx.showModal({
      title: "确认清除",
      content: "确定要清除所有历史记录吗？此操作不可恢复。",
      confirmText: "确认清除",
      cancelText: "取消",
      success: async (res) => {
        if (res.confirm) {
          const currentCount = this.data.tasks.length;

          try {
            const userId = wx.getStorageSync("userId");
            await clearAllTasks(userId);
            wx.showToast({
              title: `成功清除 ${currentCount} 条记录`,
              icon: "success"
            });
            this.loadTasks();
          } catch (error) {
            console.error("清除历史记录失败:", error);
            wx.showToast({
              title: error.message || "清除失败",
              icon: "none"
            });
          }
        }
      }
    });
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

  goHome() {
    wx.reLaunch({
      url: "/pages/home/home"
    });
  }
});
