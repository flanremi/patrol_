<template>
  <div class="modern-chat flex flex-col h-full bg-white relative overflow-hidden">
    <!-- 背景装饰 - 柔和的几何形状 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute top-20 right-10 w-64 h-64 bg-blue-200/20 rounded-full blur-3xl"></div>
      <div class="absolute bottom-32 left-10 w-80 h-80 bg-blue-300/20 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 right-1/4 w-48 h-48 bg-blue-100/30 rounded-full blur-2xl"></div>
    </div>

    <!-- 聊天消息区域 -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto relative z-10"
      :class="messages.length === 0 ? 'flex items-center justify-center' : ''"
    >
      <!-- 欢迎界面 - 空状态 -->
      <div v-if="messages.length === 0"
           class="max-w-[52rem] mx-auto px-8 text-center">
        <div class="mb-16 relative">
          <!-- 装饰小圆点 -->
          <div class="absolute -top-4 left-1/2 -translate-x-12 w-2 h-2 bg-blue-500 rounded-full opacity-60"></div>
          <div class="absolute -top-2 left-1/2 translate-x-16 w-1.5 h-1.5 bg-blue-400 rounded-full opacity-40"></div>

          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl  mb-6  relative">
            <Logo class="w-20 h-20 "></Logo>
          </div>

          <h1 class="text-[32px] font-bold text-gray-900 mb-3 tracking-tight">
            故障检测智能体
          </h1>
          <p class="text-[16px] text-gray-600 leading-relaxed max-w-md mx-auto">
            故障检查系统
          </p>
        </div>

        <!-- 快捷建议卡片 - 加载预设对话 -->
        <div class="grid grid-cols-1 gap-3 max-w-[44rem] mx-auto">
          <button
            v-for="(suggestion, index) in suggestions"
            :key="suggestion.file"
            @click="loadChatFile(suggestion.file)"
            :disabled="isReplaying"
            class="group relative px-5 py-4 text-left rounded-2xl bg-white border-2 border-blue-200 shadow-sm hover:shadow-md hover:border-blue-500 transition-all duration-200 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <!-- 装饰小形状 -->
            <div class="absolute top-2 right-2 w-1 h-1 bg-blue-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>

            <div class="flex items-center gap-4">
              <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl group-hover:bg-blue-200 transition-all duration-200 relative">
                {{suggestion.icon}}
                <!-- 小装饰点 -->
                <div class="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-blue-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[16px] font-bold text-gray-900 group-hover:text-blue-600 transition-colors leading-tight">
                  {{suggestion.title}}
                </div>
                <div class="text-[14px] text-gray-600 mt-1 leading-snug">
                  {{suggestion.description}}
                </div>
              </div>
              <ArrowRightIcon class="flex-shrink-0 w-5 h-5 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all duration-200"/>
            </div>
          </button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-else
           class="max-w-[50rem] mx-auto px-6 py-8">
        <div
          v-for="message in messages"
          :key="message.id"
          class="mb-6"
        >
          <!-- 用户消息 -->
          <div v-if="message.type === 'user'"
               class="flex justify-end animate-fade-in">
            <div class="max-w-[70%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-md shadow-blue-500/20 relative break-words">
              <!-- 小装饰点 -->
              <div class="absolute -top-1 -left-1 w-2 h-2 bg-blue-600 rounded-full"></div>
              <div class="text-[15px] leading-[1.6] whitespace-pre-wrap break-words">{{message.content}}</div>
            </div>
          </div>

          <!-- AI 消息 -->
          <div v-else-if="message.type === 'ai' && message.content"
               class="flex justify-start animate-fade-in">
            <div class="w-full max-w-[98%]">
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0 w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center mt-0.5 border-2 border-blue-200 relative">
                  <SparklesIcon class="w-4 h-4 text-blue-600"/>
                  <!-- 小装饰 -->
                  <div class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                </div>
                <div class="flex-1 min-w-0 bg-white rounded-2xl rounded-tl-sm px-5 py-4 border-2 border-blue-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all overflow-hidden relative">
                  <!-- 装饰形状 -->
                  <div class="absolute top-2 right-2 w-1 h-1 bg-blue-100 rounded-full"></div>
                  <div
                    class="markdown-content text-[15px] text-gray-700 leading-[1.7] overflow-x-auto"
                    v-html="renderMarkdown(message.content)"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 系统消息 -->
          <div v-else-if="message.type === 'system'"
               class="flex justify-center animate-fade-in my-3">
            <div
              class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-semibold shadow-sm border-2 relative"
              :class="message.error
                ? 'bg-red-50 text-red-600 border-red-200'
                : 'bg-blue-50 text-blue-600 border-blue-200'"
            >
              <CheckCircleIcon v-if="!message.error"
                               class="w-3.5 h-3.5"/>
              <ExclamationCircleIcon v-else
                                     class="w-3.5 h-3.5"/>
              <span>{{message.content}}</span>
            </div>
          </div>

          <!-- 工具调用消息 -->
          <div v-else-if="message.type === 'tool_call'"
               class="flex justify-start animate-fade-in">
            <div class="max-w-[85%]">
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0 w-9 h-9 rounded-xl bg-yellow-100 flex items-center justify-center mt-0.5 border-2 border-yellow-200 relative">
                  <WrenchScrewdriverIcon class="w-4 h-4 text-amber-800"/>
                  <div class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-yellow-500 rounded-full"></div>
                </div>
                <div class="flex-1 bg-yellow-50 border-2 border-yellow-200 rounded-2xl rounded-tl-sm px-5 py-3.5 shadow-sm relative">
                  <div class="absolute top-2 right-2 w-1 h-1 bg-yellow-100 rounded-full"></div>
                  <div class="flex items-center gap-2 text-[12px] font-bold text-amber-800 mb-2 uppercase tracking-wide">
                    <CogIcon class="w-3.5 h-3.5"/>
                    <span>工具调用</span>
                  </div>
                  <div class="text-[14px] text-gray-700 leading-[1.6]">{{message.content}}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 回放指示器 -->
        <div v-if="isReplaying"
             class="mb-6 animate-fade-in">
          <div class="flex justify-center">
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-semibold shadow-md border-2 bg-yellow-100 text-amber-800 border-yellow-200">
              <ArrowPathIcon class="w-3.5 h-3.5 animate-spin"/>
              <span>正在回放对话...</span>
            </div>
          </div>
        </div>

        <!-- 加载指示器 -->
        <div v-else-if="loading || streamingStatus"
             class="mb-6 animate-fade-in">
          <div class="flex items-start gap-3">
            <div class="flex-shrink-0 w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center mt-0.5 border-2 border-blue-200 relative">
              <SparklesIcon class="w-4 h-4 text-blue-600 animate-pulse"/>
              <div class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
            </div>
            <div class="flex-1 bg-white rounded-2xl rounded-tl-sm px-5 py-4 border-2 border-blue-200 shadow-sm relative">
              <div class="absolute top-2 right-2 w-1 h-1 bg-blue-100 rounded-full"></div>
              <div class="flex items-center gap-3">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                       style="animation-delay: 0s;"></div>
                  <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                       style="animation-delay: 0.15s;"></div>
                  <div class="w-2 h-2 bg-blue-300 rounded-full animate-bounce"
                       style="animation-delay: 0.3s;"></div>
                </div>
                <span class="text-[14px] text-gray-700 font-semibold">{{streamingStatus || '正在思考...'}}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 - 固定在底部 -->
    <div class="flex-shrink-0  border-blue-200 bg-white shadow-lg relative z-10">
      <div class="max-w-[50rem] mx-auto px-6 py-5">
        <!-- 输入框容器 -->
        <div class="relative"
             style="height: 56px;">
          <input
            ref="inputRef"
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendMessage"
            :disabled="loading || isReplaying"
            :placeholder="isReplaying ? '正在回放对话，请稍候...' : '输入你的问题，开启故障分析检测...'"
            class="w-full resize-none rounded-2xl bg-white border-2 border-blue-200 px-5 py-3.5 pr-28 text-[15px] text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-400 transition-all leading-[1.5] shadow-sm"
            style="max-height: 200px; height: 57px"
          />

          <!-- 工具栏 -->
          <div class="absolute right-2 bottom-[6px] flex items-center gap-2">
            <!-- 清空按钮 -->
            <button
              v-if="inputMessage.trim()"
              @click="clearInput"
              class="p-2 rounded-xl text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all"
              title="清空输入"
            >
              <XMarkIcon class="w-4 h-4"/>
            </button>

            <!-- 发送按钮 -->
            <button
              @click="sendMessage"
              :disabled="loading || !inputMessage.trim() || isReplaying"
              class="px-4 py-2.5 rounded-xl font-semibold text-[13px] transition-all flex items-center gap-2 shadow-sm transform relative"
              :class="loading || !inputMessage.trim() || isReplaying
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600 active:scale-95 hover:shadow-md shadow-blue-500/20'"
            >
              <PaperAirplaneIcon v-if="!loading"
                                 class="w-4 h-4"/>
              <ArrowPathIcon v-else
                             class="w-4 h-4 animate-spin"/>
              <span>{{loading ? '发送中' : '发送'}}</span>
            </button>
          </div>
        </div>

        <!-- 底部提示 -->
        <div class="flex items-center justify-between mt-3.5 px-1">
          <div class="flex items-center gap-3 text-[12px] text-gray-600">
            <span v-if="messages.length > 0"
                  class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-600 border border-blue-200">
              <ChatBubbleLeftRightIcon class="w-3.5 h-3.5"/>
              <span>已有 {{messages.length}} 条对话</span>
            </span>
            <span v-else
                  class="flex items-center gap-1.5">
              <SparklesIcon class="w-3.5 h-3.5"/>
              <span>按 Enter 发送消息</span>
            </span>
          </div>
          <div v-if="messages.length > 0"
               class="flex items-center gap-2">
            <button
              @click="saveChat"
              :disabled="isReplaying"
              class="flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-lg text-gray-600 hover:text-blue-600 hover:bg-blue-50 transition-all border border-transparent hover:border-blue-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowDownTrayIcon class="w-3.5 h-3.5"/>
              <span>保存对话</span>
            </button>
            <button
              @click="clearChat"
              :disabled="isReplaying"
              class="flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-lg text-gray-600 hover:text-red-600 hover:bg-red-50 transition-all border border-transparent hover:border-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <TrashIcon class="w-3.5 h-3.5"/>
              <span>清空对话</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ArrowRightIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  CogIcon,
  ExclamationCircleIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  TrashIcon,
  WrenchScrewdriverIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { ChatStoreKey, convertPathToNodeId } from '~/composables/useChatStore'

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

// Props
const props = defineProps({
  apiBaseUrl: {
    type: String,
    default: 'http://localhost:8001',
  },
})

// 注入聊天存储
const chatStore = inject(ChatStoreKey)

// 使用 chatStore 的数据，如果没有则使用本地状态（兼容性）
const messages = chatStore ? chatStore.messages : ref([])
const loading = chatStore ? chatStore.loading : ref(false)
const streamingStatus = chatStore ? chatStore.streamingStatus : ref('')

// 本地状态
const inputMessage = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

// 快捷建议 - 加载预设对话文件
const suggestions = ref([
  {
    icon: '🔬',
    title: '铁为什么会生锈？',
    description: '探索金属氧化的化学原理和生活中的防锈方法',
    file: '铁为什么会生锈.json',
  },
])

// 回放状态
const isReplaying = ref(false)
const replaySpeed = ref(1) // 回放速度倍率

// 节点执行上下文，用于跟踪工具调用
const nodeExecutionContext = ref(new Map()) // nodeId -> { hasToolCalls: boolean, startTime: number }

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

// 清空输入
const clearInput = () => {
  inputMessage.value = ''
}

// 保存对话为 JSON 文件
const saveChat = () => {
  if (messages.value.length === 0) {
    alert('没有可保存的对话')
    return
  }

  // 计算相对时间
  const firstTimestamp = new Date(messages.value[0].timestamp).getTime()
  const messagesWithRelativeTime = messages.value.map((msg) => {
    const currentTimestamp = new Date(msg.timestamp).getTime()
    const relativeTime = currentTimestamp - firstTimestamp
    return {
      ...msg,
      relativeTime, // 相对于第一条消息的时间差（毫秒）
    }
  })

  const chatData = {
    title: messages.value.find((m) => m.type === 'user')?.content || '未命名对话',
    savedAt: new Date().toISOString(),
    messageCount: messages.value.length,
    messages: messagesWithRelativeTime,
  }

  // 创建下载链接
  const blob = new Blob([JSON.stringify(chatData, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${chatData.title.substring(0, 20)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 加载对话文件
const loadChatFile = async (file) => {
  try {
    const response = await fetch(`/${file}`)
    if (!response.ok) {
      throw new Error(`文件加载失败: ${response.status} ${response.statusText}`)
    }
    const chatData = await response.json()
    await replayChat(chatData)
  } catch (error) {
    console.error('[加载] 加载对话失败:', error)
    alert(`加载对话失败: ${error.message}`)
  }
}

// 回放对话
const replayChat = async (chatData) => {
  console.log(chatData)
  if (isReplaying.value) {
    return
  }

  // 清空现有消息
  if (chatStore) {
    chatStore.clearMessages()
    // 重置所有节点状态为默认
    chatStore.emitNodeStatusChange(null, 'default')
    // 触发聊天开始事件（显示工作流画布）
    chatStore.emitChatStart()
  } else {
    messages.value = []
  }

  // 清空节点执行上下文
  nodeExecutionContext.value.clear()

  isReplaying.value = true

  // 延迟 2 秒，让工作流画布出现动画完成
  await new Promise((resolve) => setTimeout(resolve, 2000))

  const messagesData = chatData.messages || []

  for (let i = 0; i < messagesData.length; i++) {
    const msg = messagesData[i]

    // 如果有相对时间，则按时间间隔回放
    if (i > 0 && msg.relativeTime !== undefined) {
      const prevMsg = messagesData[i - 1]
      const delay = (msg.relativeTime - prevMsg.relativeTime) / replaySpeed.value
      // 限制最大延迟为 3 秒
      await new Promise((resolve) => setTimeout(resolve, Math.min(delay, 1000)))
    }

    // 添加消息
    const message = {
      ...msg,
    }

    if (chatStore) {
      chatStore.addMessage(message)
    } else {
      messages.value.push(message)
    }

    // 如果是节点相关消息，触发节点高亮
    if (msg.node_path) {
      const nodeId = convertPathToNodeId(msg.node_path, msg)

      if (nodeId && chatStore) {
        // 检查是否是开始执行的消息
        if (msg.streamType === 'node_start') {
          chatStore.emitNodeHighlight(nodeId, 3000)
          chatStore.emitNodeStatusChange(nodeId, 'executing')
        }
        // 检查是否是完成执行的消息
        else if (msg.streamType === 'node_complete') {
          chatStore.emitNodeUnhighlight(nodeId)
          chatStore.emitNodeStatusChange(nodeId, 'completed')
        } else {
          chatStore.emitNodeHighlight(nodeId)

          // 3秒后自动取消工具节点的高亮，但保持执行状态
          setTimeout(() => {
            if (chatStore) {
              chatStore.emitNodeUnhighlight(nodeId)
            }
          }, 500)
        }
      }
    }

    scrollToBottom()
  }

  console.log('[回放] 回放完成')
  isReplaying.value = false
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  const newMessage = {
    id: Date.now(),
    type: 'user',
    content: userMessage,
    timestamp: new Date().toISOString(),
  }

  if (chatStore) {
    chatStore.addMessage(newMessage)
    // 触发聊天开始事件（显示工作流画布）
    chatStore.emitChatStart()
  } else {
    messages.value.push(newMessage)
  }

  loading.value = true
  streamingStatus.value = '工作流准备中...'

  // 延迟 2 秒，让工作流画布出现动画完成
  await new Promise(resolve => setTimeout(resolve, 2000))

  streamingStatus.value = ''

  try {
    const response = await fetch(`${props.apiBaseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: userMessage }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleStreamData(data)
          } catch (e) {
            console.error('解析流数据失败:', e)
          }
        }
      }
    }

  } catch (error) {
    console.error('发送消息失败:', error)
    const errorMessage = {
      id: Date.now(),
      type: 'system',
      content: '❌ 发生错误，请稍后重试',
      timestamp: new Date().toISOString(),
      error: true,
    }

    if (chatStore) {
      chatStore.addMessage(errorMessage)
    } else {
      messages.value.push(errorMessage)
    }
  } finally {
    loading.value = false
    streamingStatus.value = ''
  }
}


// 处理流式数据
const handleStreamData = (data) => {
  switch (data.type) {
    case 'start':
      streamingStatus.value = data.message
      break

    case 'status':
      streamingStatus.value = data.message
      break

    case 'node_start':
      streamingStatus.value = data.message

      // 从 node_path 转换节点 ID，暂时不考虑工具调用（会在收到消息时更新）
      const nodeIdForStart = data.node_path ? convertPathToNodeId(data.node_path) : data.node

      // 初始化节点执行上下文
      if (nodeIdForStart) {
        nodeExecutionContext.value.set(nodeIdForStart, {
          hasToolCalls: false,
          startTime: Date.now(),
          originalPath: data.node_path,
          node: data.node,
        })
      }

      const startMessage = {
        id: Date.now() + Math.random(),
        type: 'system',
        content: `${data.message}`,
        timestamp: new Date().toISOString(),
        node: data.node,
        path: data.node_path,
        streamType: data.type,
      }

      if (chatStore) {
        chatStore.addMessage(startMessage)
      } else {
        messages.value.push(startMessage)
      }

      if (nodeIdForStart) {
        if (chatStore) {
          chatStore.emitNodeHighlight(nodeIdForStart, 3000)
          chatStore.emitNodeStatusChange(nodeIdForStart, 'executing')
        }
      }
      break

    case 'node_complete':
      streamingStatus.value = data.message

      // 从 node_path 转换节点 ID，考虑工具调用上下文
      let nodeIdForComplete = data.node_path ? convertPathToNodeId(data.node_path) : data.node

      // 检查是否有工具调用上下文，如果有则重新计算节点ID
      const contextKey = nodeIdForComplete
      const context = nodeExecutionContext.value.get(contextKey)
      if (context && context.hasToolCalls && data.node_path) {
        nodeIdForComplete = convertPathToNodeId(data.node_path, { tool_calls: [{}] })
      }

      const completeMessage = {
        id: Date.now() + Math.random(),
        type: 'system',
        content: `${data.message}`,
        timestamp: new Date().toISOString(),
        node: data.node,
        path: data.node_path,
        streamType: data.type,
      }

      if (chatStore) {
        chatStore.addMessage(completeMessage)
      } else {
        messages.value.push(completeMessage)
      }

      if (nodeIdForComplete) {
        if (chatStore) {
          // 停止高亮
          chatStore.emitNodeUnhighlight(nodeIdForComplete)
          // 更新状态为完成
          chatStore.emitNodeStatusChange(nodeIdForComplete, 'completed')
        }
      }

      // 清理节点执行上下文
      if (contextKey) {
        nodeExecutionContext.value.delete(contextKey)
      }
      break

    case 'message':
      // 跳过用户消息（前端已经添加过了）
      if (data.data.type !== 'user') {
        const aiMessage = {
          id: data.data.id || Date.now() + Math.random(),
          ...data.data,
          timestamp: data.data.timestamp || new Date().toISOString(),
        }

        // 检查是否有工具调用，如果有则更新节点执行上下文
        if (data.data.tool_calls && data.data.tool_calls.length > 0) {
          // 查找最近的正在执行的节点
          let recentNodeId = null
          let recentStartTime = 0

          for (const [nodeId, context] of nodeExecutionContext.value.entries()) {
            if (!context.hasToolCalls && context.startTime > recentStartTime) {
              recentNodeId = nodeId
              recentStartTime = context.startTime
            }
          }

          if (recentNodeId) {
            // 更新上下文
            const context = nodeExecutionContext.value.get(recentNodeId)
            context.hasToolCalls = true

            // 如果节点正在高亮，需要重新高亮正确的节点
            if (chatStore) {
              // 取消当前高亮
              chatStore.emitNodeUnhighlight(recentNodeId)

              // 计算新的节点ID（工具节点）
              const newNodeId = context.originalPath ? convertPathToNodeId(context.originalPath, aiMessage) : null

              if (newNodeId && newNodeId !== recentNodeId) {
                chatStore.emitNodeHighlight(newNodeId, 3000)
                chatStore.emitNodeStatusChange(newNodeId, 'executing')

                // 3秒后自动取消工具节点的高亮，但保持执行状态
                setTimeout(() => {
                  if (chatStore) {
                    chatStore.emitNodeUnhighlight(newNodeId)
                  }
                }, 3000)

                // 更新上下文中的节点ID
                nodeExecutionContext.value.delete(recentNodeId)
                nodeExecutionContext.value.set(newNodeId, context)
              }
            }
          }
        }

        if (chatStore) {
          chatStore.addMessage(aiMessage)
        } else {
          messages.value.push(aiMessage)
        }
      }
      break

    case 'complete':
      streamingStatus.value = '处理完成'
      if (data.metadata && data.metadata.nodes_executed) {
        const completionMessage = {
          id: Date.now() + Math.random(),
          type: 'system',
          content: `处理完成！`,
          timestamp: new Date().toISOString(),
          metadata: data.metadata,
          streamType: data.type,
        }

        if (chatStore) {
          chatStore.addMessage(completionMessage)
        } else {
          messages.value.push(completionMessage)
        }
      }
      setTimeout(() => {
        streamingStatus.value = ''
      }, 1000)
      break

    case 'error':
      console.error('Stream error:', data.error)
      const streamErrorMessage = {
        id: Date.now(),
        type: 'system',
        content: `❌ 错误: ${data.error}`,
        timestamp: new Date().toISOString(),
        error: true,
        node: data.node,
        streamType: data.type,
      }

      if (chatStore) {
        chatStore.addMessage(streamErrorMessage)
      } else {
        messages.value.push(streamErrorMessage)
      }

      if (data.node) {
        if (chatStore) {
          chatStore.emitNodeStatusChange(data.node, 'error')
        }
      }
      break
  }
}

// 清空对话
const clearChat = () => {
  if (chatStore) {
    chatStore.clearMessages()
    chatStore.emitNodeStatusChange(null, 'default')
  } else {
    messages.value = []
  }

  // 清空节点执行上下文
  nodeExecutionContext.value.clear()
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息变化
watch(() => messages.value, () => {
  scrollToBottom()
}, { deep: true })

// 监听加载状态
watch(() => loading.value, () => {
  scrollToBottom()
})
</script>

<style scoped>
.modern-chat {
  height: 100%;
}

/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #D0D5DD;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #98A2B3;
}

/* 平滑滚动 */
.overflow-y-auto {
  scroll-behavior: smooth;
}

/* 动画 */
@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

.animate-bounce {
  animation: bounce 1s infinite;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}

/* 图片样式 */
.image-container {
  margin: 1rem 0;
  text-align: center;
}

.image-container img {
  max-width: 100%;
  height: auto;
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  border: 2px solid #E9D5FF;
}

/* Markdown 样式 - 积木风格 */
.markdown-content {
  word-wrap: break-word;
  font-feature-settings: "kern" 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.markdown-content :deep(p) {
  margin-bottom: 1rem;
  line-height: 1.7;
  font-weight: 500;
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
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  color: #1A202C;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.markdown-content :deep(h1:first-child),
.markdown-content :deep(h2:first-child),
.markdown-content :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-content :deep(h1) {
  font-size: 1.5rem;
  color: #7C3AED;
}

.markdown-content :deep(h2) {
  font-size: 1.25rem;
  color: #A78BFA;
}

.markdown-content :deep(h3) {
  font-size: 1.125rem;
  color: #1F2937;
}

.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-size: 1rem;
  color: #374151;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.75rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.5rem;
  line-height: 1.7;
  font-weight: 500;
}

.markdown-content :deep(li:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(code) {
  background: #F3E8FF;
  padding: 0.2rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.875em;
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  color: #7C3AED;
  border: 1px solid #E9D5FF;
  font-weight: 600;
}

.markdown-content :deep(pre) {
  background: #1F2937;
  padding: 1.25rem 1.5rem;
  border-radius: 1rem;
  overflow-x: auto;
  margin: 1rem 0;
  border: 2px solid #374151;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #F9FAFB;
  font-size: 0.875rem;
  line-height: 1.6;
  border: none;
  font-weight: 400;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid #A78BFA;
  padding-left: 1.25rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  margin: 1rem 0;
  color: #4B5563;
  background: #F9FAFB;
  border-radius: 0 0.75rem 0.75rem 0;
  font-weight: 500;
}

.markdown-content :deep(a) {
  color: #7C3AED;
  text-decoration: none;
  border-bottom: 2px solid #DDD6FE;
  font-weight: 600;
  transition: all 0.2s;
}

.markdown-content :deep(a:hover) {
  color: #6D28D9;
  border-bottom-color: #A78BFA;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1rem 0;
  font-size: 0.9375rem;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.05);
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 2px solid #E2E8F0;
  padding: 0.75rem 1rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #F3E8FF;
  font-weight: 700;
  color: #6D28D9;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.markdown-content :deep(td) {
  color: #4B5563;
  font-weight: 500;
  background-color: white;
}

.markdown-content :deep(tr:hover td) {
  background: #FAFAFA;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 1rem;
  margin: 1rem 0;
  border: 2px solid #E9D5FF;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.markdown-content :deep(hr) {
  border: none;
  height: 2px;
  background: #E9D5FF;
  margin: 2rem 0;
  border-radius: 2px;
}

/* 代码高亮样式 */
.markdown-content :deep(.hljs) {
  background: #1D2939;
  color: #F9FAFB;
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
