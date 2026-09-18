// pages/notes/record/record.js
import { upload } from '../../../utils/upload.js';

const recorderManager = wx.getRecorderManager();

Page({
  data: {
    isRecording: false,
    uploading: false,
    timeText: '00:00',
    statusHint: '准备好后，点击下方按钮'
  },

  onLoad() {
    this.recordTimer = null;
    this.recordSeconds = 0;

    // 监听录音结束
    recorderManager.onStop((res) => {
      clearInterval(this.recordTimer);
      const duration = Math.round(res.duration / 1000);

      if (duration < 2) {
        wx.showToast({ title: '录音太短', icon: 'none' });
        this.setData({ isRecording: false, statusHint: '准备好后，点击下方按钮' });
        return;
      }

      this.uploadAudio(res.tempFilePath, res.duration);
    });

    // 监听录音错误
    recorderManager.onError((err) => {
      console.error('录音失败:', err);
      clearInterval(this.recordTimer);
      this.setData({ isRecording: false });
      wx.showToast({ title: '录音失败', icon: 'none' });
    });
  },

  onUnload() {
    if (this.data.isRecording) {
      recorderManager.stop();
    }
    clearInterval(this.recordTimer);
  },

  onToggleRecord() {
    if (this.data.uploading) return;

    if (this.data.isRecording) {
      recorderManager.stop();
      this.setData({ isRecording: false, statusHint: '正在处理...' });
      return;
    }

    // 申请权限并开始
    wx.authorize({
      scope: 'scope.record',
      success: () => this.startRecord(),
      fail: () => {
        wx.showModal({
          title: '需要麦克风权限',
          content: '请在设置中开启麦克风权限',
          confirmText: '去设置',
          success: (res) => {
            if (res.confirm) wx.openSetting();
          }
        });
      }
    });
  },

  startRecord() {
    this.recordSeconds = 0;
    this.setData({
      isRecording: true,
      timeText: '00:00',
      statusHint: '正在录音...'
    });

    recorderManager.start({
      duration: 30 * 60 * 1000,    // 最长 30 分钟
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3'
    });

    this.recordTimer = setInterval(() => {
      this.recordSeconds++;
      this.setData({ timeText: this.formatTime(this.recordSeconds) });
    }, 1000);
  },

  formatTime(seconds) {
    const m = String(Math.floor(seconds / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    return `${m}:${s}`;
  },

  async uploadAudio(filePath, duration) {
    this.setData({
      uploading: true,
      statusHint: '上传并处理中...'
    });

    try {
      const fileName = `recording_${Date.now()}.mp3`;
      const res = await upload('/notes/upload', filePath, fileName);

      this.setData({ uploading: false });

      // 跳转到详情页
      wx.redirectTo({
        url: `/pages/notes/detail/detail?id=${res.id}`
      });
    } catch (err) {
      console.error('上传失败:', err);
      this.setData({
        uploading: false,
        statusHint: '上传失败，请重试'
      });
      wx.showModal({
        title: '处理失败',
        content: err.message,
        showCancel: false
      });
    }
  },

  onGoList() {
    wx.navigateTo({ url: '/pages/notes/list/list' });
  }
})
