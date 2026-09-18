// utils/request.js
import { BASE_URL } from './config.js';
import { getToken, reLogin } from './auth.js';

export function request(url, method = 'GET', data = {}) {
  return new Promise((resolve, reject) => {
    _doRequest(url, method, data, true).then(resolve).catch(reject);
  });
}

function _doRequest(url, method, data, allowRetry) {
  return new Promise((resolve, reject) => {
    const token = getToken();

    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      timeout: 60000,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': 'Bearer ' + token } : {})
      },
      success: async (res) => {
        if (res.statusCode === 401 && allowRetry) {
          try {
            await reLogin();
            const retry = await _doRequest(url, method, data, false);
            resolve(retry);
          } catch (e) {
            reject(new Error('登录已失效，请重启小程序'));
          }
          return;
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const msg = (res.data && res.data.detail) || JSON.stringify(res.data);

          // 428 = 需要配置 Embedding Key（知识库）
          if (res.statusCode === 428) {
            wx.showModal({
              title: '需要配置知识库',
              content: msg,
              confirmText: '去配置',
              success: (r) => {
                if (r.confirm) {
                  wx.navigateTo({ url: '/pages/setup/setup' });
                }
              }
            });
          }

          // 400 + "请先" = 需要配置 AI Key
          if (res.statusCode === 400 && msg.indexOf('请先') !== -1) {
            wx.showModal({
              title: '需要配置 API',
              content: msg + '\n\n是否现在去配置？',
              confirmText: '去配置',
              success: (r) => {
                if (r.confirm) {
                  wx.navigateTo({ url: '/pages/setup/setup' });
                }
              }
            });
          }

          reject(new Error(`HTTP ${res.statusCode}: ${msg}`));
        }
      },
      fail: (err) => {
        reject(new Error('网络请求失败: ' + err.errMsg));
      }
    });
  });
}