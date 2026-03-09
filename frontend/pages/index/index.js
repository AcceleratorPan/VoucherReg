const { createTask, uploadPage, finishUpload, recognize } = require("../../utils/http");

Page({
  data: {
    firstImage: "",
    images: [],
    loading: false,
    loadingText: "",
    step: 1,
    taskCount: 0,
    pendingTasks: [],
    activeTaskIds: [], // 正在后台识别的任务ID
  },

  onShow() {
    // 检查是否有待确认的任务
    const pendingTasks = wx.getStorageSync("pendingTasks") || [];
    this.setData({
      pendingTasks: pendingTasks,
      taskCount: pendingTasks.length
    });

    // 检查是否有待处理的任务需要更新
    this.checkPendingRecognitions();
  },

  // 检查待处理任务的识别状态
  async checkPendingRecognitions() {
    const pendingTasks = wx.getStorageSync("pendingTasks") || [];
    const userId = wx.getStorageSync("userId");
    const activeTaskIds = this.data.activeTaskIds;

    if (pendingTasks.length === 0 && activeTaskIds.length === 0) {
      return;
    }

    // 过滤掉已完成的任务（已有识别结果的）
    const incompleteTasks = pendingTasks.filter(t => !t.subject && !t.month && !t.voucherNo);

    if (incompleteTasks.length > 0) {
      // 有未完成识别的任务，尝试获取最新状态
      try {
        const { getTask } = require("../../utils/http");
        for (const task of incompleteTasks) {
          try {
            const result = await getTask(task.taskId, userId);
            if (result && result.status === 'recognized') {
              // 更新本地存储
              const updatedTasks = pendingTasks.map(t =>
                t.taskId === task.taskId ? { ...t, ...result } : t
              );
              wx.setStorageSync("pendingTasks", updatedTasks);
              this.setData({ pendingTasks: updatedTasks, taskCount: updatedTasks.length });
            }
          } catch (e) {
            // 忽略单个任务获取失败
          }
        }
      } catch (e) {
        console.error("检查任务状态失败:", e);
      }
    }
  },

  async retryWithBackoff(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i += 1) {
      try {
        return await fn();
      } catch (error) {
        if (i === maxRetries - 1) {
          throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, delay * Math.pow(2, i)));
      }
    }
  },

  takeFirstPhoto() {
    wx.chooseImage({
      count: 1,
      sizeType: ["original", "compressed"],
      sourceType: ["camera"],
      success: (res) => {
        this.setData({
          firstImage: res.tempFilePaths[0],
          step: 1,
        });
      },
    });
  },

  chooseFirstImage() {
    wx.chooseImage({
      count: 1,
      sizeType: ["original", "compressed"],
      sourceType: ["album"],
      success: (res) => {
        this.setData({
          firstImage: res.tempFilePaths[0],
          step: 1,
        });
      },
    });
  },

  takePhoto() {
    wx.chooseImage({
      count: 9,
      sizeType: ["original", "compressed"],
      sourceType: ["camera"],
      success: (res) => {
        this.setData({
          images: this.data.images.concat(res.tempFilePaths),
        });
      },
    });
  },

  chooseImages() {
    wx.chooseImage({
      count: 9,
      sizeType: ["original", "compressed"],
      sourceType: ["album"],
      success: (res) => {
        this.setData({
          images: this.data.images.concat(res.tempFilePaths),
        });
      },
    });
  },

  nextStep() {
    this.setData({ step: 2 });
  },

  prevStep() {
    this.setData({ step: 1 });
  },

  deleteImage(e) {
    const { type, index } = e.currentTarget.dataset;
    if (type === "first") {
      this.setData({
        firstImage: "",
        images: [],
        step: 1,
      });
      return;
    }

    const images = [...this.data.images];
    images.splice(index, 1);
    this.setData({ images });
  },

  async startProcess() {
    if (!this.data.firstImage) {
      wx.showToast({
        title: "必须上传首页图片",
        icon: "none",
      });
      return;
    }

    const userId = wx.getStorageSync("userId") || ("wx_user_" + Date.now());

    this.setData({ loading: true, loadingText: "正在上传任务..." });

    try {
      const task = await createTask(userId);
      const taskId = task.taskId;

      await uploadPage({
        taskId,
        filePath: this.data.firstImage,
        pageIndex: 0,
        userId,
      });

      for (let i = 0; i < this.data.images.length; i += 1) {
        await uploadPage({
          taskId,
          filePath: this.data.images[i],
          pageIndex: i + 1,
          userId,
        });
      }

      await finishUpload(taskId, userId);

      // 先将任务添加到待处理列表（只有 taskId）
      const newTask = {
        taskId: taskId,
        status: "uploaded"
      };
      const pendingTasks = [...this.data.pendingTasks, newTask];
      wx.setStorageSync("pendingTasks", pendingTasks);
      this.setData({
        pendingTasks: pendingTasks,
        taskCount: pendingTasks.length
      });

      // 重置表单，允许用户继续上传
      this.resetUploadForm();

      wx.showToast({
        title: "已加入后台识别",
        icon: "success",
        duration: 1500,
      });

      // 后台异步识别
      this.runRecognitionInBackground(taskId, userId);

    } catch (error) {
      console.error("上传任务失败:", error);
      this.setData({ loading: false, loadingText: "" });
      wx.showModal({
        title: "上传失败",
        content: error.message || "上传任务失败，请重试。",
        confirmText: "重试",
        cancelText: "取消",
        success: (res) => {
          if (res.confirm) {
            this.startProcess();
          }
        },
      });
    }
  },

  async runRecognitionInBackground(taskId, userId) {
    // 添加到活跃任务列表
    this.setData({
      activeTaskIds: [...this.data.activeTaskIds, taskId]
    });

    try {
      const recognized = await this.retryWithBackoff(() => recognize(taskId, userId), 3);

      // 更新待处理列表中的任务信息
      const pendingTasks = wx.getStorageSync("pendingTasks") || [];
      const updatedTasks = pendingTasks.map(t => {
        if (t.taskId === taskId) {
          return {
            ...t,
            subject: recognized.subject || "",
            month: recognized.month || "",
            voucherNo: recognized.voucherNo || "",
            confidence: recognized.confidence || 0,
            fileNamePreview: recognized.fileNamePreview || "",
            status: "recognized"
          };
        }
        return t;
      });
      wx.setStorageSync("pendingTasks", updatedTasks);
      this.setData({
        pendingTasks: updatedTasks,
        taskCount: updatedTasks.length
      });

    } catch (error) {
      console.error("后台识别失败:", taskId, error);

      // 标记识别失败
      const pendingTasks = wx.getStorageSync("pendingTasks") || [];
      const updatedTasks = pendingTasks.map(t => {
        if (t.taskId === taskId) {
          return { ...t, status: "failed" };
        }
        return t;
      });
      wx.setStorageSync("pendingTasks", updatedTasks);

    } finally {
      // 从活跃列表中移除
      const activeTaskIds = this.data.activeTaskIds.filter(id => id !== taskId);
      this.setData({ activeTaskIds });
    }
  },

  resetUploadForm() {
    this.setData({
      firstImage: "",
      images: [],
      step: 1,
      loading: false,
      loadingText: "",
    });
  },

  // 等待所有后台识别完成
  async waitForAllRecognitions() {
    const activeTaskIds = this.data.activeTaskIds;
    if (activeTaskIds.length === 0) {
      return;
    }

    wx.showLoading({ title: "等待识别完成..." });

    // 等待直到所有识别完成
    while (this.data.activeTaskIds.length > 0) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    wx.hideLoading();
  },

  async goToConfirm() {
    // 等待所有后台识别完成
    if (this.data.activeTaskIds.length > 0) {
      wx.showLoading({ title: "等待识别完成..." });
      while (this.data.activeTaskIds.length > 0) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      wx.hideLoading();
    }

    const pendingTasks = this.data.pendingTasks;
    if (pendingTasks.length === 0) {
      wx.showToast({
        title: "暂无可查看结果",
        icon: "none",
      });
      return;
    }

    wx.navigateTo({
      url: "/pages/confirm/confirm",
    });
  },

  goHome() {
    const { taskCount } = this.data;

    if (taskCount > 0) {
      wx.showModal({
        title: "返回首页",
        content: `当前有 ${taskCount} 个任务待处理，是否保留？`,
        confirmText: "保留",
        cancelText: "清空",
        success: (res) => {
          if (res.confirm) {
            this.doGoHome(false);
          } else {
            this.doGoHome(true);
          }
        },
      });
      return;
    }

    this.doGoHome(true);
  },

  doGoHome(clearAll) {
    if (clearAll) {
      wx.removeStorageSync("pendingTasks");
      this.setData({
        firstImage: "",
        images: [],
        step: 1,
        loading: false,
        loadingText: "",
        taskCount: 0,
        pendingTasks: [],
        activeTaskIds: []
      });
    }

    wx.reLaunch({
      url: "/pages/home/home",
    });
  },
});
