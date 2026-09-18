// pages/history/history.js
import { request } from '../../utils/request.js';

const PAGE_SIZE = 10;   // 每页 10 条

Page({
  data: {
    tasks: [],        // 已加载的任务列表
    loading: false,   // 是否正在加载
    noMore: false,    // 是否已经没有更多
    offset: 0         // 分页偏移
  },

  onLoad() {
    this.loadMore(true);
  },

  // 下拉刷新（微信自带的下拉动作）
  onPullDownRefresh() {
    this.setData({ tasks: [], offset: 0, noMore: false });
    this.loadMore(true).then(() => wx.stopPullDownRefresh());
  },

  // 上拉加载更多（页面触底时触发）
  onReachBottom() {
    if (this.data.noMore || this.data.loading) return;
    this.loadMore(false);
  },

  /**
   * 加载任务
   * @param {boolean} reset 是否重置（第一次加载或下拉刷新）
   */
  async loadMore(reset) {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      const offset = reset ? 0 : this.data.offset;
      const res = await request(`/tasks?limit=${PAGE_SIZE}&offset=${offset}`, 'GET');

      // 合并新旧数据
      const newTasks = reset ? res.items : this.data.tasks.concat(res.items);

      // 判断是否还有更多：已加载数量 >= 总数
      const noMore = newTasks.length >= res.total;

      // 格式化时间：2026-09-15T14:57:35.023824 → 2026-09-15 14:57
      const formatted = newTasks.map(t => ({
        ...t,
        created_at: t.created_at.replace('T', ' ').slice(0, 16)
      }));

      this.setData({
        tasks: formatted,
        offset: offset + PAGE_SIZE,
        noMore: noMore,
        loading: false
      });
    } catch (err) {
      console.error('加载失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  }
})