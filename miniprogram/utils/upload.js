// utils/upload.js
import { BASE_URL } from './config.js';
import { getToken, reLogin } from './auth.js';

/**
 * 上传文件：自动带 token，遇到 401 自动重新登录。
 */
export function upload(url, filePath, fileName) {
  return new Promise((resolve, reject) => {
    _doUpload(url, filePath, fileName, true)
      .then(resolve)
      .catch(reject);
  });
}

function _doUpload(url, filePath, fileName, allowRetry) {
  return new Promise((resolve, reject) => {
    const token = getToken();

    wx.uploadFile({
      url: BASE_URL + url,
      filePath: filePath,
      name: 'file',
      timeout: 60000,
      header: {
        ...(token ? { 'Authorization': 'Bearer ' + token } : {})
      },
      formData: {
        original_filename: fileName
      },
      success: async (res) => {
        // 401 → 重新登录并重试
        if (res.statusCode === 401 && allowRetry) {
          try {
            await reLogin();
            const retry = await _doUpload(url, filePath, fileName, false);
            resolve(retry);
          } catch (e) {
            reject(new Error('登录已失效，请重启小程序'));
          }
          return;
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data));
          } catch (e) {
            reject(new Error('响应解析失败: ' + res.data));
          }
        } else {
          let msg = res.data;
          try { msg = JSON.parse(res.data).detail; } catch (e) {}
          reject(new Error(`HTTP ${res.statusCode}: ${msg}`));
        }
      },
      fail: (err) => {
        reject(new Error('上传失败: ' + err.errMsg));
      }
    });
  });
}