<template>
  <div class="tool-result-container">
    <!-- 工具信息头部 -->
    <div v-if="toolInfo" class="tool-header mb-3 p-3 bg-gray-50 rounded border">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center space-x-2">
          <span class="text-lg">{{ getToolEmoji(toolName) }}</span>
          <span class="font-medium text-gray-800">{{ toolInfo.name }}</span>
        </div>
        <div class="text-xs text-gray-500">
          <span class="bg-gray-200 px-2 py-1 rounded">Level {{ toolInfo.level }}</span>
        </div>
      </div>
      
      <!-- 工具描述 -->
      <div class="text-sm text-gray-600 mb-2">
        {{ toolInfo.description }}
      </div>
      
      <!-- 工具路径信息 -->
      <div class="text-xs text-gray-400">
        <div class="flex items-center space-x-2">
          <span>📍 路径:</span>
          <code class="bg-gray-100 px-1 rounded">{{ toolInfo.node_path }}</code>
        </div>
        <div class="flex items-center space-x-2 mt-1">
          <span>🆔 ID:</span>
          <code class="bg-gray-100 px-1 rounded">{{ toolInfo.id }}</code>
        </div>
      </div>
    </div>

    <!-- YOLO检测结果 -->
    <div v-if="toolName === 'yolo_detect_tool'" class="yolo-result">
      <div v-if="parsedResult">
        <div class="flex items-center justify-between mb-2">
          <span class="font-medium text-emerald-800">🎯 检测结果</span>
          <div class="flex items-center space-x-2">
            <span class="text-xs text-emerald-600">
              状态: {{ parsedResult.status === 'success' ? '✅ 成功' : '❌ 失败' }}
            </span>
            <button 
              @click="toggleExpanded"
              class="text-xs text-emerald-600 hover:text-emerald-800"
            >
              {{ isExpanded ? '收起' : '详情' }}
            </button>
          </div>
        </div>
        
        <!-- 简要信息（默认显示） -->
        <div v-if="!isExpanded">
          <p class="text-sm text-emerald-700">
            {{ parsedResult.status === 'success' ? parsedResult.message : parsedResult.message }}
          </p>
          <div v-if="parsedResult.status === 'success' && parsedResult.count" class="text-xs text-emerald-600 mt-1">
            检测到 {{ parsedResult.count }} 个对象
          </div>
        </div>
        
        <!-- 详细信息（展开时显示） -->
        <div v-if="isExpanded">
          <div v-if="parsedResult.status === 'success'">
            <p class="text-sm mb-2">{{ parsedResult.message }}</p>
            
            <div v-if="parsedResult.detections && parsedResult.detections.length > 0">
              <div class="text-xs text-emerald-700 mb-2">
                检测到 {{ parsedResult.count }} 个对象:
              </div>
              
              <div class="space-y-1">
                <div 
                  v-for="(detection, index) in parsedResult.detections.slice(0, 5)" 
                  :key="index"
                  class="flex justify-between items-center text-xs bg-emerald-25 p-2 rounded"
                >
                  <div class="flex items-center space-x-2">
                    <span class="w-2 h-2 bg-emerald-400 rounded-full"></span>
                    <span class="font-medium">{{ detection.class_name }}</span>
                  </div>
                  <div class="text-emerald-600">
                    {{ (detection.confidence * 100).toFixed(1) }}%
                  </div>
                </div>
              </div>
              
              <div v-if="parsedResult.detections.length > 5" class="text-xs text-emerald-600 mt-1">
                ... 还有 {{ parsedResult.detections.length - 5 }} 个对象
              </div>
            </div>
            
            <div v-else class="text-sm text-emerald-600">
              未检测到任何对象
            </div>
          </div>
          
          <div v-else class="text-sm text-red-600">
            {{ parsedResult.message }}
          </div>
        </div>
      </div>
      
      <div v-else class="text-xs text-gray-600">
        {{ result }}
      </div>
    </div>

    <!-- 天气查询结果 -->
    <div v-else-if="toolName === 'city_weather'" class="weather-result">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center space-x-2">
          <span class="text-lg">🌤️</span>
          <span class="font-medium text-blue-800">天气信息</span>
        </div>
        <button 
          @click="toggleExpanded"
          class="text-xs text-blue-600 hover:text-blue-800"
        >
          {{ isExpanded ? '收起' : '详情' }}
        </button>
      </div>
      
      <!-- 简要信息（默认显示） -->
      <div v-if="!isExpanded" class="text-sm text-blue-700">
        {{ result.length > 50 ? result.substring(0, 50) + '...' : result }}
      </div>
      
      <!-- 详细信息（展开时显示） -->
      <div v-if="isExpanded" class="text-sm">
        {{ result }}
      </div>
    </div>

    <!-- 通用工具结果 -->
    <div v-else class="generic-result">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center space-x-2">
          <span class="text-lg">⚙️</span>
          <span class="font-medium text-gray-800">工具执行结果</span>
        </div>
        <button 
          @click="toggleExpanded"
          class="text-xs text-gray-600 hover:text-gray-800"
        >
          {{ isExpanded ? '收起' : '详情' }}
        </button>
      </div>
      
      <!-- 简要信息（默认显示） -->
      <div v-if="!isExpanded" class="text-sm text-gray-700">
        <div v-if="isJsonResult" class="json-result">
          <span class="text-xs text-gray-500">JSON数据 (点击详情查看)</span>
        </div>
        <div v-else class="text-result">
          {{ result.length > 50 ? result.substring(0, 50) + '...' : result }}
        </div>
      </div>
      
      <!-- 详细信息（展开时显示） -->
      <div v-if="isExpanded" class="text-sm">
        <div v-if="isJsonResult" class="json-result">
          <pre class="bg-gray-50 p-2 rounded text-xs overflow-x-auto">{{ formatJson(result) }}</pre>
        </div>
        <div v-else class="text-result">
          {{ result }}
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

// Props
const props = defineProps({
  result: {
    type: [String, Object, Array],
    required: true
  },
  toolName: {
    type: String,
    default: 'unknown'
  },
  autoFetch: {
    type: Boolean,
    default: true
  },
  apiBaseUrl: {
    type: String,
    default: 'http://localhost:8001'
  }
})

// 响应式数据
const isExpanded = ref(false)
const toolInfo = ref(null)
const loading = ref(false)
const error = ref(null)

// 计算属性
const parsedResult = computed(() => {
  if (typeof props.result === 'string') {
    try {
      return JSON.parse(props.result)
    } catch {
      return null
    }
  }
  return props.result
})

const isJsonResult = computed(() => {
  return typeof props.result === 'object' || 
    (typeof props.result === 'string' && props.result.startsWith('{'))
})


// 方法
const formatJson = (obj) => {
  try {
    if (typeof obj === 'string') {
      return JSON.stringify(JSON.parse(obj), null, 2)
    }
    return JSON.stringify(obj, null, 2)
  } catch {
    return obj
  }
}

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

// 获取工具图标
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

// 从API获取工具信息
const fetchToolInfo = async () => {
  if (!props.autoFetch || !props.toolName) return
  
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
    
    // 从 graph_info 的 tools 字段中查找当前工具的信息
    const tools = data.tools || []
    console.log('🔍 可用工具列表:', tools.map(t => t.name))
    console.log('🎯 查找工具:', props.toolName)
    
    const currentTool = tools.find(tool => tool.name === props.toolName)
    
    if (currentTool) {
      console.log('✅ 找到工具信息:', currentTool)
      toolInfo.value = {
        name: currentTool.name,
        description: currentTool.description,
        id: currentTool.id,
        node_path: currentTool.node_path,
        node_name: currentTool.node_name,
        level: currentTool.level
      }
    } else {
      console.log('❌ 未找到工具信息，工具名:', props.toolName)
    }
    
  } catch (err) {
    console.error('❌ 获取工具信息失败:', err)
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  if (props.autoFetch) {
    fetchToolInfo()
  }
})

// 监听工具名称变化
watch(() => props.toolName, () => {
  if (props.autoFetch) {
    fetchToolInfo()
  }
})
</script>

<style scoped>
.tool-result-container {
  @apply w-full;
}

.yolo-result {
  @apply bg-emerald-50 border-l-4 border-emerald-400 p-3;
}

.weather-result {
  @apply bg-blue-50 border-l-4 border-blue-400 p-3;
}

.generic-result {
  @apply bg-gray-50 border-l-4 border-gray-400 p-3;
}

.json-result pre {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.4;
  max-height: 200px;
}

/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 2px;
}
</style>
