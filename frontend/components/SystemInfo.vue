<template>
  <div class="system-info">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- 连接状态 -->
      <div class="info-card">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div :class="[
              'w-3 h-3 rounded-full',
              systemStatus.connected ? 'bg-green-500' : 'bg-red-500'
            ]"></div>
          </div>
          <div>
            <div class="text-sm font-medium text-gray-900">连接状态</div>
            <div :class="[
              'text-sm',
              systemStatus.connected ? 'text-green-600' : 'text-red-600'
            ]">
              {{ systemStatus.connected ? '已连接' : '未连接' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 节点统计 -->
      <div class="info-card">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <span class="text-blue-600 text-lg">🔗</span>
            </div>
          </div>
          <div>
            <div class="text-sm font-medium text-gray-900">活跃节点</div>
            <div class="text-sm text-gray-600">
              {{ systemStatus.nodes_count || 0 }} 个节点
            </div>
          </div>
        </div>
      </div>

      <!-- 工具统计 -->
      <div class="info-card">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
              <span class="text-yellow-600 text-lg">🔧</span>
            </div>
          </div>
          <div>
            <div class="text-sm font-medium text-gray-900">可用工具</div>
            <div class="text-sm text-gray-600">
              {{ systemStatus.tools_count || 0 }} 个工具
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详细信息 -->
    <div class="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 节点列表 -->
      <div class="detail-card">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-medium text-gray-900">节点列表</h3>
          <button
            v-if="props.autoFetch"
            @click="fetchGraphInfo"
            :disabled="loading"
            class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
          >
            {{ loading ? '刷新中...' : '🔄 刷新' }}
          </button>
        </div>
        <div class="space-y-2">
          <div
            v-for="node in nodeList"
            :key="node.id"
            class="flex items-center justify-between p-2 bg-gray-50 rounded"
          >
            <div class="flex items-center space-x-2">
              <span :class="getNodeIcon(node.type)">{{ getNodeEmoji(node.type) }}</span>
              <div>
                <div class="text-sm font-medium">{{ node.name }}</div>
                <div v-if="node.description" class="text-xs text-gray-500">{{ node.description }}</div>
              </div>
            </div>
            <div class="flex flex-col items-end space-y-1">
              <span :class="[
                'px-2 py-1 text-xs rounded-full',
                node.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
              ]">
                {{ node.active ? '活跃' : '空闲' }}
              </span>
              <span v-if="node.category" class="text-xs text-gray-400">{{ node.category }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 工具列表 -->
      <div class="detail-card">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-medium text-gray-900">工具列表</h3>
          <span v-if="error" class="text-xs text-red-500">获取失败</span>
        </div>
        <div class="space-y-2">
          <div
            v-for="tool in toolList"
            :key="tool.name"
            class="flex items-center justify-between p-2 bg-gray-50 rounded"
          >
            <div class="flex items-center space-x-2">
              <span class="text-lg">{{ getToolEmoji(tool.name) }}</span>
              <div>
                <div class="text-sm font-medium">{{ tool.display_name }}</div>
                <div class="text-xs text-gray-500">{{ tool.description }}</div>
              </div>
            </div>
            <span :class="[
              'px-2 py-1 text-xs rounded-full',
              tool.available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            ]">
              {{ tool.available ? '可用' : '不可用' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 最后更新时间 -->
    <div class="mt-4 text-xs text-gray-500 text-center">
      最后更新: {{ formatLastUpdate(systemStatus.last_update) }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

// Props
const props = defineProps({
  systemStatus: {
    type: Object,
    default: () => ({
      connected: false,
      nodes_count: 0,
      tools_count: 0,
      last_update: null
    })
  },
  autoFetch: {
    type: Boolean,
    default: true
  },
  apiBaseUrl: {
    type: String,
    default: 'http://0.0.0.0:8001'
  }
})

// 响应式数据
const graphData = ref({
  nodes: [],
  edges: [],
  tools: []
})
const loading = ref(false)
const error = ref(null)

// 计算属性
const nodeList = computed(() => {
  // 优先使用从API获取的节点数据
  if (graphData.value.nodes.length > 0) {
    return graphData.value.nodes.map(node => ({
      id: node.id,
      name: node.name || node.label,
      type: node.type,
      active: props.systemStatus.connected,
      category: node.category,
      description: node.description
    }))
  }

  // 后备方案：使用预定义的节点列表
  return [
    { id: 'start', name: 'START', type: 'start', active: props.systemStatus.connected },
    { id: 'memory', name: 'memory', type: 'memory', active: props.systemStatus.connected },
    { id: 'memory_tool', name: 'memory_tool', type: 'memory_tool', active: props.systemStatus.connected },
    { id: 'router', name: 'router', type: 'router', active: props.systemStatus.connected },
    { id: 'tool', name: 'tool', type: 'tool', active: false },
    { id: 'summary', name: 'summary', type: 'summary', active: false },
    { id: 'end', name: 'END', type: 'end', active: false }
  ]
})

const toolList = computed(() => {
  // 优先使用从API获取的工具数据
  if (graphData.value.tools.length > 0) {
    return graphData.value.tools.map(tool => ({
      name: tool.name,
      display_name: getToolDisplayName(tool.name),
      description: tool.description,
      available: props.systemStatus.connected
    }))
  }

  // 后备方案：使用预定义的工具列表
  return [
    {
      name: 'yolo_detect_tool',
      display_name: 'YOLO图像检测',
      description: '使用YOLO11检测图像中的对象',
      available: props.systemStatus.connected
    },
    {
      name: 'search_memory',
      display_name: '记忆搜索',
      description: '搜索历史记忆信息',
      available: props.systemStatus.connected
    },
    {
      name: 'store_memory',
      display_name: '记忆存储',
      description: '存储新的记忆信息',
      available: props.systemStatus.connected
    }
  ]
})

// 方法
const getNodeEmoji = (type) => {
  const emojis = {
    start: '🚀',
    end: '🏁',
    router: '🤖',
    memory: '🧠',
    memory_tool: '💾',
    tool: '🔧',
    summary: '📝'
  }
  return emojis[type] || '⚪'
}

const getNodeIcon = (type) => {
  const colors = {
    start: 'text-green-600',
    end: 'text-green-600',
    router: 'text-blue-600',
    memory: 'text-blue-600',
    memory_tool: 'text-indigo-600',
    tool: 'text-yellow-600',
    summary: 'text-blue-600'
  }
  return colors[type] || 'text-gray-600'
}

const getToolEmoji = (toolName) => {
  const emojis = {
    yolo_detect_tool: '🎯',
    city_weather: '🌤️',
    search_memory: '🔍',
    store_memory: '💾',
    calculator: '🧮'
  }
  return emojis[toolName] || '⚙️'
}

const getToolDisplayName = (toolName) => {
  const displayNames = {
    yolo_detect_tool: 'YOLO图像检测',
    city_weather: '天气查询',
    search_memory: '记忆搜索',
    store_memory: '记忆存储',
    calculator: '计算器'
  }
  return displayNames[toolName] || toolName
}

const formatLastUpdate = (timestamp) => {
  if (!timestamp) return '从未更新'

  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`

  return date.toLocaleString('zh-CN')
}

// 从API获取图信息
const fetchGraphInfo = async () => {
  if (!props.autoFetch) return

  loading.value = true
  error.value = null

  try {
    const response = await fetch(`${props.apiBaseUrl}/graph/info`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    if (data.error) {
      throw new Error(data.error)
    }

    // 更新图数据
    graphData.value = {
      nodes: data.nodes || [],
      edges: data.edges || [],
      tools: data.tools || []
    }

    console.log('✅ SystemInfo 成功获取图结构信息:', graphData.value)

  } catch (err) {
    console.error('❌ SystemInfo 获取图结构信息失败:', err)
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  if (props.autoFetch) {
    fetchGraphInfo()
  }
})

// 监听连接状态变化，自动刷新数据
watch(() => props.systemStatus.connected, (newConnected) => {
  if (newConnected && props.autoFetch) {
    fetchGraphInfo()
  }
})
</script>

<style scoped>
.system-info {
  @apply w-full;
}

.info-card {
  @apply bg-white p-4 rounded-lg border border-gray-200;
}

.detail-card {
  @apply bg-white p-4 rounded-lg border border-gray-200;
}
</style>
