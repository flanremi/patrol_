<template>
  <div class="modern-chat flex flex-col h-full bg-white relative overflow-hidden">
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
           class="max-w-3xl mx-auto px-8 text-center w-full">
        <h1 class="text-3xl font-semibold text-gray-900 mb-2">
          有什么可以帮您的？
        </h1>
        
        <!-- 输入区域 - 空状态时放在中部 -->
        <div class="mt-8">
          <div class="max-w-3xl mx-auto px-4">
            <!-- 输入框容器 - 文心一言风格 -->
            <div class="relative bg-white border border-gray-200 rounded-3xl shadow-lg hover:shadow-xl transition-shadow duration-300">
              <!-- 输入框 -->
              <textarea
                ref="inputRef"
                v-model="inputMessage"
                @keydown="handleKeydown"
                :disabled="isInputDisabled"
                :placeholder="getInputPlaceholder"
                class="w-full px-5 py-4 text-base text-gray-800 placeholder-gray-400 bg-transparent border-none outline-none resize-none"
                rows="1"
                style="min-height: 56px; max-height: 200px;"
              ></textarea>

              <!-- 底部工具栏 -->
              <div class="flex items-center justify-between px-3 pb-3">
                <div class="flex items-center gap-2">
                  <!-- 附件按钮 -->
                  <button class="p-2 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                    <PlusIcon class="w-5 h-5" />
                  </button>
                  <!-- 深度思考按钮 -->
                  <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 transition-colors border border-blue-100">
                    <SparklesIcon class="w-4 h-4" />
                    <span>思考·自动</span>
                  </button>
                </div>

                <div class="flex items-center gap-2">
                  <!-- 语音按钮 -->
                  <button class="p-2 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                    <MicrophoneIcon class="w-5 h-5" />
                  </button>
                  <!-- 发送按钮 -->
                  <button
                    @click="sendMessage"
                    :disabled="isSendDisabled"
                    class="p-2.5 rounded-full transition-all duration-200 flex items-center justify-center"
                    :class="isSendDisabled
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-black text-white hover:bg-gray-800 hover:scale-105'"
                  >
                    <PaperAirplaneIcon v-if="!isSending" class="w-5 h-5" />
                    <ArrowPathIcon v-else class="w-5 h-5 animate-spin" />
                  </button>
                </div>
              </div>
            </div>

            <!-- 快捷工具标签 - 放在输入框下方 -->
            <div class="flex items-center justify-center gap-1.5 mt-5">
              <button
                v-for="tool in quickTools"
                :key="tool.id"
                @click="selectTool(tool)"
                class="flex items-center gap-1 px-2 py-1 rounded-full text-xs transition-all duration-200 whitespace-nowrap"
                :class="currentTool === tool.id 
                  ? 'bg-blue-50 border border-blue-300 text-blue-600' 
                  : 'bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 text-gray-600 hover:text-blue-600'"
              >
                <span>{{ tool.icon }}</span>
                <span>{{ tool.name }}</span>
              </button>
            </div>

            <!-- 底部提示 -->
            <div class="flex items-center justify-center mt-4">
              <span class="text-xs text-gray-400">
                按 Enter 发送消息，Shift + Enter 换行
              </span>
            </div>
          </div>
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
              :class="getSystemMessageClass(message)"
            >
              <CheckCircleIcon v-if="!message.error && !message.clickable"
                               class="w-3.5 h-3.5"/>
              <ExclamationCircleIcon v-else-if="message.error"
                                     class="w-3.5 h-3.5"/>
              <component v-else-if="message.clickable"
                         :is="getMessageIcon(message)"
                         class="w-3.5 h-3.5"/>
              <span>{{message.content}}</span>
              <!-- 可点击的操作按钮 -->
              <button
                v-if="message.clickable"
                @click="handleMessageAction(message)"
                class="ml-2 px-2 py-0.5 rounded-lg text-[11px] font-bold transition-all"
                :class="message.actionType === 'form' 
                  ? 'bg-blue-200 hover:bg-blue-300 text-blue-700' 
                  : message.actionType === 'qualityResult'
                    ? 'bg-emerald-200 hover:bg-emerald-300 text-emerald-800'
                    : message.actionType === 'gradeResult'
                      ? 'bg-purple-200 hover:bg-purple-300 text-purple-800'
                      : 'bg-green-200 hover:bg-green-300 text-green-700'"
              >
                {{ message.actionLabel || '查看' }}
              </button>
            </div>
          </div>

        </div>

        <!-- 加载指示器 - 支持并发显示 -->
        <div v-if="hasActiveTasks || streamingStatus"
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
                <span class="text-[14px] text-gray-700 font-semibold">
                  {{ streamingStatus || (pendingMessages.size > 1 ? `处理中 (${pendingMessages.size} 个请求)...` : '正在思考...') }}
                </span>
                <!-- 并发任务数标记 -->
                <span v-if="pendingMessages.size > 1" 
                      class="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-600">
                  {{ pendingMessages.size }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 - 文心一言风格 (有消息时显示在底部) -->
    <div v-if="messages.length > 0" class="flex-shrink-0 bg-white relative z-10 pb-6">
      <div class="max-w-3xl mx-auto px-4">
        <!-- 输入框容器 - 文心一言风格 -->
        <div class="relative bg-white border border-gray-200 rounded-3xl shadow-lg hover:shadow-xl transition-shadow duration-300">
          <!-- 输入框 -->
          <textarea
            ref="inputRef"
            v-model="inputMessage"
            @keydown.enter.prevent="sendMessage"
            :disabled="isInputDisabled"
            :placeholder="getInputPlaceholder"
            class="w-full px-5 py-4 text-base text-gray-800 placeholder-gray-400 bg-transparent border-none outline-none resize-none"
            rows="1"
            style="min-height: 56px; max-height: 200px;"
          ></textarea>

          <!-- 底部工具栏 -->
          <div class="flex items-center justify-between px-3 pb-3">
            <div class="flex items-center gap-2">
              <!-- 附件按钮 -->
              <button class="p-2 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                <PlusIcon class="w-5 h-5" />
              </button>
              <!-- 深度思考按钮 -->
              <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 transition-colors border border-blue-100">
                <SparklesIcon class="w-4 h-4" />
                <span>思考·自动</span>
              </button>
            </div>

            <div class="flex items-center gap-2">
              <!-- 语音按钮 -->
              <button class="p-2 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
                <MicrophoneIcon class="w-5 h-5" />
              </button>
              <!-- 发送按钮 -->
              <button
                @click="sendMessage"
                :disabled="isSendDisabled"
                class="p-2.5 rounded-full transition-all duration-200 flex items-center justify-center"
                :class="isSendDisabled
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-black text-white hover:bg-gray-800 hover:scale-105'"
              >
                <PaperAirplaneIcon v-if="!isSending" class="w-5 h-5" />
                <ArrowPathIcon v-else class="w-5 h-5 animate-spin" />
              </button>
            </div>
          </div>
        </div>

        <!-- 快捷工具标签 - 放在输入框下方 -->
        <div class="flex items-center justify-center gap-2 mt-4 flex-wrap">
          <button
            v-for="tool in quickTools"
            :key="tool.id"
            @click="selectTool(tool)"
            class="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm transition-all duration-200"
            :class="currentTool === tool.id 
              ? 'bg-blue-50 border border-blue-300 text-blue-600' 
              : 'bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 text-gray-600 hover:text-blue-600'"
          >
            <span>{{ tool.icon }}</span>
            <span>{{ tool.name }}</span>
          </button>
        </div>

        <!-- 底部提示 -->
        <div class="flex items-center justify-center mt-3">
          <span class="text-xs text-gray-400">
            按 Enter 发送消息，Shift + Enter 换行
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentListIcon,
  DocumentChartBarIcon,
  ExclamationCircleIcon,
  MicrophoneIcon,
  PaperAirplaneIcon,
  PlusIcon,
  SparklesIcon,
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
  'show-analyzing',
  'hide-canvas',
  'analysis-start',
  'analysis-step',
  'analysis-complete',
  'analysis-error',
  'tool-change',
  'quiz-generated',
  'grade-result',
  'courseware-generated',
  'agent-response',
  'quality-check-result',
  'connection-status-change',
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

// 分析状态 - 分析进行中时仍允许对话
const isAnalyzing = ref(false)

// 并发对话追踪：存储进行中的消息 ID
const pendingMessages = ref(new Set())

// 分析任务存储：task_id -> 任务数据（报告、步骤等）
const analysisTasks = ref(new Map())

// 当前活跃的分析任务 ID
const currentTaskId = ref(null)

// WebSocket 状态
const wsConnected = ref(false)
const wsConnecting = ref(false)
let ws = null
let reconnectTimer = null
const maxReconnectAttempts = 5
let reconnectAttempts = 0

// 工具选择状态（与 ToolSelector 默认列表一致，用于气泡展示）
const MODULE_TOOLS = [
  { id: 'inspection', name: '故障检测工单', icon: '🔍' },
  { id: 'planning', name: '巡检计划', icon: '📅' },
  { id: 'repair', name: '维修方案', icon: '🔧' },
  { id: 'quality', name: '工单质检', icon: '✅' },
  { id: 'training', name: '员工培训', icon: '📚' },
  { id: 'field_guidance', name: '现场作业指导', icon: '📍' },
]

const currentTool = ref('inspection')
const currentToolInfo = ref({
  id: 'inspection',
  name: '故障检测工单',
  icon: '🔍'
})

const currentToolBadge = computed(() =>
  MODULE_TOOLS.find((t) => t.id === currentTool.value) || currentToolInfo.value
)

const getToolBadgeClass = (toolId) => {
  const map = {
    inspection: 'bg-blue-100 text-blue-800 border border-blue-200',
    planning: 'bg-green-100 text-green-800 border border-green-200',
    repair: 'bg-orange-100 text-orange-800 border border-orange-200',
    quality: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
    training: 'bg-purple-100 text-purple-800 border border-purple-200',
    field_guidance: 'bg-teal-100 text-teal-800 border border-teal-200',
  }
  return map[toolId] || 'bg-slate-100 text-slate-800 border border-slate-200'
}

// 快捷工具标签 - 放在输入框下方
const quickTools = [
  { id: 'inspection', name: '故障检测工单', icon: '🔍' },
  { id: 'planning', name: '巡检计划生成', icon: '📋' },
  { id: 'repair', name: '维修方案咨询', icon: '🛠️' },
  { id: 'quality', name: '工单质量检查', icon: '✅' },
  { id: 'training', name: '员工培训系统', icon: '📚' },
  { id: 'field_guidance', name: '现场作业指导', icon: '📍'},
]

// 选择工具
const selectTool = (tool) => {
  handleToolChange(tool)
}

// 输入框占位符
const getInputPlaceholder = computed(() => {
  if (!wsConnected.value) return '正在连接服务器...'
  if (isAnalyzing.value) return '分析进行中，您仍可继续提问或查询知识库...'
  if (pendingMessages.value.size > 0) return `${pendingMessages.value.size} 个请求处理中，可继续发送新消息...`
  return '输入你的问题，开启知识问答与智能巡检'
})

// 是否正在发送消息（短暂状态，防止重复点击）
const isSending = ref(false)

// 输入框是否禁用（仅在未连接或正在发送瞬间禁用，并发处理中不禁用）
const isInputDisabled = computed(() => {
  return !wsConnected.value || isSending.value
})

// 发送按钮是否禁用
const isSendDisabled = computed(() => {
  return !inputMessage.value.trim() || !wsConnected.value || isSending.value
})

// 是否有任何请求在处理中
const hasActiveTasks = computed(() => {
  return pendingMessages.value.size > 0 || isAnalyzing.value
})

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
      emit('connection-status-change', 'connected')
    }

    ws.onclose = (event) => {
      console.log(`❌ WebSocket 断开: code=${event.code}`)
      wsConnected.value = false
      wsConnecting.value = false
      emit('connection-status-change', 'disconnected')

      // 自动重连
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        console.log(`🔄 尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})...`)
        emit('connection-status-change', 'connecting')
        reconnectTimer = setTimeout(connectWebSocket, 3000)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      wsConnecting.value = false
      emit('connection-status-change', 'disconnected')
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
  
  const taskId = payload?.task_id
  
  // 确保任务存在于本地存储
  const ensureTask = () => {
    if (taskId && !analysisTasks.value.has(taskId)) {
      analysisTasks.value.set(taskId, {
        task_id: taskId,
        input_data: payload?.input || payload?.defect_input || {},
        status: 'running',
        steps: [],
        final_report: null,
        thinking_processes: [],
        created_at: new Date().toISOString()
      })
    }
    return taskId ? analysisTasks.value.get(taskId) : null
  }
  
  if (action === 'analysis_start') {
    // 分析开始 - 通知父组件展开 Canvas 并切换到分析视图
    isAnalyzing.value = true
    currentTaskId.value = taskId
    const task = ensureTask()
    if (task) task.status = 'running'
    
    emit('analysis-start', {
      task_id: taskId,
      message: payload?.message || '开始分析...',
      input: payload?.defect_input || payload?.input || {},
      timestamp: payload?.timestamp
    })
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `🔄 故障分析任务已启动 [${taskId || ''}]（点击可查看分析流程）。分析期间您仍可继续对话。`,
      clickable: true,
      actionType: 'analyzing',
      actionLabel: '查看流程',
      taskId: taskId,
      analyzingData: {
        task_id: taskId,
        input: payload?.defect_input || payload?.input || {},
        timestamp: payload?.timestamp,
      },
    })
  } else if (action === 'thinking_step') {
    // 思考步骤 - 存储并转发给父组件
    const task = ensureTask()
    const stepData = {
      node: payload?.node || 'process',
      title: payload?.title || '处理中',
      summary: payload?.content || payload?.summary || '',
      content: payload?.content,
      data: payload?.data,
      status: 'complete',
      step_number: payload?.step_number
    }
    if (task) task.steps.push(stepData)
    emit('analysis-step', stepData)
  } else if (action === 'node_start') {
    // 节点开始
    const task = ensureTask()
    const stepData = {
      node: payload?.node || 'process',
      title: payload?.title || `${payload?.node || '节点'} 开始`,
      summary: payload?.message || '正在处理...',
      status: 'running'
    }
    if (task) task.steps.push(stepData)
    emit('analysis-step', stepData)
  } else if (action === 'node_complete') {
    // 节点完成 - 更新步骤状态
    const task = ensureTask()
    const stepData = {
      node: payload?.node || 'process',
      title: payload?.title || `${payload?.node || '节点'} 完成`,
      summary: payload?.message || '处理完成',
      content: payload?.content,
      data: payload?.data,
      status: 'complete'
    }
    if (task) task.steps.push(stepData)
    emit('analysis-step', stepData)
  } else if (action === 'final_report') {
    // 最终报告 - 存储并添加系统提示
    // 注意：report_markdown 是 fault_analysis_core_vector 使用的字段名
    // final_report 是其他模块使用的字段名
    isAnalyzing.value = false
    const task = ensureTask()
    
    // 兼容多种字段名
    const finalReport = payload?.final_report || payload?.report_markdown || payload?.content || ''
    
    console.log(`📊 [final_report] 收到报告, task_id=${taskId}, 长度=${finalReport.length}, payload_keys=`, Object.keys(payload || {}))
    
    const resultData = {
      task_id: taskId,
      final_report: finalReport,
      report_markdown: finalReport,  // 兼容字段
      retry_count: payload?.retry_count || 0,
      thinking_processes: payload?.thinking_processes || [],
      input: payload?.input || payload?.defect_input || {},
      timestamp: payload?.timestamp || new Date().toISOString()
    }
    
    // 存储到本地任务
    if (task) {
      task.status = 'completed'
      task.final_report = finalReport
      task.thinking_processes = resultData.thinking_processes
      task.completed_at = new Date().toISOString()
      console.log(`✅ [analysis] 任务完成: ${taskId}，报告长度: ${task.final_report?.length || 0}`)
    }
    
    emit('analysis-complete', resultData)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `✅ 故障分析完成 [${taskId || ''}]，请点击查看详细报告`,
      clickable: true,
      actionType: 'result',
      actionLabel: '查看报告',
      taskId: taskId,
      resultData: resultData,
    })
  } else if (action === 'analysis_complete') {
    // 分析完成统计（在 final_report 之后发送，不添加消息避免重复）
    isAnalyzing.value = false
    const task = ensureTask()
    
    // 兼容多种字段名
    const finalReport = payload?.final_report || payload?.report_markdown || ''
    if (task && finalReport) {
      task.status = 'completed'
      task.final_report = finalReport
      task.thinking_processes = payload?.thinking_processes || []
    }
    console.log('📊 分析统计:', payload)
    emit('analysis-complete', payload)
  } else if (action === 'error') {
    // 分析错误
    isAnalyzing.value = false
    const task = ensureTask()
    if (task) {
      task.status = 'error'
      task.error = payload?.error
    }
    emit('analysis-error', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 分析出错 [${taskId || ''}]: ${payload?.error || '未知错误'}`,
      error: true,
      taskId: taskId,
    })
  }
}

/** 后端已有回复（含 AI 正文、一轮结束或错误）时通知侧栏表单恢复可提交 */
const notifyAgentResponse = (detail = {}) => {
  emit('agent-response', detail)
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
  } else if (action === 'tool_selected') {
    // 后端确认工具切换（避免误报未知动作）
    console.log('✅ 工具已切换:', payload?.tool_id, payload?.tool_info)
  } else if (action === 'error') {
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 错误: ${payload?.error || '未知错误'}`,
      error: true,
    })
    notifyAgentResponse({ source: 'system', kind: 'error' })
  }
}

const handleChatMessage = (action, payload) => {
  const messageId = payload?.message_id
  
  if (action === 'start') {
    // 追踪新的消息处理
    if (messageId) {
      pendingMessages.value.add(messageId)
    }
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
        messageId: messageId, // 关联消息 ID
      })
      if (String(payload.content).trim()) {
        notifyAgentResponse({ source: 'chat', kind: 'message' })
      }
    }
  } else if (action === 'complete') {
    // 移除已完成的消息追踪
    if (messageId) {
      pendingMessages.value.delete(messageId)
    }
    
    // 只有当所有消息都处理完才清除 loading 状态
    if (pendingMessages.value.size === 0) {
      loading.value = false
      streamingStatus.value = ''
    }

    // 不再添加"处理完成"系统消息，避免并发时消息混乱
    console.log(`✅ 消息处理完成 [${messageId || 'unknown'}]`)
    notifyAgentResponse({ source: 'chat', kind: 'complete' })
  } else if (action === 'error') {
    // 移除失败的消息追踪
    if (messageId) {
      pendingMessages.value.delete(messageId)
    }
    
    if (pendingMessages.value.size === 0) {
      loading.value = false
      streamingStatus.value = ''
    }

    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ ${payload?.error || '处理失败'}`,
      error: true,
      messageId: messageId,
    })
    notifyAgentResponse({ source: 'chat', kind: 'error' })
  }
}

const handleToolMessage = (action, payload) => {
  if (action === 'call') {
    // 工具调用 - 不显示，仅记录日志
    console.log('工具调用:', payload?.tool_name, payload?.tool_args)
  } else if (action === 'result') {
    // 工具结果 - 不显示，仅记录日志
    console.log('工具执行完成:', payload?.tool_name)
  } else if (action === 'knowledge_query') {
    // 知识库查询开始
    console.log('📚 知识库查询:', payload?.query)
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `📚 正在查询知识库: "${payload?.query?.substring(0, 30)}..."`,
    })
  } else if (action === 'knowledge_result') {
    // 知识库查询完成
    console.log('📚 知识库查询完成:', payload?.result_length, '字符')
  } else if (action === 'activate_form') {
    // 激活表单 - 通知父组件展开 Canvas 并显示表单
    emit('show-form', payload?.prefill_data || null)
    
    // 添加可点击的系统消息
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '已打开故障检测工单，请在右侧面板填写信息',
      clickable: true,
      actionType: 'form',
      actionLabel: '打开工单',
      prefillData: payload?.prefill_data || null,
    })
  } else if (action === 'task_created') {
    // 任务创建 - 存储任务信息
    const taskId = payload?.task_id
    if (taskId) {
      analysisTasks.value.set(taskId, {
        task_id: taskId,
        input_data: payload?.input_data || {},
        status: 'running',
        steps: [],
        final_report: null,
        thinking_processes: [],
        created_at: new Date().toISOString()
      })
      currentTaskId.value = taskId
      console.log(`📋 任务创建: ${taskId}`, payload?.input_data)
    }
  } else if (action === 'task_detail') {
    // 任务详情响应 - 更新本地存储并显示
    const taskId = payload?.task_id
    if (taskId) {
      analysisTasks.value.set(taskId, payload)
      // 如果有最终报告，显示结果
      if (payload?.final_report) {
        emit('show-result', payload)
      }
    }
  } else if (action === 'form_processing') {
    loading.value = true
    streamingStatus.value = payload?.message || '正在处理表单...'
  } else if (action === 'form_complete') {
    loading.value = false
    streamingStatus.value = ''
    notifyAgentResponse({ source: 'tool', kind: 'form_complete' })
  } else if (action === 'form_error') {
    loading.value = false
    streamingStatus.value = ''

    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ ${payload?.error || '表单处理失败'}`,
      error: true,
      taskId: payload?.task_id,
    })
    notifyAgentResponse({ source: 'tool', kind: 'form_error' })
  } else if (action === 'analysis_start') {
    // 分析开始 - 通知父组件开始分析
    const taskId = payload?.task_id
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      task.status = 'running'
    }
    currentTaskId.value = taskId
    isAnalyzing.value = true
    
    emit('analysis-start', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `🔄 故障分析任务已启动 [${taskId || ''}]（点击可查看分析流程）`,
      clickable: true,
      actionType: 'analyzing',
      actionLabel: '查看流程',
      taskId: taskId,
      analyzingData: payload,
    })
  } else if (action === 'analysis_step') {
    // 分析步骤 - 存储并通知父组件
    const taskId = payload?.task_id
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      task.steps.push(payload)
    }
    emit('analysis-step', payload)
  } else if (action === 'analysis_complete' || action === 'final_report') {
    // 分析完成 - 存储最终报告
    // 兼容多种字段名：final_report, report_markdown
    const taskId = payload?.task_id
    const finalReport = payload?.final_report || payload?.report_markdown || ''
    
    console.log(`📊 [tool/${action}] task_id=${taskId}, 报告长度=${finalReport.length}, payload_keys=`, Object.keys(payload || {}))
    
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      task.status = 'completed'
      task.final_report = finalReport
      task.thinking_processes = payload?.thinking_processes || []
      task.completed_at = new Date().toISOString()
      console.log(`✅ 任务完成: ${taskId}，报告长度: ${task.final_report?.length || 0}`)
    }
    
    isAnalyzing.value = false
    
    // 标准化 payload 确保有 final_report 字段
    const normalizedPayload = {
      ...payload,
      final_report: finalReport,
      report_markdown: finalReport
    }
    emit('analysis-complete', normalizedPayload)
    
    // 添加可点击的完成消息
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `✅ 故障分析完成 [${taskId || ''}]，请点击查看详细报告`,
      clickable: true,
      actionType: 'result',
      actionLabel: '查看报告',
      taskId: taskId,
      resultData: normalizedPayload,
    })
  } else if (action === 'analysis_error') {
    // 分析错误
    const taskId = payload?.task_id
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      task.status = 'error'
      task.error = payload?.error
    }
    
    isAnalyzing.value = false
    emit('analysis-error', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `❌ 分析出错 [${taskId || ''}]: ${payload?.error || '未知错误'}`,
      error: true,
      taskId: taskId,
    })
  } else if (action === 'analysis_result') {
    // 旧版分析结果 - 保持兼容
    emit('show-result', payload)
    
    addMessage({
      id: Date.now(),
      type: 'system',
      content: '故障分析完成，请在右侧面板查看详细报告',
      clickable: true,
      actionType: 'result',
      actionLabel: '查看报告',
      resultData: payload,
    })
  } 
  // ========== 新模块消息处理 ==========
  else if (action === 'quiz_generated') {
    // 培训试题生成完成
    emit('quiz-generated', payload?.quiz)
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `📚 培训试题已生成，请在右侧面板作答`,
      clickable: true,
      actionType: 'training',
      actionLabel: '开始作答',
      quizData: payload?.quiz,
    })
    notifyAgentResponse({ source: 'tool', kind: 'quiz_generated' })
  } else if (action === 'grade_result') {
    // 批改结果
    emit('grade-result', payload?.grade)
    const score = payload?.grade?.score || 0
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `📝 作业批改完成，得分：${Math.round(score)} 分`,
      clickable: true,
      actionType: 'gradeResult',
      actionLabel: '查看详情',
      gradeData: payload?.grade,
    })
    notifyAgentResponse({ source: 'tool', kind: 'grade_result' })
  } else if (action === 'courseware_generated') {
    // 课件生成完成
    emit('courseware-generated', payload?.courseware)
    addMessage({
      id: Date.now(),
      type: 'system',
      content: `📖 培训课件已生成`,
    })
    notifyAgentResponse({ source: 'tool', kind: 'courseware_generated' })
  } else if (action === 'quality_check_result') {
    // 工单质检结果
    const passed = payload?.passed
    emit('quality-check-result', {
      passed,
      issues: payload?.issues || [],
      report: payload?.report || '',
    })
    addMessage({
      id: Date.now(),
      type: 'system',
      content: passed 
        ? `✅ 工单审核通过` 
        : `❌ 工单审核不通过，发现 ${payload?.issues?.length || 0} 个问题`,
      clickable: true,
      actionType: 'qualityResult',
      actionLabel: '查看详情',
      qualityData: payload,
    })
    notifyAgentResponse({ source: 'tool', kind: 'quality_check_result' })
  } else if (action === 'knowledge_fragments') {
    // 知识片段检索结果（培训模块）
    console.log('📚 检索到知识片段:', payload?.fragments?.length)
  } else if (action === 'thinking_step') {
    // 思考步骤（各模块通用）
    console.log(`🔄 [${payload?.agent_type}] ${payload?.title}: ${payload?.summary}`)
  }
}

// 获取任务数据
const getTask = (taskId) => {
  return analysisTasks.value.get(taskId)
}

// 请求任务详情（从后端获取）
const requestTaskDetail = (taskId) => {
  sendWSMessage({
    type: 'tool',
    action: 'get_task',
    data: { task_id: taskId }
  })
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

const handleKeydown = (event) => {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Shift + Enter: allow newline (default behavior)
      return
    } else {
      // Enter only: prevent default and send message
      event.preventDefault()
      sendMessage()
    }
  }
}

const sendMessage = () => {
  if (!inputMessage.value.trim() || !wsConnected.value || isSending.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  
  // 设置发送状态（短暂，仅防止重复点击）
  isSending.value = true

  // 生成本地消息 ID 用于关联（后端会返回自己的 message_id）
  const localMsgId = Date.now()

  // 添加用户消息
  addMessage({
    id: localMsgId,
    type: 'user',
    content: userMessage,
  })

  // 发送到 WebSocket
  const sent = sendWSMessage({
    type: 'chat',
    action: 'send',
    data: { message: userMessage },
  })
  
  if (sent) {
    console.log(`📤 消息已发送: "${userMessage.substring(0, 30)}..."`)
  }
  
  // 短暂延迟后恢复发送状态（允许连续发送新消息）
  setTimeout(() => {
    isSending.value = false
  }, 300)
}

const sendQuickMessage = (message) => {
  if (!wsConnected.value) return
  inputMessage.value = message
  sendMessage()
}

// 处理工具切换
const handleToolChange = (tool) => {
  console.log('🔄 切换工具:', tool)
  currentTool.value = tool.id
  currentToolInfo.value = tool
  
  // 通知后端切换工具
  sendWSMessage({
    type: 'system',
    action: 'select_tool',
    data: { tool_id: tool.id }
  })
  
  // 添加系统消息提示
  addMessage({
    id: Date.now(),
    type: 'system',
    content: `已切换到 ${tool.icon} ${tool.name} 模块`,
    toolSwitch: true
  })
  
  // 通知父组件工具已切换
  emit('tool-change', tool)
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
// 获取系统消息样式
const getSystemMessageClass = (message) => {
  if (message.error) return 'bg-red-50 text-red-600 border-red-200'
  if (message.clickable) {
    if (message.actionType === 'form') return 'bg-blue-50 text-blue-600 border-blue-200 cursor-pointer hover:bg-blue-100 transition-colors'
    if (message.actionType === 'result') return 'bg-green-50 text-green-600 border-green-200 cursor-pointer hover:bg-green-100 transition-colors'
    if (message.actionType === 'qualityResult') return 'bg-emerald-50 text-emerald-700 border-emerald-200 cursor-pointer hover:bg-emerald-100 transition-colors'
    if (message.actionType === 'gradeResult') return 'bg-purple-50 text-purple-700 border-purple-200 cursor-pointer hover:bg-purple-100 transition-colors'
  }
  return 'bg-blue-50 text-blue-600 border-blue-200'
}

// 获取消息图标
const getMessageIcon = (message) => {
  if (message.actionType === 'form') return ClipboardDocumentListIcon
  if (message.actionType === 'result') return DocumentChartBarIcon
  return CheckCircleIcon
}

// 处理消息点击动作
const handleMessageAction = (message) => {
  if (message.actionType === 'form') {
    emit('show-form', message.prefillData || null)
  } else if (message.actionType === 'analyzing') {
    // 如果有 taskId，从本地存储获取任务数据
    const taskId = message.taskId
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      emit('show-analyzing', { ...message.analyzingData, task })
    } else {
      emit('show-analyzing', message.analyzingData || null)
    }
  } else if (message.actionType === 'result') {
    // 优先从本地存储获取完整的任务数据
    const taskId = message.taskId
    if (taskId && analysisTasks.value.has(taskId)) {
      const task = analysisTasks.value.get(taskId)
      console.log(`📊 点击查看报告 [${taskId}]，报告长度: ${task.final_report?.length || 0}`)
      emit('show-result', {
        task_id: taskId,
        final_report: task.final_report,
        thinking_processes: task.thinking_processes,
        input: task.input_data,
        steps: task.steps,
        status: task.status,
        ...message.resultData
      })
    } else if (message.resultData) {
      emit('show-result', message.resultData)
    } else {
      // 如果本地没有数据，请求后端
      if (taskId) {
        requestTaskDetail(taskId)
      }
    }
  } else if (message.actionType === 'qualityResult' && message.qualityData) {
    emit('quality-check-result', {
      passed: message.qualityData.passed,
      issues: message.qualityData.issues || [],
      report: message.qualityData.report || '',
    })
  }
}

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

// 发送模块消息到后端（供父组件调用）
const sendModuleMessage = (action, data) => {
  console.log(`📦 发送模块消息: action=${action}`, data)
  sendWSMessage({
    type: 'module',
    action: action,
    data: {
      tool_id: currentTool.value,
      ...data
    }
  })
}

// 暴露方法给父组件
defineExpose({
  sendFormData,
  sendModuleMessage,
  wsConnected,
  isAnalyzing,
  analysisTasks,
  currentTaskId,
  currentTool,
  currentToolInfo,
  getTask,
  requestTaskDetail,
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
