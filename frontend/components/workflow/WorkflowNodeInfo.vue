<template>
  <div class="flex flex-col h-full">
    <!-- 节点头部 - 精简版 -->
    <div class="flex-shrink-0 px-4 py-4 border-b border-slate-200">
      <div class="flex items-start gap-3">
        <!-- 节点图标 -->
        <div
          class="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center shadow-sm"
          :class="getNodeIconBgClass(node.data?.type)"
        >
          <span class="text-xl">{{ getNodeIcon(node.data?.type) }}</span>
        </div>

        <div class="flex-1 min-w-0">
          <h4 class="text-sm font-semibold text-slate-900 mb-1 truncate">
            {{ node.data?.label }}
          </h4>
          <div class="flex items-center gap-2 flex-wrap">
            <span
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
              :class="getNodeTypeClass(node.data?.type)"
            >
              {{ node.data?.type }}
            </span>
          </div>
        </div>
      </div>

      <!-- 节点描述 -->
      <div v-if="node.data?.description" class="mt-3 text-xs text-slate-600 leading-relaxed">
        {{ node.data.description }}
      </div>

      <!-- 节点 ID -->
      <div class="mt-3">
        <div class="flex items-center gap-2 px-2.5 py-1.5 bg-slate-50 rounded text-xs font-mono text-slate-600 border border-slate-200">
          <span class="flex-1 truncate">{{ node.id }}</span>
          <button
            @click="copyNodeId"
            class="flex-shrink-0 p-1 text-slate-400 hover:text-slate-700 hover:bg-white rounded transition-all"
            title="复制 ID"
          >
            <ClipboardDocumentIcon class="w-3.5 h-3.5"/>
          </button>
        </div>
      </div>
    </div>

    <!-- 节点相关对话 - 可展开 -->
    <div class="flex-1 overflow-hidden flex flex-col">
      <div class="flex-shrink-0 px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <ChatBubbleLeftRightIcon class="w-4 h-4 text-slate-500"/>
            <h5 class="text-xs font-semibold text-slate-700">相关对话</h5>
          </div>
          <span class="text-xs font-medium text-slate-500">{{ sortedMessages.length }} 条</span>
        </div>
      </div>

      <div v-if="sortedMessages.length > 0" class="flex-1 overflow-y-auto custom-scrollbar">
        <div class="px-4 py-3 space-y-2">
          <div
            v-for="(msg, index) in sortedMessages"
            :key="msg.id"
            class="border rounded-lg overflow-hidden transition-all"
            :class="{
              'border-blue-200 bg-blue-50/50': msg.type === 'user',
              'border-slate-200 bg-white': msg.type === 'ai',
              'border-blue-200 bg-blue-50/50': msg.type === 'system' && !msg.error,
              'border-red-200 bg-red-50/50': msg.type === 'system' && msg.error,
              'border-amber-200 bg-amber-50/50': msg.type === 'tool_call'
            }"
          >
            <!-- 消息头部 - 可点击展开/收起 -->
            <button
              @click="toggleMessage(index)"
              class="w-full px-3 py-2.5 flex items-center gap-2 hover:bg-white/50 transition-colors text-left"
            >
              <div class="flex-shrink-0">
                <div
                  class="w-6 h-6 rounded flex items-center justify-center text-xs"
                  :class="{
                    'bg-blue-500 text-white': msg.type === 'user',
                    'bg-slate-500 text-white': msg.type === 'ai',
                    'bg-blue-500 text-white': msg.type === 'system' && !msg.error,
                    'bg-red-500 text-white': msg.type === 'system' && msg.error,
                    'bg-amber-500 text-white': msg.type === 'tool_call'
                  }"
                >
                  {{ getMessageIcon(msg) }}
                </div>
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-0.5">
                  <span
                    class="text-xs font-semibold"
                    :class="{
                      'text-blue-900': msg.type === 'user',
                      'text-slate-900': msg.type === 'ai',
                      'text-blue-900': msg.type === 'system' && !msg.error,
                      'text-red-900': msg.type === 'system' && msg.error,
                      'text-amber-900': msg.type === 'tool_call'
                    }"
                  >
                    {{ getMessageTypeLabel(msg.type) }}
                  </span>
                  <span class="text-[10px] text-slate-400">
                    {{ formatTime(msg.timestamp) }}
                  </span>
                </div>
                <div
                  class="text-xs text-slate-600 truncate"
                  :class="{
                    'text-blue-700': msg.type === 'user',
                    'text-slate-600': msg.type === 'ai',
                    'text-blue-700': msg.type === 'system' && !msg.error,
                    'text-red-700': msg.type === 'system' && msg.error,
                    'text-amber-700': msg.type === 'tool_call'
                  }"
                >
                  {{ msg.content }}
                </div>
              </div>

              <ChevronDownIcon
                class="flex-shrink-0 w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': expandedMessages.has(index) }"
              />
            </button>

            <!-- 消息详细内容 - 展开时显示 -->
            <div
              v-show="expandedMessages.has(index)"
              class="px-3 pb-3 border-t"
              :class="{
                'border-blue-200': msg.type === 'user',
                'border-slate-200': msg.type === 'ai',
                'border-blue-200': msg.type === 'system' && !msg.error,
                'border-red-200': msg.type === 'system' && msg.error,
                'border-amber-200': msg.type === 'tool_call'
              }"
            >
              <!-- AI 消息使用 markdown 渲染 -->
              <div 
                v-if="msg.type === 'ai'"
                class="pt-3 markdown-content text-xs leading-relaxed overflow-x-auto"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <!-- 其他消息类型使用纯文本 -->
              <div 
                v-else
                class="pt-3 text-xs leading-relaxed whitespace-pre-wrap break-words"
                :class="{
                  'text-blue-900': msg.type === 'user',
                  'text-blue-800': msg.type === 'system' && !msg.error,
                  'text-red-800': msg.type === 'system' && msg.error,
                  'text-amber-800': msg.type === 'tool_call'
                }"
              >
                {{ msg.content }}
              </div>

              <!-- 额外信息 -->
              <div v-if="msg.path || msg.metadata" class="mt-2 pt-2 border-t border-slate-200/50 text-[10px] text-slate-500 space-y-1">
                <div v-if="msg.path" class="flex items-start gap-1">
                  <span class="font-semibold">路径:</span>
                  <span>{{ msg.path }}</span>
                </div>
                <div v-if="msg.metadata?.nodes_executed" class="flex items-start gap-1">
                  <span class="font-semibold">已执行:</span>
                  <span>{{ msg.metadata.nodes_executed.join(', ') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="flex-1 flex items-center justify-center px-4 py-8">
        <div class="text-center">
          <ChatBubbleLeftRightIcon class="w-12 h-12 mx-auto text-slate-300 mb-2"/>
          <p class="text-sm text-slate-400">暂无相关对话</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, computed, watch, onMounted } from 'vue'
import {
  ClipboardDocumentIcon,
  ChatBubbleLeftRightIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'
import { ChatStoreKey } from '~/composables/useChatStore'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// 配置 marked
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.error('Highlight error:', err)
      }
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
})

// 注入聊天存储
const chatStore = inject(ChatStoreKey, null)

// 获取与当前节点相关的消息（按时间倒序）
const nodeMessages = computed(() => {
  if (!chatStore || !props.node) return []
  return chatStore.getNodeMessages(props.node.id)
})

// 按时间倒序排列
const sortedMessages = computed(() => {
  return [...nodeMessages.value].sort((a, b) => {
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  })
})

// 展开的消息索引集合
const expandedMessages = ref(new Set())

// 切换消息展开状态
const toggleMessage = (index) => {
  if (expandedMessages.value.has(index)) {
    expandedMessages.value.delete(index)
  } else {
    expandedMessages.value.add(index)
  }
}

// 默认展开第一条消息
watch(sortedMessages, (messages) => {
  if (messages.length > 0) {
    expandedMessages.value = new Set([0])
  }
}, { immediate: true })

// 监听节点变化，重置展开状态
watch(() => props.node?.id, () => {
  if (sortedMessages.value.length > 0) {
    expandedMessages.value = new Set([0])
  } else {
    expandedMessages.value = new Set()
  }
})

// 复制节点 ID
const copyNodeId = async () => {
  try {
    await navigator.clipboard.writeText(props.node.id)
    // 可以添加提示，这里简化处理
  } catch (err) {
    console.error('复制失败:', err)
  }
}

// 获取消息图标
const getMessageIcon = (msg) => {
  if (msg.type === 'user') return '👤'
  if (msg.type === 'ai') return '🤖'
  if (msg.type === 'tool_call') return '🔧'
  if (msg.error) return '❌'
  return 'ℹ️'
}

// 获取消息类型标签
const getMessageTypeLabel = (type) => {
  const labels = {
    user: '用户',
    ai: 'AI 回复',
    system: '系统',
    tool_call: '工具调用'
  }
  return labels[type] || type
}

// Markdown 渲染
const renderMarkdown = (content) => {
  if (!content) return ''
  try {
    // 检查是否是图片格式 <img_path>filename</img_path>
    const imgMatch = content.match(/^<img_path>([^<]+)<\/img_path>$/)
    if (imgMatch) {
      const imgPath = imgMatch[1]
      return `<div class="image-container">
        <img src="/${imgPath}" alt="图片" class="max-w-full h-auto rounded-lg shadow-md border border-gray-200" />
      </div>`
    }

    // 检查是否包含 <img> 标签
    if (content.includes('<img')) {
      // 先渲染 markdown
      let html = marked.parse(content)

      // 处理 <img> 标签
      html = html.replace(/<img([^>]+)>/g, (match, attrs) => {
        // 解析属性
        const srcMatch = attrs.match(/src=["']([^"']+)["']/)
        const altMatch = attrs.match(/alt=["']([^"']*)["']/)
        const titleMatch = attrs.match(/title=["']([^"']*)["']/)
        const widthMatch = attrs.match(/width=["']([^"']*)["']/)
        const heightMatch = attrs.match(/height=["']([^"']*)["']/)

        const src = srcMatch ? srcMatch[1] : ''
        const alt = altMatch ? altMatch[1] : '图片'
        const title = titleMatch ? titleMatch[1] : ''
        const width = widthMatch ? widthMatch[1] : ''
        const height = heightMatch ? heightMatch[1] : ''

        // 如果是相对路径，添加 /
        let finalSrc = src
        if (src && !src.startsWith('http') && !src.startsWith('/')) {
          finalSrc = '/' + src
        }

        // 构建样式
        let style = ''
        if (width) style += `width: ${width}; `
        if (height) style += `height: ${height}; `

        return `<div class="image-container">
          <img src="${finalSrc}" alt="${alt}" title="${title}" ${style ? `style="${style}"` : ''} class="max-w-full h-auto rounded-lg shadow-md border border-gray-200" />
        </div>`
      })

      return html
    }

    // 先渲染 markdown
    let html = marked.parse(content)

    // 处理行内数学公式 $...$
    html = html.replace(/\$([^$]+)\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula, {
          displayMode: false, // 行内公式
          throwOnError: false,
          errorColor: '#cc0000',
        })
      } catch (error) {
        console.error('KaTeX inline render error:', error)
        return match // 如果渲染失败，返回原始文本
      }
    })

    // 处理块级数学公式 $$...$$
    html = html.replace(/\$\$([^$]+)\$\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula, {
          displayMode: true, // 块级公式
          throwOnError: false,
          errorColor: '#cc0000',
        })
      } catch (error) {
        console.error('KaTeX block render error:', error)
        return match // 如果渲染失败，返回原始文本
      }
    })

    return html
  } catch (error) {
    console.error('Markdown parse error:', error)
    return content
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  // 如果是今天
  if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  // 如果是昨天
  if (diff < 48 * 60 * 60 * 1000 && date.getDate() === now.getDate() - 1) {
    return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  // 其他日期
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 节点样式相关函数
const getNodeTypeClass = (type) => {
  const classes = {
    start: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    end: 'bg-rose-50 text-rose-700 border border-rose-200',
    chatbot: 'bg-violet-50 text-violet-700 border border-violet-200',
    tool: 'bg-amber-50 text-amber-700 border border-amber-200',
    tools: 'bg-amber-50 text-amber-700 border border-amber-200',
    summary: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    agent: 'bg-pink-50 text-pink-700 border border-pink-200',
    supervisor: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
    worker: 'bg-teal-50 text-teal-700 border border-teal-200',
  }
  return classes[type] || 'bg-slate-50 text-slate-700 border border-slate-200'
}

const getNodeIconBgClass = (type) => {
  const classes = {
    start: 'bg-gradient-to-br from-emerald-400 to-emerald-600',
    end: 'bg-gradient-to-br from-rose-400 to-rose-600',
    chatbot: 'bg-gradient-to-br from-violet-400 to-violet-600',
    tool: 'bg-gradient-to-br from-amber-400 to-amber-600',
    tools: 'bg-gradient-to-br from-amber-400 to-amber-600',
    summary: 'bg-gradient-to-br from-cyan-400 to-cyan-600',
    agent: 'bg-gradient-to-br from-pink-400 to-pink-600',
    supervisor: 'bg-gradient-to-br from-indigo-400 to-indigo-600',
    worker: 'bg-gradient-to-br from-teal-400 to-teal-600',
  }
  return classes[type] || 'bg-gradient-to-br from-slate-400 to-slate-600'
}

const getNodeBgPattern = (type) => {
  const patterns = {
    start: 'bg-gradient-to-br from-emerald-100 to-transparent',
    end: 'bg-gradient-to-br from-rose-100 to-transparent',
    chatbot: 'bg-gradient-to-br from-violet-100 to-transparent',
    tool: 'bg-gradient-to-br from-amber-100 to-transparent',
    tools: 'bg-gradient-to-br from-amber-100 to-transparent',
    summary: 'bg-gradient-to-br from-cyan-100 to-transparent',
    agent: 'bg-gradient-to-br from-pink-100 to-transparent',
    supervisor: 'bg-gradient-to-br from-indigo-100 to-transparent',
    worker: 'bg-gradient-to-br from-teal-100 to-transparent',
  }
  return patterns[type] || 'bg-gradient-to-br from-slate-100 to-transparent'
}

const getNodeIcon = (type) => {
  const icons = {
    start: '🚀',
    end: '🏁',
    chatbot: '🤖',
    tool: '🔧',
    tools: '🛠️',
    summary: '📝',
    agent: '🎯',
    supervisor: '👔',
    worker: '👷',
  }
  return icons[type] || '📦'
}

const getNodeTypeLabel = (type) => {
  const labels = {
    start: '流程起点',
    end: '流程终点',
    chatbot: 'AI 对话节点',
    tool: '工具节点',
    tools: '工具集节点',
    summary: '总结节点',
    agent: '智能代理',
    supervisor: '监督节点',
    worker: '工作节点',
  }
  return labels[type] || '通用节点'
}
</script>

<style scoped>
/* 自定义滚动条 - 用于消息列表 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 2px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

/* 图片样式 */
.image-container {
  margin: 0.75rem 0;
  text-align: center;
}

.image-container img {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.1);
  border: 1px solid #E2E8F0;
}

/* Markdown 样式 - 紧凑版本适合侧边栏 */
.markdown-content {
  word-wrap: break-word;
  color: #475569;
  font-feature-settings: "kern" 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.markdown-content :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.6;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(p:first-child) {
  margin-top: 0;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-weight: 700;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  color: #1e293b;
  line-height: 1.3;
}

.markdown-content :deep(h1:first-child),
.markdown-content :deep(h2:first-child),
.markdown-content :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-content :deep(h1) {
  font-size: 1rem;
  color: #7c3aed;
}

.markdown-content :deep(h2) {
  font-size: 0.9375rem;
  color: #8b5cf6;
}

.markdown-content :deep(h3) {
  font-size: 0.875rem;
  color: #334155;
}

.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-size: 0.8125rem;
  color: #475569;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 0.75rem;
  padding-left: 1.25rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.375rem;
  line-height: 1.6;
}

.markdown-content :deep(li:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(code) {
  background: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.8125em;
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  color: #7c3aed;
  border: 1px solid #e2e8f0;
  font-weight: 600;
}

.markdown-content :deep(pre) {
  background: #1e293b;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.75rem 0;
  border: 1px solid #334155;
  box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.1);
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #f8fafc;
  font-size: 0.8125rem;
  line-height: 1.5;
  border: none;
  font-weight: 400;
}

.markdown-content :deep(blockquote) {
  border-left: 2px solid #a78bfa;
  padding-left: 0.75rem;
  padding-top: 0.375rem;
  padding-bottom: 0.375rem;
  margin: 0.75rem 0;
  color: #64748b;
  background: #f8fafc;
  border-radius: 0 0.5rem 0.5rem 0;
}

.markdown-content :deep(a) {
  color: #7c3aed;
  text-decoration: none;
  border-bottom: 1px solid #ddd6fe;
  font-weight: 600;
  transition: all 0.2s;
}

.markdown-content :deep(a:hover) {
  color: #6d28d9;
  border-bottom-color: #a78bfa;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0.75rem 0;
  font-size: 0.8125rem;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 3px -1px rgb(0 0 0 / 0.05);
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f1f5f9;
  font-weight: 700;
  color: #475569;
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.markdown-content :deep(td) {
  color: #64748b;
  background-color: white;
}

.markdown-content :deep(tr:hover td) {
  background: #fafafa;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  margin: 0.75rem 0;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.1);
}

.markdown-content :deep(hr) {
  border: none;
  height: 1px;
  background: #e2e8f0;
  margin: 1rem 0;
  border-radius: 1px;
}

/* 代码高亮样式 */
.markdown-content :deep(.hljs) {
  background: #1e293b;
  color: #f8fafc;
}

.markdown-content :deep(.hljs-keyword),
.markdown-content :deep(.hljs-selector-tag),
.markdown-content :deep(.hljs-literal),
.markdown-content :deep(.hljs-section),
.markdown-content :deep(.hljs-link) {
  color: #c084fc;
}

.markdown-content :deep(.hljs-string),
.markdown-content :deep(.hljs-title),
.markdown-content :deep(.hljs-name),
.markdown-content :deep(.hljs-type),
.markdown-content :deep(.hljs-attribute),
.markdown-content :deep(.hljs-symbol),
.markdown-content :deep(.hljs-bullet),
.markdown-content :deep(.hljs-addition),
.markdown-content :deep(.hljs-variable),
.markdown-content :deep(.hljs-template-tag),
.markdown-content :deep(.hljs-template-variable) {
  color: #a3e635;
}

.markdown-content :deep(.hljs-comment),
.markdown-content :deep(.hljs-quote),
.markdown-content :deep(.hljs-deletion),
.markdown-content :deep(.hljs-meta) {
  color: #94a3b8;
}

.markdown-content :deep(.hljs-number),
.markdown-content :deep(.hljs-regexp),
.markdown-content :deep(.hljs-selector-id),
.markdown-content :deep(.hljs-selector-class),
.markdown-content :deep(.hljs-tag) {
  color: #fbbf24;
}

.markdown-content :deep(.hljs-function) {
  color: #60a5fa;
}

.markdown-content :deep(.hljs-built_in),
.markdown-content :deep(.hljs-builtin-name) {
  color: #fb923c;
}
</style>
