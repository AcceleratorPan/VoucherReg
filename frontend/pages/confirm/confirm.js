const { confirmGenerate, batchDownloadLink, getFirstImage } = require("../../utils/http");

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

  async onLoad(options) {
    const userId = wx.getStorageSync("userId");
    this.setData({ userId });

    // 从存储中获取任务列表
    const pendingTasks = wx.getStorageSync("pendingTasks");
    console.log("confirm页面读取到任务数:", pendingTasks ? pendingTasks.length : 0);
    if (pendingTasks && pendingTasks.length > 0) {
      // 为每个任务初始化选中状态
      let taskList = pendingTasks.map(task => ({
        ...task,
        confidencePercent: task.confidence ? (task.confidence * 100).toFixed(0) : 0
      }));

      // 将 subject 是 "unknown" 的任务排在最前面
      const unknownTasks = taskList.filter(t => t.subject === "unknown");
      const otherTasks = taskList.filter(t => t.subject !== "unknown");
      taskList = [...unknownTasks, ...otherTasks];

      this.setData({ taskList });

      // 自动生成所有已识别任务的 PDF
      await this.autoGeneratePDFs(taskList, userId);
    }
  },

  async autoGeneratePDFs(taskList, userId) {
    // 找出已识别但未生成 PDF 的任务
    const tasksToGenerate = taskList.filter(t =>
      t.status === "recognized" && t.subject && t.month && t.voucherNo
    );

    if (tasksToGenerate.length === 0) {
      return;
    }

    wx.showLoading({ title: "正在生成PDF..." });

    try {
      for (const task of tasksToGenerate) {
        await this.retryWithBackoff(
          () => confirmGenerate(task.taskId, {
            subject: task.subject,
            month: task.month,
            voucherNo: task.voucherNo
          }, userId),
          3
        );
      }

      // 更新本地存储
      const pendingTasks = wx.getStorageSync("pendingTasks") || [];
      const updatedTasks = pendingTasks.map(t => {
        if (tasksToGenerate.find(g => g.taskId === t.taskId)) {
          return { ...t, status: "pdf_generated" };
        }
        return t;
      });
      wx.setStorageSync("pendingTasks", updatedTasks);

      // 刷新列表
      let newTaskList = updatedTasks.map(task => ({
        ...task,
        confidencePercent: task.confidence ? (task.confidence * 100).toFixed(0) : 0
      }));
      const unknownTasks = newTaskList.filter(t => t.subject === "unknown");
      const otherTasks = newTaskList.filter(t => t.subject !== "unknown");
      newTaskList = [...unknownTasks, ...otherTasks];

      this.setData({ taskList: newTaskList });

      wx.showToast({
        title: `已生成 ${tasksToGenerate.length} 个PDF`,
        icon: "success"
      });
    } catch (error) {
      console.error("自动生成PDF失败:", error);
      wx.showToast({
        title: "部分PDF生成失败",
        icon: "none"
      });
    } finally {
      wx.hideLoading();
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

  // 确认单个任务
  async confirmOneTask(e) {
    const index = e.currentTarget.dataset.index;
    const taskId = e.currentTarget.dataset.taskid;
    const { taskList, userId } = this.data;
    const task = taskList[index];

    // 检查信息是否完整
    if (!task.subject || !task.month || !task.voucherNo) {
      wx.showToast({
        title: "请填写完整信息",
        icon: "none"
      });
      return;
    }

    // 更新状态为生成中
    const newTaskList = [...taskList];
    newTaskList[index] = { ...task, status: "confirmed" };
    this.setData({ taskList: newTaskList });

    try {
      await this.retryWithBackoff(
        () => confirmGenerate(taskId, {
          subject: task.subject,
          month: task.month,
          voucherNo: task.voucherNo
        }, userId),
        3
      );

      // 更新状态为已生成
      const updatedTaskList = [...this.data.taskList];
      updatedTaskList[index] = { ...updatedTaskList[index], status: "pdf_generated" };
      this.setData({ taskList: updatedTaskList });

      // 更新本地存储
      const pendingTasks = wx.getStorageSync("pendingTasks") || [];
      const updatedTasks = pendingTasks.map(t =>
        t.taskId === taskId ? { ...t, status: "pdf_generated" } : t
      );
      wx.setStorageSync("pendingTasks", updatedTasks);

      wx.showToast({
        title: "生成成功",
        icon: "success"
      });
    } catch (error) {
      // 生成失败，恢复状态
      const restoredTaskList = [...this.data.taskList];
      restoredTaskList[index] = { ...restoredTaskList[index], status: "recognized" };
      this.setData({ taskList: restoredTaskList });

      wx.showToast({
        title: "生成失败",
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
            url: "/pages/present/present"
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
    const { taskList, selectedTasks } = this.data;

    // 只选择已生成 PDF 的任务
    const tasksToDownload = taskList.filter((task, index) => selectedTasks[index] && task.status === "pdf_generated");

    if (tasksToDownload.length === 0) {
      wx.showToast({
        title: "请选择已生成PDF的任务",
        icon: "none"
      });
      return;
    }

    // 保存选中的任务用于下载页面
    const downloadTasks = tasksToDownload.map(t => ({
      taskId: t.taskId,
      pdfName: t.fileNamePreview || "凭证.pdf",
      pdfUrl: t.pdfUrl || ""
    }));
    wx.setStorageSync("selectedTasksForDownload", downloadTasks);

    // 跳转到下载页面
    wx.navigateTo({
      url: "/pages/present/present"
    });
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
