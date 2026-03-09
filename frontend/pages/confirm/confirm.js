const { confirmGenerate, batchDownload, getFirstImage } = require("../../utils/http");

Page({
  data: {
    taskList: [],
    userId: "",
    loading: false,
    // 选择模式
    selectionMode: false,
    selectedTasks: [],
    selectedCount: 0
  },

  onLoad(options) {
    const userId = wx.getStorageSync("userId");
    this.setData({ userId });

    // 从存储中获取任务列表
    const pendingTasks = wx.getStorageSync("pendingTasks");
    console.log("confirm页面读取到任务数:", pendingTasks ? pendingTasks.length : 0);
    if (pendingTasks && pendingTasks.length > 0) {
      // 为每个任务初始化选中状态
      const taskList = pendingTasks.map(task => ({
        ...task,
        confidencePercent: task.confidence ? (task.confidence * 100).toFixed(0) : 0
      }));
      this.setData({ taskList });
    }
  },

  // 监听输入变化
  onSubjectInput(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    const taskList = this.data.taskList;
    taskList[index].subject = value;
    this.setData({ taskList });
  },

  onMonthInput(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    const taskList = this.data.taskList;
    taskList[index].month = value;
    this.setData({ taskList });
  },

  onVoucherNoInput(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value;
    const taskList = this.data.taskList;
    taskList[index].voucherNo = value;
    this.setData({ taskList });
  },

  // 回看第一张图片
  async viewFirstImage(e) {
    const taskId = e.currentTarget.dataset.taskid;
    wx.showLoading({ title: "加载中..." });

    try {
      const result = await getFirstImage(taskId, this.data.userId);
      wx.hideLoading();

      if (result.imageUrl) {
        wx.previewImage({
          urls: [result.imageUrl]
        });
      } else {
        wx.showToast({
          title: "无法获取图片",
          icon: "none"
        });
      }
    } catch (error) {
      wx.hideLoading();
      console.error("获取第一张图片失败:", error);
      wx.showToast({
        title: "获取图片失败",
        icon: "none"
      });
    }
  },

  // 进入选择模式
  enterSelectionMode() {
    this.setData({
      selectionMode: true,
      selectedTasks: new Array(this.data.taskList.length).fill(false),
      selectedCount: 0
    });
  },

  // 取消选择模式
  cancelSelectionMode() {
    this.setData({
      selectionMode: false,
      selectedTasks: []
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
    const selectedTasks = new Array(this.data.taskList.length).fill(true);
    this.setData({ selectedTasks, selectedCount: this.data.taskList.length });
  },

  // 批量确认并生成
  async onBatchConfirm() {
    const { taskList, selectedTasks, userId } = this.data;

    // 收集需要确认的任务
    const tasksToConfirm = taskList.filter((task, index) => selectedTasks[index]);

    if (tasksToConfirm.length === 0) {
      wx.showToast({
        title: "请选择要生成的任务",
        icon: "none"
      });
      return;
    }

    // 检查是否填写完整
    for (const task of tasksToConfirm) {
      if (!task.subject || !task.month || !task.voucherNo) {
        wx.showToast({
          title: "请填写完整信息",
          icon: "none"
        });
        return;
      }
    }

    this.setData({ loading: true });

    try {
      const results = [];

      for (const task of tasksToConfirm) {
        const result = await this.retryWithBackoff(
          () => confirmGenerate(task.taskId, {
            subject: task.subject,
            month: task.month,
            voucherNo: task.voucherNo
          }, userId),
          3
        );
        results.push({
          ...task,
          result
        });
      }

      this.setData({ loading: false });

      // 筛选生成成功的任务
      const successTasks = results
        .filter(r => r.result.status === "pdf_generated" && r.result.pdfUrl)
        .map(r => ({
          taskId: r.taskId,
          pdfName: r.result.fileName || r.fileNamePreview || "凭证.pdf",
          pdfUrl: r.result.pdfUrl
        }));

      if (successTasks.length > 0) {
        // 保存选中的任务用于下载页面
        wx.setStorageSync("selectedTasksForDownload", successTasks);

        // 从待确认列表中移除已处理的任务
        const remainingTasks = taskList.filter((task, index) => !selectedTasks[index]);
        wx.setStorageSync("pendingTasks", remainingTasks);

        wx.showToast({
          title: `成功生成 ${successTasks.length} 个`,
          icon: "success"
        });

        setTimeout(() => {
          wx.navigateTo({
            url: "/pages/download/download"
          });
        }, 1500);
      } else {
        wx.showToast({
          title: "生成PDF失败",
          icon: "none"
        });
      }
    } catch (error) {
      console.error("批量生成失败:", error);
      this.setData({ loading: false });
      wx.showToast({
        title: "生成失败",
        icon: "none"
      });
    }
  },

  // 批量下载（已选择的任务直接下载）
  async downloadSelected() {
    const { taskList, selectedTasks, userId } = this.data;

    const tasksToDownload = taskList.filter((task, index) => selectedTasks[index]);

    if (tasksToDownload.length === 0) {
      wx.showToast({
        title: "请选择要下载的任务",
        icon: "none"
      });
      return;
    }

    this.setData({ loading: true });

    try {
      const taskIds = tasksToDownload.map(t => t.taskId);
      const result = await batchDownload(taskIds, userId);

      this.setData({ loading: false });

      if (result.zipUrl) {
        // 下载 zip 文件
        wx.downloadFile({
          url: result.zipUrl,
          success: (res) => {
            if (res.statusCode === 200) {
              wx.saveFile({
                tempFilePath: res.tempFilePath,
                success: (saveRes) => {
                  wx.showToast({
                    title: "保存成功",
                    icon: "success"
                  });
                },
                fail: () => {
                  wx.showToast({
                    title: "保存失败",
                    icon: "none"
                  });
                }
              });
            }
          },
          fail: () => {
            wx.showToast({
              title: "下载失败",
              icon: "none"
            });
          }
        });
      } else {
        // 如果后端直接返回文件，则跳转预览
        const successTasks = tasksToDownload.map(t => ({
          taskId: t.taskId,
          pdfName: t.fileNamePreview || "凭证.pdf",
          pdfUrl: result.pdfUrls ? result.pdfUrls[t.taskId] : ""
        })).filter(t => t.pdfUrl);

        if (successTasks.length > 0) {
          wx.setStorageSync("selectedTasksForDownload", successTasks);
          wx.navigateTo({
            url: "/pages/download/download"
          });
        } else {
          wx.showToast({
            title: "获取下载链接失败",
            icon: "none"
          });
        }
      }
    } catch (error) {
      console.error("批量下载失败:", error);
      this.setData({ loading: false });
      wx.showToast({
        title: "下载失败",
        icon: "none"
      });
    }
  },

  retryWithBackoff(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return fn();
      } catch (error) {
        if (i === maxRetries - 1) throw error;
      }
    }
  },

  // 返回继续处理（返回 index）
  onCancel() {
    // 设置标记，告诉 index 页面需要重新创建任务
    wx.setStorageSync("recreateTask", true);
    wx.redirectTo({
      url: "/pages/index/index"
    });
  },

  goHome() {
    // 清除所有待处理任务
    wx.removeStorageSync("pendingTasks");
    wx.removeStorageSync("selectedTasksForDownload");
    wx.reLaunch({
      url: "/pages/home/home"
    });
  }
});
