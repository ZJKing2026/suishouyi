// utils/markdown.js
// 轻量 Markdown 解析器：把 AI 输出转成 rich-text 可用节点
// 支持：# 标题、**加粗**、- 列表、1. 有序列表、段落、空行

const STYLES = {
  h1: 'font-size: 36rpx; font-weight: 700; margin: 20rpx 0 12rpx;',
  h2: 'font-size: 32rpx; font-weight: 600; margin: 16rpx 0 10rpx;',
  h3: 'font-size: 30rpx; font-weight: 600; margin: 12rpx 0 8rpx;',
  p: 'font-size: 28rpx; line-height: 1.8; margin: 8rpx 0;',
  li: 'font-size: 28rpx; line-height: 1.8; margin: 6rpx 0; padding-left: 20rpx;',
  br: 'height: 16rpx;',
  bold: 'font-weight: 600;',
};

/**
 * 把 Markdown 文本解析成 rich-text 的 nodes 数组
 */
export function parseMarkdown(text) {
  if (!text) return [];

  const nodes = [];
  const lines = text.split('\n');

  for (let raw of lines) {
    const line = raw.trim();

    // 空行
    if (!line) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.br },
        children: []
      });
      continue;
    }

    // ### 三级标题
    if (line.startsWith('### ')) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.h3 },
        children: parseInline(line.slice(4))
      });
      continue;
    }

    // ## 二级标题
    if (line.startsWith('## ')) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.h2 },
        children: parseInline(line.slice(3))
      });
      continue;
    }

    // # 一级标题
    if (line.startsWith('# ')) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.h1 },
        children: parseInline(line.slice(2))
      });
      continue;
    }

    // - 或 * 无序列表
    if (/^[-*]\s/.test(line)) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.li },
        children: [
          { type: 'text', text: '• ' },
          ...parseInline(line.slice(2))
        ]
      });
      continue;
    }

    // 1. 有序列表
    const orderedMatch = line.match(/^(\d+)\.\s(.*)$/);
    if (orderedMatch) {
      nodes.push({
        type: 'node',
        name: 'p',
        attrs: { style: STYLES.li },
        children: [
          { type: 'text', text: orderedMatch[1] + '. ' },
          ...parseInline(orderedMatch[2])
        ]
      });
      continue;
    }

    // 普通段落
    nodes.push({
      type: 'node',
      name: 'p',
      attrs: { style: STYLES.p },
      children: parseInline(line)
    });
  }

  return nodes;
}

/**
 * 解析行内语法：**加粗**、`代码`
 */
function parseInline(text) {
  const result = [];
  // 先按 **粗体** 切分
  const parts = text.split(/(\*\*[^*]+\*\*)/g);

  for (const part of parts) {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      result.push({
        type: 'text',
        text: part.slice(2, -2),
        attrs: { style: STYLES.bold }
      });
    } else if (part) {
      result.push({ type: 'text', text: part });
    }
  }

  return result;
}