const {
  clearAllResultState,
  clearSelectedDownloadTasks,
  getSelectedDownloadTasks,
} = require("../../utils/result-session");

Page({
  data: {
    taskList: [],
  },

  onLoad(options) {
    const selectedTasks = getSelectedDownloadTasks();
    if (selectedTasks) {
      this.setData({ taskList: selectedTasks });
    }
  },

  // 返回首页
  goHome() {
    clearAllResultState();

    wx.reLaunch({
      url: "/pages/home/home"
    });
  },

  // 返回上一步（回到 confirm 页面）
  goBack() {
    clearSelectedDownloadTasks();
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
