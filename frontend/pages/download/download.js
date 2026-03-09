Page({
  data: {
    taskList: [],
    userId: ""
  },

  onLoad(options) {
    const userId = wx.getStorageSync("userId");
    this.setData({ userId });

    // 从全局或存储中获取选中的任务列表
    const selectedTasks = wx.getStorageSync("selectedTasksForDownload");
    if (selectedTasks) {
      this.setData({ taskList: selectedTasks });
    }
  },

  // 返回首页
  goHome() {
    // 清理所有相关存储
    wx.removeStorageSync("pendingTasks");
    wx.removeStorageSync("recreateTask");
    wx.removeStorageSync("shouldResetIndex");
    wx.removeStorageSync("selectedTasksForDownload");

    wx.reLaunch({
      url: "/pages/home/home"
    });
  },

  // 返回上一步（回到 confirm 页面）
  goBack() {
    wx.removeStorageSync("selectedTasksForDownload");
    wx.navigateBack();
  },

  // 分享 zip
  onShareAppMessage() {
    const { taskList } = this.data;
    const taskIds = taskList.map(t => t.taskId).join(",");
    return {
      title: "凭证PDF包",
      path: `/pages/index/index?tasks=${taskIds}`
    };
  }
});
