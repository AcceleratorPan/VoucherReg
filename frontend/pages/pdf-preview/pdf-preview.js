const { BASE_URL } = require("../../config");
const { clearAllResultState } = require("../../utils/result-session");

Page({
  data: {
    pdfUrl: "",
    fileName: "",
    tempFilePath: ""
  },

  onLoad(options) {
    const pdfUrl = decodeURIComponent(options.pdfUrl || "");
    const fileName = decodeURIComponent(options.fileName || "");
    
    this.setData({
      pdfUrl: pdfUrl,
      fileName: fileName
    });
    
    this.openPDF();
  },

  onShareAppMessage() {
    const { fileName } = this.data;
    return {
      title: fileName ? `凭证：${fileName}` : "凭证PDF",
      path: "/pages/index/index",
      imageUrl: ""
    };
  },

  openPDF() {
    wx.showLoading({
      title: "正在加载PDF...",
    });

    const fullPdfUrl = this.data.pdfUrl.startsWith("http") 
      ? this.data.pdfUrl 
      : `${BASE_URL}${this.data.pdfUrl}`;

    const fileName = this.data.fileName || "凭证.pdf";
    
    wx.downloadFile({
      url: fullPdfUrl,
      filePath: wx.env.USER_DATA_PATH + "/" + fileName,
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          this.setData({
            tempFilePath: res.filePath || res.tempFilePath
          });
          
          wx.openDocument({
            filePath: res.filePath || res.tempFilePath,
            fileType: "pdf",
            showMenu: true,
            success: function(res) {
              console.log("PDF打开成功");
              wx.showToast({
                title: "PDF已打开，可在查看中保存",
                icon: "none",
                duration: 3000
              });
            },
            fail: function(err) {
              console.error("打开PDF失败:", err);
              wx.showToast({
                title: "打开PDF失败",
                icon: "none"
              });
            }
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error("下载PDF失败:", err);
        wx.showToast({
          title: "下载PDF失败",
          icon: "none"
        });
      }
    });
  },

  goHome() {
    clearAllResultState();

    // 返回应用首页（home页面）
    wx.reLaunch({
      url: "/pages/home/home"
    });
  },

  nextProcess() {
    wx.reLaunch({
      url: "/pages/index/index"
    });
  },

  goHistory() {
    wx.redirectTo({
      url: "/pages/history/history"
    });
  }
});
