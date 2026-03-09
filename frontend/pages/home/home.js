Page({
  data: {

  },

  onLoad() {

  },

  goToProcess() {
    wx.navigateTo({
      url: "/pages/index/index"
    });
  },

  goToHistory() {
    wx.navigateTo({
      url: "/pages/history/history"
    });
  }
});
