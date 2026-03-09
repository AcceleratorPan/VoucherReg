const { ensureLocalUserId } = require("./utils/user");

App({
  onLaunch() {
    const logs = wx.getStorageSync("logs") || [];
    logs.unshift(Date.now());
    wx.setStorageSync("logs", logs);

    // Remove legacy auth state from the previous bearer-token flow.
    wx.removeStorageSync("accessToken");
    wx.removeStorageSync("tokenType");
    wx.removeStorageSync("expiresIn");

    const userId = ensureLocalUserId();
    this.globalData.userId = userId;
  },

  globalData: {
    userInfo: null,
    userId: "",
  },
});
