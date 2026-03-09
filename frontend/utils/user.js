function generateUserId() {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2, 10);
  return `user_${timestamp}${random}`;
}

function normalizeUserId(userId) {
  return typeof userId === "string" ? userId.trim() : "";
}

function getLocalUserId() {
  return normalizeUserId(wx.getStorageSync("userId"));
}

function ensureLocalUserId() {
  const existingUserId = getLocalUserId();
  if (existingUserId) {
    return existingUserId;
  }

  const userId = generateUserId();
  wx.setStorageSync("userId", userId);
  return userId;
}

module.exports = {
  ensureLocalUserId,
  getLocalUserId,
};
