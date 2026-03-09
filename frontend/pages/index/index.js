const { createTask, uploadPage, finishUpload, recognize } = require("../../utils/http");
const {
  addPendingResultTaskId,
  clearAllResultState,
  getActiveResultTaskIds,
  getPendingResultCount,
} = require("../../utils/result-session");

Page({
  data: {
    firstImage: "",
    images: [],
    loading: false,
    loadingText: "",
    step: 1,
    taskCount: 0,
  },

  onShow() {
    this.refreshTaskCount();
  },

  refreshTaskCount() {
    this.setData({ taskCount: getPendingResultCount() + getActiveResultTaskIds().length });
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

    this.setData({ loading: true, loadingText: "正在上传任务..." });

    try {
      const task = await createTask();
      const taskId = task.taskId;

      await uploadPage({
        taskId,
        filePath: this.data.firstImage,
        pageIndex: 0,
      });

      for (let i = 0; i < this.data.images.length; i += 1) {
        await uploadPage({
          taskId,
          filePath: this.data.images[i],
          pageIndex: i + 1,
        });
      }

      await finishUpload(taskId);
      addPendingResultTaskId(taskId);

      this.resetUploadForm();
      this.refreshTaskCount();

      wx.showToast({
        title: "已加入后台识别",
        icon: "success",
        duration: 1500,
      });

      this.runRecognitionInBackground(taskId);
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

  async runRecognitionInBackground(taskId) {
    try {
      await this.retryWithBackoff(() => recognize(taskId), 3);
    } catch (error) {
      console.error("后台识别失败:", taskId, error);
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

  goToConfirm() {
    const pendingTaskCount = getPendingResultCount();
    const activeSessionCount = getActiveResultTaskIds().length;

    if (pendingTaskCount === 0 && activeSessionCount === 0) {
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
    const taskCount = getPendingResultCount() + getActiveResultTaskIds().length;

    if (taskCount > 0) {
      wx.showModal({
        title: "返回首页",
        content: `当前有 ${taskCount} 个任务待查看结果，是否保留？`,
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
      clearAllResultState();
      this.resetUploadForm();
      this.setData({ taskCount: 0 });
    }

    wx.reLaunch({
      url: "/pages/home/home",
    });
  },
});
