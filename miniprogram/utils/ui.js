// utils/ui.js —— 跨页面共用的界面辅助函数

/**
 * 读取状态栏高度和底部安全区高度
 * 优先用新版 API，旧基础库回退到 getSystemInfoSync
 * @returns {{ statusBarHeight: number, safeBottom: number }}
 */
export function getSafeAreaMetrics() {
  try {
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const statusBarHeight = win.statusBarHeight || 20;
    const screenHeight = win.screenHeight || win.windowHeight || 0;
    const safeArea = win.safeArea;

    // 安全区底边距 = 屏幕底 - 安全区底（全面屏手势条高度）
    let safeBottom = 0;
    if (safeArea && screenHeight) {
      safeBottom = Math.max(0, screenHeight - safeArea.bottom);
    }

    return { statusBarHeight, safeBottom };
  } catch (e) {
    return { statusBarHeight: 20, safeBottom: 0 };
  }
}

/**
 * 把时间戳格式化成相对时间标签
 * 一小时内显示分钟、当天显示时分、今年显示月日、跨年显示年月日
 * @param {string|number|Date} value 时间戳或可被 Date 解析的值
 * @returns {string}
 */
export function formatTime(value) {
  if (!value) return '';

  const date = value instanceof Date ? value : new Date(value);
  if (isNaN(date.getTime())) return '';

  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;

  const pad = (n) => (n < 10 ? '0' + n : '' + n);

  const isToday = date.toDateString() === now.toDateString();
  if (isToday) return `${pad(date.getHours())}:${pad(date.getMinutes())}`;

  const isThisYear = date.getFullYear() === now.getFullYear();
  if (isThisYear) return `${date.getMonth() + 1}月${date.getDate()}日`;

  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`;
}

/**
 * 安全关闭 loading，避免 hideLoading 未配对时的警告
 */
export function hideLoadingSafe() {
  try {
    wx.hideLoading();
  } catch (e) {
    // 没有正在显示的 loading 时忽略
  }
}
