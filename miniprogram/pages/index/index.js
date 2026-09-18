// pages/index/index.js
import { request } from '../../utils/request.js';
import { upload } from '../../utils/upload.js';
import { getUser, getToken } from '../../utils/auth.js';
import { parseMarkdown } from '../../utils/markdown.js';
import { BASE_URL } from '../../utils/config.js';
import { getSafeAreaMetrics, formatTime as formatTimeLabel } from '../../utils/ui.js';

const RAG_STORAGE_KEY = 'rag_enabled';
const recorderManager = wx.getRecorderManager();

Page({
  data: {
    statusBarHeight: 20,
    safeBottom: 0,
    userNickname: '用户',
    userInitial: '用',
    drawerOpen: false,
    drawerTab: 'sessions',
    sessions: [],
    sessionId: '',
    currentTitle: '随手一下',
    tasks: [],
    messages: [],
    inputText: '',
    sending: false,
    scrollToId: '',
    attachPanelOpen: false,

    // RAG
    ragEnabled: false,
    ragDocCount: 0,

    // 录音
    recording: false,
    voiceStatus: '正在录音...',
    voiceTimeText: '00:00'
  },

  onLoad() {
    const cachedRag = wx.getStorageSync(RAG_STORAGE_KEY);

    this.setData({
      ...getSafeAreaMetrics(),
      ragEnabled: cachedRag === true
    });

    this.loadUserInfo();
    this.loadSessions();
    this.loadRagStatus();
    this.setupRecorder();
  },

  onShow() {
    if (this.data.sessionId) {
      this.loadHistory();
    }
    this.loadRagDocCount();
  },

  // ==================== 用户信息 ====================
  loadUserInfo() {
    const user = getUser();
    if (user) {
      const nickname = user.nickname || '用户';
      this.setData({
        userNickname: nickname,
        userInitial: nickname.charAt(0)
      });
    }
  },

  // ==================== 录音 ====================
  setupRecorder() {
    recorderManager.onStop((res) => {
      clearInterval(this.recordTimer);

      if (this.recordingCancelled) {
        this.recordingCancelled = false;
        return;
      }

      const duration = Math.round(res.duration / 1000);

      if (duration < 1) {
        this.setData({ recording: false });
        wx.showToast({ title: '录音太短', icon: 'none' });
        return;
      }

      this.setData({ recording: false, voiceStatus: '正在识别...' });
      wx.showLoading({ title: '识别中...', mask: true });
      this.transcribeAudio(res.tempFilePath);
    });

    recorderManager.onError(() => {
      clearInterval(this.recordTimer);
      this.setData({ recording: false });
      wx.showToast({ title: '录音失败', icon: 'none' });
    });
  },

  transcribeAudio(filePath) {
    wx.uploadFile({
      url: BASE_URL + '/smart/transcribe',
      filePath: filePath,
      name: 'file',
      header: { 'Authorization': 'Bearer ' + getToken() },
      success: (res) => {
        wx.hideLoading();
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode === 200 && data.text) {
            const current = this.data.inputText;
            const newText = current ? (current + ' ' + data.text) : data.text;
            this.setData({ inputText: newText });
            wx.showToast({ title: '识别完成', icon: 'success' });
          } else {
            wx.showToast({ title: data.detail || '识别失败', icon: 'none' });
          }
        } catch (e) {
          wx.showToast({ title: '解析失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '网络失败', icon: 'none' });
      }
    });
  },

  startVoiceRecord() {
    this.recordSeconds = 0;
    this.recordingCancelled = false;
    this.setData({
      recording: true,
      voiceStatus: '正在录音...',
      voiceTimeText: '00:00'
    });

    recorderManager.start({
      duration: 60 * 1000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3'
    });

    this.recordTimer = setInterval(() => {
      this.recordSeconds++;
      const m = String(Math.floor(this.recordSeconds / 60)).padStart(2, '0');
      const s = String(this.recordSeconds % 60).padStart(2, '0');
      this.setData({ voiceTimeText: `${m}:${s}` });
    }, 1000);
  },

  onStopVoice() {
    recorderManager.stop();
  },

  onCancelVoice() {
    clearInterval(this.recordTimer);
    this.recordingCancelled = true;
    recorderManager.stop();
    this.setData({ recording: false });
  },

  noop() {},

  // ==================== RAG ====================
  async loadRagDocCount() {
    try {
      const docs = await request('/rag/documents', 'GET');
      this.setData({ ragDocCount: (docs.documents || []).length });
    } catch (e) {
      console.error('加载知识库文档失败:', e);
    }
  },

  async loadRagStatus() {
    await this.loadRagDocCount();
    const cachedRag = wx.getStorageSync(RAG_STORAGE_KEY);
    if (cachedRag !== '' && cachedRag !== undefined && cachedRag !== null) {
      return;
    }
    try {
      const cfg = await request('/user/config', 'GET');
      const enabled = !!cfg.is_embedding_configured && (cfg.rag_enabled !== false);
      wx.setStorageSync(RAG_STORAGE_KEY, enabled);
      this.setData({ ragEnabled: enabled });
    } catch (err) {
      console.error('加载 RAG 状态失败:', err);
    }
  },

  onToggleRag() {
    const newState = !this.data.ragEnabled;
    if (newState && this.data.ragDocCount === 0) {
      wx.showModal({
        title: '知识库是空的',
        content: '先在「知识库」里上传文档，AI 才能检索',
        confirmText: '去上传',
        success: (res) => {
          if (res.confirm) {
            this.setData({ drawerOpen: false });
            wx.navigateTo({ url: '/pages/rag/rag' });
          }
        }
      });
      return;
    }
    this.setData({ ragEnabled: newState });
    wx.setStorageSync(RAG_STORAGE_KEY, newState);
    wx.showToast({
      title: newState ? '知识库已启用' : '知识库已关闭',
      icon: 'none'
    });
  },

  onGoRagDocs() {
    wx.navigateTo({ url: '/pages/rag/rag' });
  },

  // ==================== 会话 ====================
  async loadSessions() {
    try {
      const res = await request('/sessions', 'GET');
      const sessions = res.sessions.map(s => ({
        ...s,
        timeLabel: this.formatTime(s.updated_at)
      }));
      if (sessions.length === 0) {
        const created = await request('/sessions', 'POST', { title: '新对话' });
        sessions.push({ ...created, timeLabel: '刚刚' });
        this.setData({
          sessions,
          sessionId: created.id,
          currentTitle: '随手一下'
        });
        return;
      }
      this.setData({
        sessions,
        sessionId: sessions[0].id,
        currentTitle: sessions[0].title
      });
      this.loadHistory();
    } catch (err) {
      console.error('加载会话失败:', err);
    }
  },

  async onNewChat() {
    try {
      const created = await request('/sessions', 'POST', { title: '新对话' });
      const newSession = { ...created, timeLabel: '刚刚' };
      this.setData({
        sessions: [newSession, ...this.data.sessions],
        sessionId: created.id,
        currentTitle: '随手一下',
        messages: [],
        drawerOpen: false,
        attachPanelOpen: false
      });
    } catch (err) {
      wx.showToast({ title: '创建失败', icon: 'none' });
    }
  },

  onSelectSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const target = this.data.sessions.find(s => s.id === sessionId);
    if (!target) return;
    this.setData({
      sessionId,
      currentTitle: target.title,
      drawerOpen: false,
      messages: []
    });
    this.loadHistory();
  },

  onLongPressSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const target = this.data.sessions.find(s => s.id === sessionId);
    if (!target) return;
    wx.showActionSheet({
      itemList: ['重命名', '删除'],
      success: (res) => {
        if (res.tapIndex === 0) this.renameSession(sessionId, target.title);
        if (res.tapIndex === 1) this.deleteSession(sessionId);
      }
    });
  },

  renameSession(sessionId, oldTitle) {
    wx.showModal({
      title: '重命名',
      editable: true,
      placeholderText: '输入新标题',
      content: oldTitle,
      success: async (res) => {
        if (!res.confirm || !res.content.trim()) return;
        try {
          await request(`/sessions/${sessionId}`, 'PUT', { title: res.content.trim() });
          this.loadSessions();
          if (sessionId === this.data.sessionId) {
            this.setData({ currentTitle: res.content.trim() });
          }
        } catch (err) {
          wx.showToast({ title: '重命名失败', icon: 'none' });
        }
      }
    });
  },

  deleteSession(sessionId) {
    wx.showModal({
      title: '删除对话',
      content: '确定删除这个对话吗？',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request(`/sessions/${sessionId}`, 'DELETE');
          const remaining = this.data.sessions.filter(s => s.id !== sessionId);
          if (sessionId === this.data.sessionId) {
            if (remaining.length > 0) {
              this.setData({
                sessions: remaining,
                sessionId: remaining[0].id,
                currentTitle: remaining[0].title,
                messages: []
              });
              this.loadHistory();
            } else {
              this.loadSessions();
            }
          } else {
            this.setData({ sessions: remaining });
          }
          wx.showToast({ title: '已删除', icon: 'success' });
        } catch (err) {
          wx.showToast({ title: '删除失败', icon: 'none' });
        }
      }
    });
  },

  // ==================== 任务 ====================
  async loadTasks() {
    try {
      const res = await request('/tasks?limit=30', 'GET');
      const tasks = res.items.map(t => ({
        ...t,
        timeLabel: this.formatTime(t.created_at)
      }));
      this.setData({ tasks });
    } catch (err) {
      console.error('加载任务失败:', err);
    }
  },

  onSelectTask(e) {
    const task = e.currentTarget.dataset.task;
    wx.setStorageSync('last_result', {
      taskType: task.task_type,
      inputText: task.input_text,
      outputText: task.output_text || '（无内容）'
    });
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/result/result' });
  },

  onSwitchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ drawerTab: tab });
    if (tab === 'tasks') this.loadTasks();
  },

  // ==================== 抽屉 ====================
  openDrawer() {
    this.setData({ drawerOpen: true, attachPanelOpen: false });
    if (this.data.drawerTab === 'tasks') {
      this.loadTasks();
    } else {
      this.loadSessions();
    }
  },

  closeAll() {
    this.setData({ drawerOpen: false, attachPanelOpen: false });
  },

  openAttachPanel() {
    this.setData({ attachPanelOpen: true, drawerOpen: false });
  },

  closeAttachPanel() {
    this.setData({ attachPanelOpen: false });
  },

  onTapRag() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/rag/rag' });
  },

  onTapToolbox() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/toolbox/toolbox' });
  },

  onTapCareer() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/career/career' });
  },

  onTapNotes() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/notes/list/list' });
  },

  onTapTools() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/tools/tools' });
  },

  onTapMcp() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/mcp/mcp' });
  },

  onTapSettings() {
    this.setData({ drawerOpen: false });
    wx.navigateTo({ url: '/pages/profile/profile' });
  },

  // ==================== 消息 ====================
  async loadHistory() {
    if (!this.data.sessionId) return;
    try {
      const res = await request(`/chat/history?session_id=${this.data.sessionId}`, 'GET');
      const messages = res.messages.map(m => ({
        ...m,
        nodes: m.role === 'assistant' ? parseMarkdown(m.content) : []
      }));
      this.setData({ messages });
      this.scrollToBottom();
    } catch (err) {
      console.error('加载历史失败:', err);
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  async onSend() {
    const text = this.data.inputText.trim();
    if (!text || this.data.sending) return;

    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: text,
      nodes: []
    };
    this.setData({
      messages: this.data.messages.concat([tempUserMsg]),
      inputText: '',
      sending: true
    });
    this.scrollToBottom();

    try {
      const res = await request('/chat/send', 'POST', {
        session_id: this.data.sessionId,
        content: text,
        use_rag: this.data.ragEnabled
      });

      const realMessages = this.data.messages.filter(m => m.id !== tempUserMsg.id);
      realMessages.push({
        id: 'user-' + Date.now(),
        role: 'user',
        content: text,
        nodes: []
      });

      let replyContent = res.reply;
      if (res.rag_used && res.rag_sources && res.rag_sources.length > 0) {
        replyContent += "\n\n---\n📚 参考了 " + res.rag_sources.length + " 个片段";
      }

      realMessages.push({
        id: res.message_id,
        role: 'assistant',
        content: replyContent,
        nodes: parseMarkdown(replyContent)
      });

      this.setData({ messages: realMessages, sending: false });
      this.scrollToBottom();

      const sid = this.data.sessionId;
      const target = this.data.sessions.find(s => s.id === sid);
      if (target && target.title === '新对话') {
        this.loadSessions();
      }
    } catch (err) {
      console.error('发送失败:', err);
      this.setData({ sending: false });
      wx.showToast({ title: '发送失败', icon: 'none' });
    }
  },

  scrollToBottom() {
    setTimeout(() => {
      const msgs = this.data.messages;
      if (msgs.length > 0) {
        this.setData({ scrollToId: 'msg-' + msgs[msgs.length - 1].id });
      }
    }, 100);
  },

  // ==================== 附件 ====================
  onTapCamera() {
    this.closeAttachPanel();
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      camera: 'back',
      success: (res) => {
        const file = res.tempFiles[0];
        wx.compressImage({
          src: file.tempFilePath,
          quality: 70,
          success: (c) => this.doUploadImage({ path: c.tempFilePath, name: 'photo.jpg' }),
          fail: () => this.doUploadImage({ path: file.tempFilePath, name: 'photo.jpg' })
        });
      },
      fail: (err) => {
        if (err.errMsg && err.errMsg.indexOf('cancel') !== -1) return;
        wx.showToast({ title: '选择图片失败', icon: 'none' });
      }
    });
  },

  async doUploadImage(file) {
    this.setData({
      messages: this.data.messages.concat([{
        id: 'user-img-' + Date.now(),
        role: 'user',
        content: '📷 [图片] ' + file.name,
        nodes: []
      }]),
      sending: true
    });
    this.scrollToBottom();

    try {
      const res = await upload('/images/upload', file.path, file.name);
      this.setData({
        messages: this.data.messages.concat([{
          id: 'ai-img-' + Date.now(),
          role: 'assistant',
          content: res.ai_output,
          nodes: parseMarkdown(res.ai_output)
        }]),
        sending: false
      });
      this.scrollToBottom();
    } catch (err) {
      this.setData({
        messages: this.data.messages.concat([{
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: '图片处理失败：' + err.message,
          nodes: []
        }]),
        sending: false
      });
      this.scrollToBottom();
    }
  },

  onTapFile() {
    this.closeAttachPanel();
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'docx', 'txt', 'md'],
      success: (res) => this.doUpload(res.tempFiles[0]),
      fail: (err) => {
        if (err.errMsg && err.errMsg.indexOf('cancel') !== -1) return;
        wx.showToast({ title: '选择文件失败', icon: 'none' });
      }
    });
  },

  async doUpload(file) {
    this.setData({
      messages: this.data.messages.concat([{
        id: 'user-file-' + Date.now(),
        role: 'user',
        content: '📄 [文件] ' + file.name,
        nodes: []
      }]),
      sending: true
    });
    this.scrollToBottom();

    try {
      const res = await upload('/files/upload', file.path, file.name);
      this.setData({
        messages: this.data.messages.concat([{
          id: 'ai-file-' + Date.now(),
          role: 'assistant',
          content: res.ai_output,
          nodes: parseMarkdown(res.ai_output)
        }]),
        sending: false
      });
      this.scrollToBottom();
      this.loadRagDocCount();
    } catch (err) {
      this.setData({
        messages: this.data.messages.concat([{
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: '文件处理失败：' + err.message,
          nodes: []
        }]),
        sending: false
      });
      this.scrollToBottom();
    }
  },

  onTapVoice() {
    this.closeAttachPanel();
    wx.authorize({
      scope: 'scope.record',
      success: () => this.startVoiceRecord(),
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

  // ==================== 工具方法 ====================
  formatTime(isoString) {
    return formatTimeLabel(isoString);
  }
})