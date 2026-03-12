<template>
  <div class="modern-chat flex flex-col h-full bg-white relative overflow-hidden">
    <!-- 背景装饰 - 柔和的几何形状 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute top-20 right-10 w-64 h-64 bg-blue-200/20 rounded-full blur-3xl"></div>
      <div class="absolute bottom-32 left-10 w-80 h-80 bg-blue-300/20 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 right-1/4 w-48 h-48 bg-blue-100/30 rounded-full blur-2xl"></div>
    </div>

    <!-- 连接状态指示器 -->
    <div v-if="!wsConnected" class="absolute top-4 right-4 z-20">
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold"
           :class="wsConnecting ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'">
        <div class="w-2 h-2 rounded-full animate-pulse"
             :class="wsConnecting ? 'bg-yellow-500' : 'bg-red-500'"></div>
        {{ wsConnecting ? '连接中...' : '未连接' }}
      </div>
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
            智能故障检查与分析系统
          </p>
        </div>

        <!-- 快捷建议卡片 -->
        <div class="grid grid-cols-1 gap-3 max-w-[44rem] mx-auto">
          <button
            v-for="(suggestion, index) in suggestions"
            :key="index"
            @click="sendQuickMessage(suggestion.message)"
            :disabled="loading || !wsConnected"
            class="group relative px-5 py-4 text-left rounded-2xl bg-white border-2 border-blue-200 shadow-sm hover:shadow-md hover:border-blue-500 transition-all duration-200 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div class="absolute top-2 right-2 w-1 h-1 bg-blue-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>

            <div class="flex items-center gap-4">
              <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl group-hover:bg-blue-200 transition-all duration-200 relative">
                {{suggestion.icon}}
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
          v-for="(message, index) in messages"
          :key="message.id"
          class="mb-6"
        >
          <!-- 用户消息 -->
          <div v-if="message.type === 'user'"
               class="flex justify-end animate-fade-in">
            <div class="max-w-[70%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-md shadow-blue-500/20 relative break-words">
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
                  <div class="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                </div>
                <div class="flex-1 min-w-0 bg-white rounded-2xl rounded-tl-sm px-5 py-4 border-2 border-blue-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all overflow-hidden relative">
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

        </div>

        <!-- 加载指示器 -->
        <div v-if="loading || streamingStatus"
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
    <div class="flex-shrink-0 border-blue-200 bg-white shadow-lg relative z-10">
      <div class="max-w-[50rem] mx-auto px-6 py-5">
        <!-- 输入框容器 -->
        <div class="relative"
             style="height: 56px;">
          <input
            ref="inputRef"
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendMessage"
            :disabled="loading || !wsConnected"
            :placeholder="!wsConnected ? '正在连接服务器...' : '输入你的问题，开启故障分析检测...'"
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
              :disabled="loading || !inputMessage.trim() || !wsConnected"
              class="px-4 py-2.5 rounded-xl font-semibold text-[13px] transition-all flex items-center gap-2 shadow-sm transform relative"
              :class="loading || !inputMessage.trim() || !wsConnected
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
              @click="clearChat"
              class="flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-lg text-gray-600 hover:text-red-600 hover:bg-red-50 transition-all border border-transparent hover:border-red-200"
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
import { inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  ArrowPathIcon,
  ArrowRightIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { ChatStoreKey } from '~/composables/useChatStore'

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
    default: 'http://0.0.0.0:8001',
  },
})

// Emits
const emit = defineEmits([
  'show-form', 
  'show-result', 
  'hide-canvas',
  'analysis-start',
  'analysis-step',
  'analysis-complete',
  'analysis-error'
])

// 注入聊天存储
const chatStore = inject(ChatStoreKey)

// 使用 chatStore 的数据，如果没有则使用本地状态
const messages = chatStore ? chatStore.messages : ref([])
const loading = chatStore ? chatStore.loading : ref(false)
const streamingStatus = chatStore ? chatStore.streamingStatus : ref('')

// 本地状态
const inputMessage = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

// WebSocket 状态
const wsConnected = ref(false)
const wsConnecting = ref(false)
let ws = null
let reconnectTimer = null
const maxReconnectAttempts = 5
let reconnectAttempts = 0

// 快捷建议
const suggestions = [
  {
    icon: '🔍',
    title: '故障排查检测',
    description: '帮您进行设备故障分析和排查',
    message: '我想进行故障排查检测',
  },
  {
    icon: '🛠️',
    title: '轴承温度异常分析',
    description: '分析轴承温度异常问题',
    message: '请帮我分析轴承温度异常的故障',
  },
  {
    icon: '📊',
    title: '设备巡检报告',
    description: '生成设备巡检分析报告',
    message: '我需要生成一份设备巡检报告',
  },
]

// ==================== WebSocket 连接管理 ====================
const connectWebSocket = () => {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return
  }

  wsConnecting.value = true

  // 构造 WebSocket URL
  const wsUrl = props.apiBaseUrl.replace(/^http/, 'ws') + '/ws'
  console.log('🔌 连接 WebSocket:', wsUrl)

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('✅ WebSocket 连接成功')
      wsConnected.value = true
      wsConnecting.value = false
      reconnectAttempts = 0
    }

    ws.onclose = (event) => {
      console.log(`❌ WebSocket 断开: code=${event.code}`)
      wsConnected.value = false
      wsConnecting.value = false

      // 自动重连
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        console.log(`🔄 尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})...`)
        reconnectTimer = setTimeout(connectWebSocket, 3000)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      wsConnecting.value = false
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWSMessage(data)
      } catch (e) {
        console.error('解析 WebSocket 消息失败:', e)
      }
    }
  } catch (error) {
    console.error('创建 WebSocket 失败:', error)
    wsConnecting.value = false
  }
}

const disconnectWebSocket = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  reconnectAttempts = maxReconnectAttempts

  if (ws) {
    ws.close()
    ws = null
  }

  wsConnected.value = false
  wsConnecting.value = false
}

const sendWSMessage = (message) => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('WebSocket 未连接')
    return false
  }

  try {
    ws.send(JSON.stringify(message))
    return true
  } catch (error) {
    console.error('发送消息失败:', error)
    return false
  }
}

// ==================== 处理 WebSocket 消息 ====================
const handleWSMessage = (data) => {
  const { type, action, data: payload } = data

  console.log(`📨 [${type}] ${action}:`, payload)

  if (type === 'system') {
    handleSystemMessage(action, payload)
  } else if (type === 'chat') {
    handleChatMessage(action, payload)
  } else if (type === 'tool') {
    handleToolMessage(action, payload)
  } else if (type === 'analysis') {
    // 分析消息 - 与 tool 类型的分析消息使用相同的处理逻辑
    handleAnalysisMessage(action, payload)
  }
}

// 处理分析消息（来自 fault_analysis_core.py）
const handleAnalysisMessage = (action, payload) => {
  console.log(`🔬 [analysis] ${action}:`, payload)
  
  if (action === 'analysis_start') {
    // 分析开始 - 通知父组件展开 Canvas 并切换到分析视图
    emit('analysis-start', {
      message: payload?.message || '开始分析...',
      input: payload?.defect_input || payload?.input || {},
      timestamp: payload?.timestamp
    })
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '🔄 故障分析任务已启动，请关注右侧面板的执行情况',
    })
  } else if (action === 'thinking_step') {
    // 思考步骤 - 转发给父组件显示在 Canvas 中
    emit('analysis-step', {
      node: payload?.node || 'process',
      title: payload?.title || '处理中',
      summary: payload?.content || payload?.summary || '',
      content: payload?.content,
      data: payload?.data,
      status: 'complete',
      step_number: payload?.step_number
    })
  } else if (action === 'node_start') {
    // 节点开始
    emit('analysis-step', {
      node: payload?.node || 'process',
      title: payload?.title || `${payload?.node || '节点'} 开始`,
      summary: payload?.message || '正在处理...',
      status: 'running'
    })
  } else if (action === 'node_complete') {
    // 节点完成 - 更新步骤状态
    emit('analysis-step', {
      node: payload?.node || 'process',
      title: payload?.title || `${payload?.node || '节点'} 完成`,
      summary: payload?.message || '处理完成',
      content: payload?.content,
      data: payload?.data,
      status: 'complete'
    })
  } else if (action === 'final_report') {
    // 最终报告 - 这是真正的完成消息，添加系统提示
    emit('analysis-complete', {
      final_report: payload?.final_report || payload?.content,
      retry_count: payload?.retry_count || 0,
      thinking_processes: payload?.thinking_processes || [],
      input: payload?.input || payload?.defect_input || {},
      timestamp: payload?.timestamp || new Date().toISOString()
    })
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '✅ 故障分析完成，请在右侧面板查看详细报告',
    })
  } else if (action === 'analysis_complete') {
    // 分析完成统计（在 final_report 之后发送，不添加消息避免重复）
    console.log('📊 分析统计:', payload)
    // 只触发事件，不添加系统消息（已在 final_report 中添加）
    emit('analysis-complete', payload)
  } else if (action === 'error') {
    // 分析错误
    emit('analysis-error', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 分析出错: ${payload?.error || '未知错误'}`,
      error: true,
    })
  }
}

const handleSystemMessage = (action, payload) => {
  if (action === 'connected') {
    console.log('连接 ID:', payload?.connection_id)
  } else if (action === 'node_start') {
    streamingStatus.value = payload?.message || '执行中...'

    // 触发节点高亮
    if (chatStore && payload?.node) {
      chatStore.emitNodeHighlight(payload.node, 3000)
      chatStore.emitNodeStatusChange(payload.node, 'executing')
    }
  } else if (action === 'node_complete') {
    streamingStatus.value = payload?.message || '完成'

    // 触发节点完成
    if (chatStore && payload?.node) {
      chatStore.emitNodeUnhighlight(payload.node)
      chatStore.emitNodeStatusChange(payload.node, 'completed')
    }
  } else if (action === 'error') {
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 错误: ${payload?.error || '未知错误'}`,
      error: true,
    })
  }
}

const handleChatMessage = (action, payload) => {
  if (action === 'start') {
    loading.value = true
    streamingStatus.value = payload?.message || '开始处理...'

    // 触发聊天开始
    if (chatStore) {
      chatStore.emitChatStart()
    }
  } else if (action === 'message') {
    // AI 消息
    if (payload?.type === 'ai' && payload?.content) {
      addMessage({
        id: Date.now() + Math.random(),
        type: 'ai',
        content: payload.content,
        node: payload.node,
        node_path: payload.node_path,
      })
    }
  } else if (action === 'complete') {
    loading.value = false
    streamingStatus.value = ''

    addMessage({
      id: Date.now(),
      type: 'system',
      content: '处理完成！',
    })
  } else if (action === 'error') {
    loading.value = false
    streamingStatus.value = ''

    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ ${payload?.error || '处理失败'}`,
      error: true,
    })
  }
}

const handleToolMessage = (action, payload) => {
  if (action === 'call') {
    // 工具调用 - 不显示，仅记录日志
    console.log('工具调用:', payload?.tool_name, payload?.tool_args)
  } else if (action === 'result') {
    // 工具结果 - 不显示，仅记录日志
    console.log('工具执行完成:', payload?.tool_name)
  } else if (action === 'activate_form') {
    // 激活表单 - 通知父组件展开 Canvas 并显示表单
    emit('show-form', payload?.prefill_data || null)
    
    // 添加系统消息提示
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '已打开故障检测工单，请在右侧面板填写信息',
    })
  } else if (action === 'form_processing') {
    loading.value = true
    streamingStatus.value = payload?.message || '正在处理表单...'
  } else if (action === 'form_complete') {
    loading.value = false
    streamingStatus.value = ''
  } else if (action === 'form_error') {
    loading.value = false
    streamingStatus.value = ''

    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ ${payload?.error || '表单处理失败'}`,
      error: true,
    })
  } else if (action === 'analysis_start') {
    // 分析开始 - 通知父组件开始分析
    emit('analysis-start', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '🔄 故障分析任务已启动，请关注右侧面板的执行情况',
    })
  } else if (action === 'analysis_step') {
    // 分析步骤 - 通知父组件添加步骤
    emit('analysis-step', payload)
  } else if (action === 'analysis_complete') {
    // 分析完成 - 通知父组件展示结果（不添加系统消息，因为 final_report 已经添加了）
    emit('analysis-complete', payload)
    
    // 注意：系统消息已在 handleAnalysisMessage 的 final_report 中添加，这里不再重复添加
  } else if (action === 'analysis_error') {
    // 分析错误
    emit('analysis-error', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 分析出错: ${payload?.error || '未知错误'}`,
      error: true,
    })
  } else if (action === 'analysis_result') {
    // 旧版分析结果 - 保持兼容
    emit('show-result', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '故障分析完成，请在右侧面板查看详细报告',
    })
  }
}

// ==================== 消息操作 ====================
const addMessage = (message) => {
  const msg = {
    ...message,
    timestamp: message.timestamp || new Date().toISOString(),
  }

  if (chatStore) {
    chatStore.addMessage(msg)
  } else {
    messages.value.push(msg)
  }

  scrollToBottom()
}

const sendMessage = () => {
  if (!inputMessage.value.trim() || loading.value || !wsConnected.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  addMessage({
    id: Date.now(),
    type: 'user',
    content: userMessage,
  })

  // 发送到 WebSocket
  sendWSMessage({
    type: 'chat',
    action: 'send',
    data: { message: userMessage },
  })
}

const sendQuickMessage = (message) => {
  if (!wsConnected.value) return
  inputMessage.value = message
  sendMessage()
}

// 发送表单数据到后端（供父组件调用）
const sendFormData = (formData) => {
  console.log('发送表单数据:', formData)
  
  // 如果有包装好的查询消息，先添加为用户消息
  if (formData.queryMessage) {
    addMessage({
      id: Date.now(),
      type: 'user',
      content: formData.queryMessage,
    })
  }
  
  // 发送表单数据到后端
  sendWSMessage({
    type: 'tool',
    action: 'form_submit',
    data: { 
      form_data: formData,
      query_message: formData.queryMessage // 同时发送查询消息
    },
  })
}

// ==================== 辅助函数 ====================
const renderMarkdown = (content) => {
  if (!content) return ''
  try {
    let html = marked.parse(content)

    // 处理行内数学公式 $...$
    html = html.replace(/\$([^$]+)\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula, {
          displayMode: false,
          throwOnError: false,
          errorColor: '#cc0000',
        })
      } catch (error) {
        return match
      }
    })

    // 处理块级数学公式 $$...$$
    html = html.replace(/\$\$([^$]+)\$\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula, {
          displayMode: true,
          throwOnError: false,
          errorColor: '#cc0000',
        })
      } catch (error) {
        return match
      }
    })

    return html
  } catch (error) {
    console.error('Markdown parse error:', error)
    return content
  }
}

const clearInput = () => {
  inputMessage.value = ''
}

const clearChat = () => {
  if (chatStore) {
    chatStore.clearMessages()
    chatStore.emitNodeStatusChange(null, 'default')
  } else {
    messages.value = []
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// ==================== 生命周期 ====================
onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  disconnectWebSocket()
})

// 监听消息变化
watch(() => messages.value, () => {
  scrollToBottom()
}, { deep: true })

// 监听加载状态
watch(() => loading.value, () => {
  scrollToBottom()
})

// 暴露方法给父组件
defineExpose({
  sendFormData,
  wsConnected,
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

/* Markdown 样式 */
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
  color: #2563eb;
}

.markdown-content :deep(h2) {
  font-size: 1.25rem;
  color: #3b82f6;
}

.markdown-content :deep(h3) {
  font-size: 1.125rem;
  color: #1F2937;
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

.markdown-content :deep(code) {
  background: #dbeafe;
  padding: 0.2rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.875em;
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
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
  border-left: 3px solid #3b82f6;
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
  color: #2563eb;
  text-decoration: none;
  border-bottom: 2px solid #bfdbfe;
  font-weight: 600;
  transition: all 0.2s;
}

.markdown-content :deep(a:hover) {
  color: #1d4ed8;
  border-bottom-color: #3b82f6;
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
  background: #dbeafe;
  font-weight: 700;
  color: #1d4ed8;
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
  border: 2px solid #bfdbfe;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.markdown-content :deep(hr) {
  border: none;
  height: 2px;
  background: #bfdbfe;
  margin: 2rem 0;
  border-radius: 2px;
}
</style>
