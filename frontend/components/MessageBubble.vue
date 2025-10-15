<template>
  <div class="message-wrapper">
    <!-- 用户消息 -->
    <div v-if="message.type === 'user'" class="flex justify-end">
      <div class="message-bubble message-user">
        <div class="flex items-start space-x-2">
          <div class="flex-1">
            <p class="whitespace-pre-wrap">{{ message.content }}</p>
          </div>
          <div class="text-xs opacity-75 mt-1">
            👤
          </div>
        </div>
        <div class="text-xs opacity-75 mt-1">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>

    <!-- AI助手消息 -->
    <div v-else-if="message.type === 'ai' || message.type === 'assistant'" class="flex justify-start">
      <div class="message-bubble message-ai">
        <div class="flex items-start space-x-2">
          <div class="text-lg">🤖</div>
          <div class="flex-1">
            <p class="whitespace-pre-wrap">{{ message.content }}</p>
            
            <!-- 工具调用信息 -->
            <div v-if="message.tool_calls && message.tool_calls.length > 0" class="mt-2">
              <div 
                v-for="(toolCall, index) in message.tool_calls" 
                :key="index"
                class="tool-call"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-2">
                    <span class="text-amber-600">🔧</span>
                    <span class="font-medium text-amber-800">
                      调用工具: {{ getToolName(toolCall.name) }}
                    </span>
                  </div>
                  <button 
                    @click="toggleToolDetails(index)"
                    class="text-xs text-amber-600 hover:text-amber-800"
                  >
                    {{ expandedTools[index] ? '收起' : '详情' }}
                  </button>
                </div>
                
                <!-- 工具调用详情 -->
                <div v-if="expandedTools[index]" class="mt-2 text-sm">
                  <div class="bg-amber-25 p-2 rounded">
                    <div><strong>参数:</strong></div>
                    <pre class="text-xs mt-1 overflow-x-auto">{{ formatToolArgs(toolCall.args) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="text-xs text-gray-500 mt-1">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>

    <!-- 工具调用消息 -->
    <div v-else-if="message.type === 'tool_call'" class="flex justify-start">
      <div class="message-bubble message-tool">
        <div class="flex items-start space-x-2">
          <div class="text-lg">🔧</div>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <div class="font-medium text-amber-800">
                工具调用: {{ getToolName(message.name) }}
              </div>
              <button 
                @click="toggleToolCallDetails"
                class="text-xs text-amber-600 hover:text-amber-800"
              >
                {{ expandedToolCall ? '收起' : '详情' }}
              </button>
            </div>
            
            <!-- 简要信息（默认显示） -->
            <div v-if="!expandedToolCall" class="text-sm text-amber-700">
              <div v-if="message.result">
                <span class="text-xs text-amber-600">执行完成</span>
              </div>
              <div v-else>
                <span class="text-xs text-amber-600">执行中...</span>
              </div>
            </div>
            
            <!-- 详细信息（展开时显示） -->
            <div v-if="expandedToolCall" class="text-sm">
              <div class="mb-2">
                <strong>输入参数:</strong>
                <pre class="bg-amber-50 p-2 rounded mt-1 text-xs overflow-x-auto">{{ formatToolArgs(message.args) }}</pre>
              </div>
              <div v-if="message.result">
                <strong>执行结果:</strong>
                <div class="tool-result mt-1">
                  <ToolResult :result="message.result" :tool-name="message.name" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="text-xs text-amber-600 mt-1">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>

    <!-- 系统消息 -->
    <div v-else-if="message.type === 'system'" class="flex justify-center">
      <div class="message-bubble message-system">
        <div class="flex items-center space-x-2">
          <span class="text-green-600">ℹ️</span>
          <span>{{ message.content }}</span>
        </div>
        <div class="text-xs text-green-600 mt-1 text-center">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>

    <!-- 错误消息 -->
    <div v-else-if="message.error" class="flex justify-start">
      <div class="message-bubble bg-red-100 text-red-800 border border-red-300">
        <div class="flex items-start space-x-2">
          <span class="text-red-600">❌</span>
          <div class="flex-1">
            <p>{{ message.content }}</p>
            <div v-if="message.error_details" class="text-xs mt-1 opacity-75">
              {{ message.error_details }}
            </div>
          </div>
        </div>
        <div class="text-xs text-red-600 mt-1">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>

    <!-- 未知类型消息 -->
    <div v-else class="flex justify-start">
      <div class="message-bubble bg-gray-100 text-gray-800">
        <div class="flex items-start space-x-2">
          <span>❓</span>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <div class="font-medium text-gray-800">
                未知消息类型
              </div>
              <button 
                @click="toggleUnknownMessageDetails"
                class="text-xs text-gray-600 hover:text-gray-800"
              >
                {{ expandedUnknownMessage ? '收起' : '详情' }}
              </button>
            </div>
            
            <!-- 简要信息（默认显示） -->
            <div v-if="!expandedUnknownMessage" class="text-sm text-gray-700">
              <span class="text-xs text-gray-600">类型: {{ message.type || '未知' }}</span>
            </div>
            
            <!-- 详细信息（展开时显示） -->
            <div v-if="expandedUnknownMessage" class="text-sm">
              <p>{{ message.content || JSON.stringify(message) }}</p>
              <div class="text-xs mt-1 opacity-75">
                类型: {{ message.type || '未知' }}
              </div>
            </div>
          </div>
        </div>
        <div class="text-xs text-gray-600 mt-1">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

// Props
const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

// Emits
const emit = defineEmits(['tool-expand'])

// 响应式数据
const expandedTools = reactive({})
const expandedToolCall = ref(false)
const expandedUnknownMessage = ref(false)

// 方法
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  })
}

const getToolName = (toolName) => {
  const toolNames = {
    'yolo_detect_tool': 'YOLO图像检测',
    'city_weather': '天气查询',
    'search_tool': '搜索工具',
    'calculator': '计算器'
  }
  return toolNames[toolName] || toolName || '未知工具'
}

const formatToolArgs = (args) => {
  if (!args) return 'null'
  if (typeof args === 'string') return args
  return JSON.stringify(args, null, 2)
}

const toggleToolDetails = (index) => {
  expandedTools[index] = !expandedTools[index]
  emit('tool-expand', {
    toolIndex: index,
    expanded: expandedTools[index],
    message: props.message
  })
}

const toggleToolCallDetails = () => {
  expandedToolCall.value = !expandedToolCall.value
}

const toggleUnknownMessageDetails = () => {
  expandedUnknownMessage.value = !expandedUnknownMessage.value
}
</script>

<style scoped>
.message-wrapper {
  @apply w-full;
}

.message-bubble {
  @apply max-w-md px-4 py-3 rounded-lg text-sm shadow-sm;
}

.message-user {
  @apply bg-blue-500 text-white;
  border-radius: 18px 4px 18px 18px;
}

.message-ai {
  @apply bg-white text-gray-800 border border-gray-200;
  border-radius: 4px 18px 18px 18px;
}

.message-tool {
  @apply bg-yellow-50 text-yellow-900 border border-yellow-200;
  border-radius: 4px 18px 18px 18px;
}

.message-system {
  @apply bg-green-50 text-green-900 border border-green-200 text-center;
  border-radius: 18px;
}

.tool-call {
  @apply bg-amber-50 border border-amber-200 rounded-md p-3 mt-2;
}

.tool-result {
  @apply bg-emerald-50 border border-emerald-200 rounded-md p-3;
}

pre {
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
