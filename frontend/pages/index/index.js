const { createTask, uploadPage, finishUpload, recognize } = require("../../utils/http");

Page({
  data: {
    firstImage: "",
    images: [],
    loading: false,
    loadingText: "",
    userId: "wx_user_" + Date.now(),
    step: 1, // 1: 上传首页, 2: 上传其他页
    taskCount: 0, // 已上传的任务数量
    pendingTasks: [] // 待确认的任务列表
  },

  async onShow() {
    const userId = wx.getStorageSync("userId");
    if (userId) {
      this.setData({ userId });
    }

    // 检查是否有待确认的任务（从 confirm 页面返回或从首页返回）
    const pendingTasks = wx.getStorageSync("pendingTasks");
    if (pendingTasks && pendingTasks.length > 0) {
      // 统一显示绿底框（正常流程）
      this.setData({
        taskCount: pendingTasks.length,
        pendingTasks: pendingTasks,
        showResumeTip: false
      });
    }

    // 检查是否需要重新创建任务（用户从confirm页面取消返回）
    const recreateTask = wx.getStorageSync("recreateTask");
    if (recreateTask) {
      wx.removeStorageSync("recreateTask");
      // 保持图片等状态，但重新创建任务
      await this.createNewTask();
      return;
    }

    // 检查是否需要重置状态（处理完成后返回首页）
    const shouldReset = wx.getStorageSync("shouldResetIndex");
    if (shouldReset) {
      // 清除标记
      wx.removeStorageSync("shouldResetIndex");
      // 重置页面状态
      this.setData({
        firstImage: "",
        images: [],
        step: 1,
        loading: false,
        loadingText: "",
        taskCount: 0,
        pendingTasks: []
      });
      // 清除待确认任务存储
      wx.removeStorageSync("pendingTasks");
      // 创建新任务
      await this.createNewTask();
    }
    // 否则保持当前状态不变（用户在步骤间切换时不会重置）
  },
  
  async createNewTask() {
    try {
      const app = getApp();
      const task = await createTask(this.data.userId);
      if (task && task.taskId) {
        app.setCurrentTaskId(task.taskId);
        this.setData({ taskId: task.taskId });
        console.log("新任务创建成功，taskId:", task.taskId);
      }
    } catch (error) {
      console.error("创建新任务失败:", error);
    }
  },

  async retryWithBackoff(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await fn();
      } catch (error) {
        if (i === maxRetries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
      }
    }
  },

  // 拍摄首页照片（只能拍1张）
  takeFirstPhoto() {
    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['original', 'compressed'],
      sourceType: ['camera'],
      success(res) {
        const tempFilePaths = res.tempFilePaths;
        that.setData({
          firstImage: tempFilePaths[0]
        });
      }
    });
  },

  // 选择首页图片（只能选1张）
  chooseFirstImage() {
    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['original', 'compressed'],
      sourceType: ['album'],
      success(res) {
        const tempFilePaths = res.tempFilePaths;
        that.setData({
          firstImage: tempFilePaths[0]
        });
      }
    });
  },

  // 拍摄其他页照片
  takePhoto() {
    const that = this;
    wx.chooseImage({
      count: 9,
      sizeType: ['original', 'compressed'],
      sourceType: ['camera'],
      success(res) {
        const tempFilePaths = res.tempFilePaths;
        that.setData({
          images: that.data.images.concat(tempFilePaths)
        });
      }
    });
  },

  // 选择其他页图片
  chooseImages() {
    const that = this;
    wx.chooseImage({
      count: 9,
      sizeType: ['original', 'compressed'],
      sourceType: ['album'],
      success(res) {
        const tempFilePaths = res.tempFilePaths;
        that.setData({
          images: that.data.images.concat(tempFilePaths)
        });
      }
    });
  },

  // 进入下一步
  nextStep() {
    this.setData({ step: 2 });
  },

  // 返回上一步
  prevStep() {
    // 只改变步骤状态，不修改图片数组
    // 这样可以处理用户在第二步上传图片后回到第一步的场景
    this.setData({ step: 1 });
  },

  deleteImage(e) {
    const type = e.currentTarget.dataset.type;
    const index = e.currentTarget.dataset.index;

    if (type === "first") {
      // 删除首页图片
      this.setData({
        firstImage: "",
        step: 1
      });
    } else {
      // 删除其他图片
      const images = this.data.images;
      images.splice(index, 1);
      this.setData({ images });
    }
  },

  async startProcess() {
    if (!this.data.firstImage) {
      wx.showToast({
        title: "必须上传首页图片",
        icon: "none"
      });
      return;
    }

    this.setData({ loading: true, loadingText: "正在准备任务..." });

    try {
      const app = getApp();
      // 每次开始处理都创建新任务，确保任务状态为 draft
      this.setData({ loadingText: "正在创建任务..." });
      const task = await createTask(this.data.userId);
      const taskId = task.taskId;
      app.setCurrentTaskId(taskId);
      this.setData({ taskId: taskId });

      this.setData({ loadingText: "正在上传图片..." });

      // 先上传首页图片（pageIndex=0）
      await uploadPage({
        taskId: taskId,
        filePath: this.data.firstImage,
        pageIndex: 0,
        userId: this.data.userId
      });

      // 再上传其他图片（pageIndex从1开始）
      for (let i = 0; i < this.data.images.length; i++) {
        await uploadPage({
          taskId: taskId,
          filePath: this.data.images[i],
          pageIndex: i + 1,
          userId: this.data.userId
        });
      }

      this.setData({ loadingText: "正在完成上传..." });

      await finishUpload(taskId, this.data.userId);

      this.setData({ loadingText: "正在识别..." });

      const recognized = await this.retryWithBackoff(() => recognize(taskId, this.data.userId), 3);

      this.setData({ loading: false });

      // 将任务添加到待确认列表
      const newTask = {
        taskId: taskId,
        subject: recognized.subject || "",
        month: recognized.month || "",
        voucherNo: recognized.voucherNo || "",
        confidence: recognized.confidence || 0,
        fileNamePreview: recognized.fileNamePreview || ""
      };

      const pendingTasks = [...this.data.pendingTasks, newTask];
      this.setData({
        pendingTasks: pendingTasks,
        taskCount: pendingTasks.length
      });

      // 保存到存储
      wx.setStorageSync("pendingTasks", pendingTasks);
      console.log("保存任务列表，当前任务数:", pendingTasks.length);

      // 上传成功后继续上传下一批
      wx.showToast({
        title: "上传成功",
        icon: "success",
        duration: 1500
      });

      // 自动继续上传，创建新任务
      this.continueUpload();

    } catch (error) {
      console.error("处理失败:", error);
      this.setData({ loading: false });
      wx.showModal({
        title: "识别失败",
        content: error.message || "OCR识别失败，是否重试？",
        confirmText: "重试",
        cancelText: "取消",
        success: (res) => {
          if (res.confirm) {
            this.startProcess();
          }
        }
      });
    }
  },

  // 继续上传下一批
  continueUpload() {
    // 重置图片数据但保留 taskCount
    this.setData({
      firstImage: "",
      images: [],
      step: 1,
      loading: false,
      loadingText: ""
    });
    // 创建新任务
    this.createNewTask();
  },

  // 跳转到确认页面
  goToConfirm() {
    const pendingTasks = this.data.pendingTasks;
    if (pendingTasks.length > 0) {
      // 将任务列表存入存储，供 confirm 页面使用
      wx.setStorageSync("pendingTasks", pendingTasks);
      wx.navigateTo({
        url: "/pages/confirm/confirm"
      });
    }
  },

  goHome() {
    const { taskCount, pendingTasks } = this.data;

    // 如果有待处理的任务，弹窗询问是否保留
    if (taskCount > 0 && pendingTasks.length > 0) {
      wx.showModal({
        title: "返回首页",
        content: `当前有 ${taskCount} 个待处理任务，是否保留？保留后下次可继续处理。`,
        confirmText: "保留",
        cancelText: "不保留",
        success: (res) => {
          if (res.confirm) {
            // 用户选择保留，pendingTasks 已存储在 wxStorage 中
            this.doGoHome(false);
          } else {
            // 用户选择不保留，清理所有数据
            this.doGoHome(true);
          }
        }
      });
    } else {
      // 没有待处理任务，直接返回首页
      this.doGoHome(true);
    }
  },

  doGoHome(clearAll) {
    if (clearAll) {
      // 清理所有相关存储
      wx.removeStorageSync("pendingTasks");
      wx.removeStorageSync("recreateTask");
      wx.removeStorageSync("shouldResetIndex");
      wx.removeStorageSync("selectedTasksForDownload");

      // 重置页面状态
      this.setData({
        firstImage: "",
        images: [],
        step: 1,
        loading: false,
        loadingText: "",
        taskCount: 0,
        pendingTasks: []
      });
    }

    wx.reLaunch({
      url: "/pages/home/home"
    });
  }
});
