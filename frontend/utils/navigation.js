/**
 * 导航辅助模块
 */

/**
 * 返回首页，如果有未下载的任务则弹窗确认
 * @param {Object} options 配置选项
 * @param {Function} options.getPendingCount - 获取待处理任务数量的函数
 * @param {string} options.pendingType - pendingTasks 的类型: 'taskList'(数组) 或 'count'(数字)
 * @param {Function} options.onComplete - 完成后的回调
 */
function goHomeWithConfirm(options) {
  const { getPendingCount, onComplete } = options;

  const pendingCount = typeof getPendingCount === 'function' ? getPendingCount() : 0;

  if (pendingCount > 0) {
    wx.showModal({
      title: "返回首页",
      content: `当前有 ${pendingCount} 个已上传的任务未下载，是否保留？`,
      confirmText: "保留",
      cancelText: "丢弃",
      success: (res) => {
        if (res.confirm) {
          // 保留任务，只清除 selectedTasksForDownload
          wx.removeStorageSync("selectedTasksForDownload");
          typeof onComplete === 'function' && onComplete(true);
        } else {
          // 清空任务
          wx.removeStorageSync("pendingTasks");
          wx.removeStorageSync("selectedTasksForDownload");
          typeof onComplete === 'function' && onComplete(false);
        }
        wx.reLaunch({
          url: "/pages/home/home"
        });
      },
    });
    return;
  }

  // 没有待处理任务，直接返回
  wx.removeStorageSync("pendingTasks");
  wx.removeStorageSync("selectedTasksForDownload");
  wx.reLaunch({
    url: "/pages/home/home"
  });
}

module.exports = {
  goHomeWithConfirm
};
