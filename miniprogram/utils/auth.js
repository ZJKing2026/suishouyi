// utils/auth.js
import { BASE_URL } from './config.js';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// ==================== 读本地 ====================
export function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || '';
}

export function getUser() {
  return wx.getStorageSync(USER_KEY) || null;
}

function saveAuth(token, user) {
  wx.setStorageSync(TOKEN_KEY, token);
  wx.setStorageSync(USER_KEY, user);
}

export function clearAuth() {
  wx.removeStorageSync(TOKEN_KEY);
  wx.removeStorageSync(USER_KEY);
}

// ==================== 微信登录 ====================
/**
 * 调用 wx.login 拿 code，然后 POST 到后端换 token。
 * 返回 Promise，resolve 时 token 已存本地。
 */
function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (loginRes) => {
        if (!loginRes.code) {
          reject(new Error('wx.login 没有返回 code'));
          return;
        }

        try {
          // 用 code 换 token
          const res = await new Promise((res2, rej2) => {
            wx.request({
              url: BASE_URL + '/auth/wx-login',
              method: 'POST',
              header: { 'Content-Type': 'application/json' },
              data: {
                code: loginRes.code,
                nickname: '',
                avatar: ''
              },
              success: (r) => res2(r),
              fail: (e) => rej2(e)
            });
          });

          if (res.statusCode !== 200) {
            reject(new Error('登录失败: HTTP ' + res.statusCode));
            return;
          }

          const { token, user } = res.data;
          saveAuth(token, user);
          resolve({ token, user });
        } catch (e) {
          reject(e);
        }
      },
      fail: (err) => reject(new Error('wx.login 失败: ' + err.errMsg))
    });
  });
}

// ==================== 确保已登录 ====================
/**
 * 保证本地有可用 token：
 * - 有 token → 直接返回
 * - 没 token → 走 wx.login
 */
export async function ensureLogin() {
  const token = getToken();
  if (token) {
    return { token, user: getUser() };
  }
  return await wxLogin();
}

// ==================== 强制重新登录 ====================
export async function reLogin() {
  clearAuth();
  return await wxLogin();
}