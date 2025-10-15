<template>
  <div class="chat-interface flex flex-col h-full">
    <!-- 聊天消息区域 -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50"
    >
      <!-- 欢迎消息 -->
      <div v-if="messages.length === 0" class="text-center text-gray-500 py-8">
        <div class="text-4xl mb-2">🤖</div>
        <p>欢迎使用 LangGraph 智能对话系统</p>
        <p class="text-sm mt-1">发送消息开始对话，系统会展示完整的执行流程</p>
      </div>

      <!-- 消息列表 -->
      <MessageBubble
        v-for="message in messages"
        :key="message.id"
        :message="message"
        @tool-expand="handleToolExpand"
      />

      <!-- 流式状态指示器 -->
      <div v-if="loading || streamingStatus" class="flex justify-start">
        <div class="message-bubble message-ai">
          <div class="flex items-center space-x-2">
            <div class="text-lg">🤖</div>
            <div class="flex-1">
              <div class="loading-dots">{{ streamingStatus || '思考中' }}</div>
              <div class="flex space-x-1 mt-1">
                <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.1s;"></div>
                <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.2s;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="border-t bg-white p-4">
      <div class="flex space-x-2">
        <div class="flex-1">
          <input
            v-model="inputMessage"
            @keypress.enter="sendMessage"
            :disabled="loading"
            type="text"
            placeholder="输入消息... (支持图像检测、天气查询等)"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>

        <button
          @click="sendMessage"
          :disabled="loading || !inputMessage.trim()"
          class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          <span v-if="!loading">发送</span>
          <span v-else>发送中...</span>
        </button>

        <button
          @click="clearChat"
          class="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          title="清空对话"
        >
          🗑️
        </button>
      </div>

      <!-- 快捷操作 -->
      <div class="flex flex-wrap gap-2 mt-3">
        <button
          v-for="suggestion in suggestions"
          :key="suggestion.text"
          @click="inputMessage = suggestion.text"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
        >
          {{ suggestion.icon }} {{ suggestion.text }}
        </button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="bg-gray-100 px-4 py-2 text-xs text-gray-600 border-t">
      消息数: {{ messages.length }} |
      工具调用: {{ toolCallsCount }} |
      最后更新: {{ lastUpdateTime }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

// Props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  streamingStatus: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['send-message', 'clear-chat', 'node-highlight', 'node-status-change'])

// 响应式数据
const inputMessage = ref('')
const messagesContainer = ref(null)

// 快捷建议
const suggestions = ref([
  { icon: '🖼️', text: '分析这张图片：patrol_img/test.jpeg' },
  { icon: '🌤️', text: '北京天气怎么样？' },
  { icon: '💭', text: '总结一下我们的对话' },
  { icon: '🔍', text: '检测图片中的物体' }
])

// 计算属性
const toolCallsCount = computed(() => {
  return props.messages.filter(msg =>
    msg.type === 'tool_call' || msg.tool_calls?.length > 0
  ).length
})

const lastUpdateTime = computed(() => {
  if (props.messages.length === 0) return '无'
  const lastMessage = props.messages[props.messages.length - 1]
  return new Date(lastMessage.timestamp).toLocaleTimeString()
})

// 方法
const sendMessage = () => {
  if (!inputMessage.value.trim() || props.loading) return

  emit('send-message', inputMessage.value.trim())
  inputMessage.value = ''
}

const clearChat = () => {
  emit('clear-chat')
}

const handleToolExpand = (toolData) => {
  console.log('工具详情:', toolData)
}

// 新增：处理节点高亮
const handleNodeHighlight = (nodeId, duration = 3000) => {
  console.log('💬 ChatInterface 发射节点高亮事件:', { nodeId, duration })
  emit('node-highlight', { nodeId, duration })
}

// 新增：处理节点状态变化
const handleNodeStatusChange = (nodeId, status) => {
  emit('node-status-change', { nodeId, status })
}

// 新增：从消息中提取节点信息并触发高亮
const processMessageForNodeHighlight = (message) => {
  if (!message) return

  // 检查消息中是否包含节点信息
  if (message.node) {
    // 根据消息类型确定节点状态
    let status = 'default'

    if (message.type === 'system') {
      if (message.content.includes('🔄') || message.content.includes('执行')) {
        status = 'executing'
      } else if (message.content.includes('✅') || message.content.includes('完成')) {
        status = 'completed'
      } else if (message.content.includes('❌') || message.content.includes('错误')) {
        status = 'error'
      }
    }

    // 触发节点高亮
    handleNodeHighlight(message.node, 3000)

    // 触发节点状态变化
    if (status !== 'default') {
      handleNodeStatusChange(message.node, status)
    }
  }

  // 检查工具调用消息
  if (message.tool_calls && message.tool_calls.length > 0) {
    message.tool_calls.forEach(toolCall => {
      // 根据工具名称推断可能的节点
      const nodeId = inferNodeFromTool(toolCall.function?.name)
      if (nodeId) {
        handleNodeHighlight(nodeId, 2000)
        handleNodeStatusChange(nodeId, 'executing')
      }
    })
  }
}

// 新增：从工具名称推断节点ID
const inferNodeFromTool = (toolName) => {
  if (!toolName) return null

  const toolToNodeMap = {
    'yolo_detector': 'yolo_agent_tool',
    'weather_tool': 'weather_tool',
    'web_search': 'web_search_tool',
    'memory_search': 'memory_tool',
    'document_search': 'document_tool'
  }

  return toolToNodeMap[toolName] || null
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息变化，自动滚动到底部
watch(() => props.messages, () => {
  scrollToBottom()
}, { deep: true })

// 监听加载状态变化
watch(() => props.loading, () => {
  scrollToBottom()
})

// 监听流式状态变化
watch(() => props.streamingStatus, () => {
  scrollToBottom()
})

// 新增：监听消息变化，处理节点高亮
watch(() => props.messages, (newMessages, oldMessages) => {
  // 检查新增的消息
  if (newMessages.length > oldMessages.length) {
    const newMessage = newMessages[newMessages.length - 1]
    processMessageForNodeHighlight(newMessage)
  }
}, { deep: true })
</script>

<style scoped>
.chat-interface {
  height: 100%;
}

/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
