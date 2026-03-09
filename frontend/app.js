App({
  onLaunch() {
    const logs = wx.getStorageSync("logs") || []
    logs.unshift(Date.now())
    wx.setStorageSync("logs", logs)

    let userId = wx.getStorageSync("userId");
    if (!userId) {
      userId = "wx_user_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
      wx.setStorageSync("userId", userId);
    }

    // 注意：任务不再在 onLaunch 中创建，而是在 index 页面的 onShow 中创建
    // 这样可以确保每次用户进入首页都能获得一个新的任务
    // this.createInitialTask(userId);
    
    // 设置标记，表示这是新启动的应用，index页面需要重置状态
    wx.setStorageSync("shouldResetIndex", true);

    wx.login({
      success: res => {
        console.log("微信登录成功，code:", res.code);
      }
    })
  },

  globalData: {
    userInfo: null,
    currentTaskId: null
  },

  setCurrentTaskId(taskId) {
    this.globalData.currentTaskId = taskId;
    wx.setStorageSync("currentTaskId", taskId);
  },

  getCurrentTaskId() {
    if (this.globalData.currentTaskId) {
      return this.globalData.currentTaskId;
    }
    return wx.getStorageSync("currentTaskId");
  },

  clearCurrentTaskId() {
    this.globalData.currentTaskId = null;
    wx.removeStorageSync("currentTaskId");
  }
})