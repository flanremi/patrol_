<template>
  <div class="graph-visualization">
    <!-- 面包屑导航栏 -->
    <div v-if="navigationHistory.length > 0" class="mb-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2 text-sm flex-wrap">
          <button 
            @click="navigateToRoot"
            class="px-2 py-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
          >
            🏠 主图
          </button>
          <span v-for="(item, index) in navigationHistory" :key="index" class="flex items-center space-x-2">
            <span class="text-gray-400">›</span>
            <button 
              v-if="index < navigationHistory.length - 1"
              @click="navigateToLevel(index + 1)"
              class="px-2 py-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
            >
              {{ item.name }}
            </button>
            <span v-else class="px-2 py-1 text-blue-900 font-medium bg-blue-200 rounded">{{ item.name }}</span>
          </span>
        </div>
        
        <!-- 返回按钮 -->
        <button 
          @click="navigateBack"
          class="ml-4 px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex-shrink-0"
          title="返回上一级"
        >
          ← 返回上级
        </button>
      </div>
    </div>
    
    <!-- 统计信息栏 -->
    <div class="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div class="flex items-center justify-center space-x-4 text-sm">
        <div class="flex items-center space-x-2">
          <span class="text-gray-500">📊</span>
          <span class="font-medium text-gray-700">{{ currentGraphData.name || '主图' }}</span>
        </div>
        <span class="text-gray-300">|</span>
        <div class="flex items-center space-x-2">
          <span class="text-gray-500">🔵</span>
          <span class="text-gray-600">节点: <span class="font-medium text-gray-800">{{ getCurrentNodes().length }}</span></span>
        </div>
        <span class="text-gray-300">|</span>
        <div class="flex items-center space-x-2">
          <span class="text-gray-500">➡️</span>
          <span class="text-gray-600">边: <span class="font-medium text-gray-800">{{ getCurrentEdges().length }}</span></span>
        </div>
        <template v-if="currentGraphData.statistics && currentGraphData.statistics.subgraph_count > 0">
          <span class="text-gray-300">|</span>
          <div class="flex items-center space-x-2">
            <span class="text-gray-500">📦</span>
            <span class="text-gray-600">子图: <span class="font-medium text-gray-800">{{ currentGraphData.statistics.subgraph_count }}</span></span>
          </div>
        </template>
      </div>
    </div>
    
    <!-- 工具栏 -->
   <!-- 工具栏 -->
    <div class="flex flex-nowrap justify-start items-center gap-2 mb-4">
      <button
        @click="resetView"
        class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors whitespace-nowrap flex-shrink-0"
        title="重置视图到最佳缩放"
      >
        🔄 重置视图
      </button>

      <!-- 布局选择下拉菜单 -->
      <select
        v-model="currentLayout"
        @change="initializeNetwork"
        class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors border-0 focus:ring-2 focus:ring-blue-500 flex-shrink-0"
      >
        <option value="hierarchical">📊 层次布局</option>
        <option value="physics">🌐 物理布局</option>
        <option value="circular">⭕ 圆形布局</option>
      </select>

      <button
        @click="refreshGraph"
        class="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md transition-colors whitespace-nowrap flex-shrink-0"
        title="从服务器重新获取图结构"
      >
        🔄 刷新数据
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
      <div class="text-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
        <p class="text-sm text-gray-600">正在加载图结构...</p>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="flex items-center justify-center h-96 bg-red-50 rounded-lg">
      <div class="text-center">
        <div class="text-red-500 text-4xl mb-2">⚠️</div>
        <p class="text-sm text-red-600 mb-2">加载图结构失败</p>
        <p class="text-xs text-red-500">{{ error }}</p>
        <button
          @click="fetchGraphInfo"
          class="mt-2 px-3 py-1 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
      <div class="text-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
        <p class="text-sm text-gray-600">正在加载图结构...</p>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="flex items-center justify-center h-96 bg-red-50 rounded-lg">
      <div class="text-center">
        <div class="text-red-500 text-4xl mb-2">⚠️</div>
        <p class="text-sm text-red-600 mb-2">加载图结构失败</p>
        <p class="text-xs text-red-500">{{ error }}</p>
        <button 
          @click="fetchGraphInfo"
          class="mt-2 px-3 py-1 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
        >
          重试
        </button>
      </div>
    </div>

    <!-- 图形容器 -->
    <div 
      v-else
      ref="networkContainer" 
      class="graph-container"
      style="height: 400px; width: 100%;"
    ></div>

    <!-- 动态图例 -->
    <div class="mt-4 p-4 bg-gray-50 rounded-lg">
      <h4 class="text-sm font-medium text-gray-700 mb-2">图例</h4>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <!-- 动态显示所有节点类型 -->
        <div v-for="nodeType in Array.from(dynamicNodeTypes)" :key="nodeType" class="flex items-center space-x-2">
          <div 
            class="w-4 h-4 rounded" 
            :style="{ backgroundColor: (baseNodeColors[nodeType] || dynamicNodeColors[nodeType] || colorPalette[0]).background }"
          ></div>
          <span>{{ getNodeTypeDescription(nodeType, getNodeCategory(nodeType)) }}</span>
        </div>
        <!-- 边类型图例 -->
        <div class="flex items-center space-x-2">
          <div class="w-8 h-1 bg-gray-400"></div>
          <span>直接边</span>
        </div>
        <div class="flex items-center space-x-2">
          <div class="w-8 h-1 bg-red-400 border-dashed border-t-2 border-red-400"></div>
          <span>条件边</span>
        </div>
      </div>
    </div>

    <!-- 节点详情面板 -->
    <div v-if="selectedNode" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <div class="flex justify-between items-start">
        <h4 class="font-medium text-blue-900">{{ selectedNode.label || selectedNode.name }}</h4>
        <button 
          v-if="selectedNode.type === 'subgraph' || (selectedNode.nodes && selectedNode.nodes.length > 0)"
          @click="enterSubgraph(selectedNode)"
          class="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
        >
          进入 →
        </button>
      </div>
      <div class="mt-2 text-sm text-blue-800">
        <p><strong>类型:</strong> {{ getNodeTypeDescription(selectedNode.type, selectedNode.category) }}</p>
        <p><strong>ID:</strong> {{ selectedNode.id }}</p>
        <p v-if="selectedNode.level !== undefined"><strong>层级:</strong> {{ selectedNode.level }}</p>
        <p v-if="selectedNode.category"><strong>分类:</strong> {{ selectedNode.category }}</p>
        <p v-if="selectedNode.description"><strong>描述:</strong> {{ selectedNode.description }}</p>
        
        <!-- 子图统计信息 -->
        <div v-if="selectedNode.statistics" class="mt-2 p-2 bg-blue-100 rounded">
          <strong>子图统计:</strong>
          <ul class="list-disc list-inside ml-2">
            <li>节点数: {{ selectedNode.statistics.node_count }}</li>
            <li>边数: {{ selectedNode.statistics.edge_count }}</li>
            <li>子图数: {{ selectedNode.statistics.subgraph_count }}</li>
          </ul>
        </div>
        
        <!-- 工具列表 -->
        <div v-if="selectedNode.nodes && selectedNode.nodes.length > 0 && selectedNode.type === 'tool'" class="mt-2">
          <strong>包含工具:</strong>
          <ul class="list-disc list-inside ml-2">
            <li v-for="tool in selectedNode.nodes" :key="tool.id">{{ tool.name }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'

// Props - 现在支持可选的初始数据
const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  autoFetch: {
    type: Boolean,
    default: true  // 默认自动从API获取数据
  },
  apiBaseUrl: {
    type: String,
    default: 'http://localhost:8001'  // 默认API地址
  },
  // 新增：当前活跃的节点ID
  activeNodeId: {
    type: String,
    default: null
  },
  // 新增：节点执行状态
  nodeExecutionStatus: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['node-click', 'refresh-graph', 'graph-loaded', 'graph-error'])

// 响应式数据
const networkContainer = ref(null)
const selectedNode = ref(null)
const network = ref(null)
const currentLayout = ref('hierarchical')
const dynamicNodeTypes = ref(new Set())
const dynamicNodeColors = ref({})
const highlightedNodes = ref(new Set()) // 新增：高亮节点集合
const animationNodes = ref(new Set()) // 新增：动画节点集合

// API数据状态
const graphData = ref(null)  // 存储完整的图结构
const currentGraphData = ref({
  name: '主图',
  nodes: [],
  edges: [],
  statistics: {}
})
const navigationHistory = ref([])  // 导航历史栈
const canNavigateBack = ref(false)
const loading = ref(false)
const error = ref(null)

// 基础节点颜色配置
const baseNodeColors = {
  start: { background: '#10b981', border: '#059669' },      // 绿色
  end: { background: '#10b981', border: '#059669' },        // 绿色
}

// 预定义颜色调色板
const colorPalette = [
  { background: '#3b82f6', border: '#2563eb' },    // 蓝色
  { background: '#f59e0b', border: '#d97706' },     // 黄色  
  { background: '#8b5cf6', border: '#7c3aed' },     // 紫色
  { background: '#ef4444', border: '#dc2626' },     // 红色
  { background: '#06b6d4', border: '#0891b2' },     // 青色
  { background: '#84cc16', border: '#65a30d' },     // 绿黄色
  { background: '#f97316', border: '#ea580c' },     // 橙色
  { background: '#ec4899', border: '#db2777' },     // 粉色
  { background: '#6366f1', border: '#4f46e5' },     // 靛蓝色
  { background: '#14b8a6', border: '#0d9488' },     // 蓝绿色
  { background: '#a855f7', border: '#9333ea' },     // 紫罗兰色
  { background: '#22c55e', border: '#16a34a' },     // 绿色
]

// 动态分配颜色给节点类型
const assignNodeColor = (nodeType, category) => {
  // 特殊节点使用固定颜色
  if (baseNodeColors[nodeType]) {
    return baseNodeColors[nodeType]
  }
  
  // 如果已经分配过颜色，直接返回
  if (dynamicNodeColors.value[nodeType]) {
    return dynamicNodeColors.value[nodeType]
  }
  
  // 根据category优先分配特定颜色
  let colorIndex
  switch (category) {
    case 'tool':
      colorIndex = 1 // 黄色
      break
    case 'function':
      colorIndex = 0 // 蓝色
      break
    case 'memory':
      colorIndex = 2 // 紫色
      break
    case 'custom':
      colorIndex = 3 // 红色
      break
    default:
      // 为其他类型动态分配颜色
      colorIndex = Object.keys(dynamicNodeColors.value).length % colorPalette.length
  }
  
  const color = colorPalette[colorIndex] || colorPalette[0]
  dynamicNodeColors.value[nodeType] = color
  return color
}

// 方法
const getNodeTypeDescription = (type, category) => {
  const basicDescriptions = {
    start: '开始节点',
    end: '结束节点',
  }
  
  if (basicDescriptions[type]) {
    return basicDescriptions[type]
  }
  
  // 根据category生成描述
  const categoryDescriptions = {
    tool: '工具执行节点',
    function: '函数处理节点', 
    memory: '记忆管理节点',
    custom: '自定义节点',
    unknown: '未知节点'
  }
  
  const categoryDesc = categoryDescriptions[category] || '节点'
  return `${type} (${categoryDesc})`
}

// 获取节点分类的辅助方法
const getNodeCategory = (nodeType) => {
  const nodes = getCurrentNodes()
  const node = nodes.find(n => n.type === nodeType)
  return node?.category || 'unknown'
}

// 获取当前使用的节点数据
const getCurrentNodes = () => {
  return currentGraphData.value.nodes || []
}

const getCurrentEdges = () => {
  return currentGraphData.value.edges || []
}

// 导航到根图
const navigateToRoot = () => {
  if (!graphData.value) return
  
  navigationHistory.value = []
  currentGraphData.value = graphData.value.graph_structure
  canNavigateBack.value = false
  
  nextTick(() => {
    initializeNetwork()
  })
}

// 导航到指定层级
const navigateToLevel = (level) => {
  if (level === 0) {
    navigateToRoot()
    return
  }
  
  // 截断历史到指定层级
  navigationHistory.value = navigationHistory.value.slice(0, level)
  
  // 从根图开始，根据历史找到目标图
  let targetGraph = graphData.value.graph_structure
  for (const item of navigationHistory.value) {
    const node = targetGraph.nodes.find(n => n.id === item.id)
    if (node && node.nodes) {
      targetGraph = node
    }
  }
  
  currentGraphData.value = targetGraph
  canNavigateBack.value = navigationHistory.value.length > 0
  
  nextTick(() => {
    initializeNetwork()
  })
}

// 返回上一级
const navigateBack = () => {
  if (navigationHistory.value.length === 0) return
  
  navigationHistory.value.pop()
  navigateToLevel(navigationHistory.value.length)
}

// 进入子图
const enterSubgraph = (node) => {
  if (!node.nodes || node.nodes.length === 0) {
    console.log('该节点不是子图或没有子节点')
    return
  }
  
  // 添加到导航历史
  navigationHistory.value.push({
    id: node.id,
    name: node.name
  })
  
  // 更新当前图数据为子图数据
  currentGraphData.value = {
    name: node.name,
    nodes: node.nodes,
    edges: node.edges || [],
    statistics: node.statistics || {}
  }
  
  canNavigateBack.value = true
  
  // 重新初始化网络
  nextTick(() => {
    initializeNetwork()
  })
}

// API调用函数
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
    
    // 存储完整的图结构数据
    graphData.value = data
    
    // 初始化为根图
    if (data.graph_structure) {
      currentGraphData.value = data.graph_structure
      navigationHistory.value = []
      canNavigateBack.value = false
    }
    
    console.log('✅ 成功获取图结构信息:', graphData.value)
    emit('graph-loaded', graphData.value)
    
    // 重新初始化网络
    await nextTick()
    if (networkContainer.value) {
      initializeNetwork()
    }
    
  } catch (err) {
    console.error('❌ 获取图结构信息失败:', err)
    error.value = err.message
    emit('graph-error', err)
  } finally {
    loading.value = false
  }
}

const initializeNetwork = async () => {
  if (!networkContainer.value) return

  const currentNodes = getCurrentNodes()
  const currentEdges = getCurrentEdges()

  // 更新动态节点类型集合
  dynamicNodeTypes.value.clear()
  currentNodes.forEach(node => {
    dynamicNodeTypes.value.add(node.type)
  })

  // 准备节点数据
  const visNodes = currentNodes.map(node => {
    const isStartEnd = node.type === 'start' || node.type === 'end'
    const nodeColor = assignNodeColor(node.type, node.category)
    
    return {
      id: node.id,
      label: node.label || node.name,
      color: {
        background: nodeColor.background,
        border: nodeColor.border,
        highlight: {
          background: nodeColor.background,
          border: '#000000'
        },
        hover: {
          background: nodeColor.background,
          border: '#666666'
        }
      },
      font: {
        color: 'white',
        size: isStartEnd ? 12 : 14,
        face: 'Arial, sans-serif',
        strokeWidth: 2,
        strokeColor: nodeColor.border
      },
      shape: isStartEnd ? 'circle' : 'box',
      margin: isStartEnd ? 8 : 12,
      widthConstraint: isStartEnd ? {minimum: 60, maximum: 80} : {minimum: 100, maximum: 180},
      heightConstraint: isStartEnd ? {minimum: 60, maximum: 80} : {minimum: 40, maximum: 60},
      size: isStartEnd ? 35 : undefined,
      borderWidth: 2,
      borderWidthSelected: 3,
      // 添加节点的额外信息
      title: `<div style="padding: 8px;">
        <strong>${node.label || node.name}</strong><br/>
        类型: ${node.type}<br/>
        ${node.category ? '分类: ' + node.category + '<br/>' : ''}
        ${node.description ? '描述: ' + node.description + '<br/>' : ''}
        ${node.tools && node.tools.length > 0 ? '工具: ' + node.tools.join(', ') : ''}
      </div>`,
      // 存储原始节点数据用于详情显示
      originalData: node
    }
  })

  // 准备边数据
  const visEdges = currentEdges.map(edge => ({
    from: edge.from,
    to: edge.to,
    label: edge.label || '',
    arrows: {
      to: {
        enabled: true,
        scaleFactor: 1.2,
        type: 'arrow'
      }
    },
    color: {
      color: edge.type === 'conditional' ? '#ef4444' : '#4f46e5',
      highlight: edge.type === 'conditional' ? '#dc2626' : '#3730a3',
      hover: edge.type === 'conditional' ? '#f87171' : '#6366f1'
    },
    width: edge.type === 'conditional' ? 3 : 2,
    dashes: edge.type === 'conditional' ? [8, 4] : false,
    font: {
      size: 12,
      color: '#1f2937',
      background: 'rgba(255, 255, 255, 0.8)',
      strokeWidth: 0,
      align: 'middle'
    },
    smooth: {
      enabled: true,
      type: 'continuous',
      roundness: 0.3
    },
    physics: true
  }))

  // 网络配置
  const options = {
    layout: currentLayout.value === 'hierarchical' ? {
      hierarchical: {
        direction: 'UD',
        sortMethod: 'directed',
        levelSeparation: 120,
        nodeSpacing: 150,
        treeSpacing: 200,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true,
        shakeTowards: 'roots'
      }
    } : currentLayout.value === 'circular' ? {
      randomSeed: 2,
      improvedLayout: true,
      clusterThreshold: 150
    } : {
      randomSeed: 2,
      improvedLayout: true
    },
    physics: {
      enabled: currentLayout.value !== 'hierarchical',
      stabilization: {
        enabled: true,
        iterations: 200,
        updateInterval: 25,
        onlyDynamicEdges: false,
        fit: true
      },
      solver: 'repulsion',
      repulsion: {
        centralGravity: 0.3,
        springLength: 150,
        springConstant: 0.05,
        nodeDistance: 200,
        damping: 0.09
      }
    },
    interaction: {
      hover: true,
      hoverConnectedEdges: true,
      selectConnectedEdges: true,
      tooltipDelay: 300,
      zoomView: true,
      dragView: true
    },
    nodes: {
      borderWidth: 2,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.2)',
        size: 5,
        x: 2,
        y: 2
      },
      scaling: {
        min: 10,
        max: 30,
        label: {
          enabled: true,
          min: 12,
          max: 18,
          maxVisible: 30,
          drawThreshold: 5
        }
      }
    },
    edges: {
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.1)',
        size: 2,
        x: 1,
        y: 1
      },
      scaling: {
        min: 1,
        max: 5
      },
      selectionWidth: 2,
      hoverWidth: 0.5
    },
    configure: {
      enabled: false
    }
  }

  // 创建网络
  const {Network} = await import('vis-network')
  network.value = new Network(
      networkContainer.value,
      {nodes: visNodes, edges: visEdges},
      options
  )

  // 等待网络稳定后自动适配视图
  network.value.once('stabilizationIterationsDone', () => {
    network.value.fit({
      animation: {
        duration: 1000,
        easingFunction: 'easeInOutQuad'
      }
    })
  })

  // 事件监听 - 修改为进入子图逻辑
  network.value.on('click', (event) => {
    if (event.nodes.length > 0) {
      const nodeId = event.nodes[0]
      const currentNodes = getCurrentNodes()
      const node = currentNodes.find(n => n.id === nodeId)
      if (node) {
        selectedNode.value = node
        emit('node-click', node)
        
        // 如果是子图节点或工具节点（有子节点），点击进入
        if (node.type === 'subgraph' || (node.nodes && node.nodes.length > 0)) {
          console.log('🔍 进入子图:', node.name)
          enterSubgraph(node)
        }
      }
    } else {
      selectedNode.value = null
    }
  })

  network.value.on('hoverNode', () => {
    networkContainer.value.style.cursor = 'pointer'
  })

  network.value.on('blurNode', () => {
    networkContainer.value.style.cursor = 'default'
  })

  network.value.on('hoverEdge', () => {
    networkContainer.value.style.cursor = 'pointer'
  })

  network.value.on('blurEdge', () => {
    networkContainer.value.style.cursor = 'default'
  })

  // 双击节点时聚焦
  network.value.on('doubleClick', (event) => {
    if (event.nodes.length > 0) {
      network.value.focus(event.nodes[0], {
        scale: 1.5,
        animation: {
          duration: 800,
          easingFunction: 'easeInOutQuad'
        }
      })
    }
  })
}

const resetView = () => {
  if (network.value) {
    network.value.fit({
      animation: {
        duration: 800,
        easingFunction: 'easeInOutQuad'
      }
    })
  }
}

const toggleLayout = () => {
  const layouts = ['hierarchical', 'physics', 'circular']
  const currentIndex = layouts.indexOf(currentLayout.value)
  const nextIndex = (currentIndex + 1) % layouts.length
  currentLayout.value = layouts[nextIndex]
  initializeNetwork()
}

// 添加特定布局切换方法
const setLayout = (layoutType) => {
  currentLayout.value = layoutType
  initializeNetwork()
}

const refreshGraph = async () => {
  emit('refresh-graph')
  await fetchGraphInfo()
}

// 新增：触发节点点击事件
const triggerNodeClick = (nodeId) => {
  console.log('🖱️ 触发节点点击事件:', nodeId)
  
  // 获取节点数据
  const currentNodes = getCurrentNodes()
  const node = currentNodes.find(n => n.id === nodeId)
  
  if (node) {
    // 设置选中节点
    selectedNode.value = node
    
    // 发射点击事件
    emit('node-click', node)
    
    console.log('✅ 节点点击事件已触发:', node)
  } else {
    console.warn('⚠️ 未找到节点数据:', nodeId)
  }
}

// 新增：高亮节点方法 - 使用vis-network内置的选中效果
const highlightNode = (nodeId, duration = 3000) => {
  console.log('🎨 高亮节点方法被调用:', { nodeId, duration, networkExists: !!network.value })
  if (!network.value || !nodeId) {
    console.warn('⚠️ 无法高亮节点:', { nodeId, networkExists: !!network.value })
    return
  }
  
  highlightedNodes.value.add(nodeId)
  animationNodes.value.add(nodeId)
  
  console.log('✅ 节点已添加到高亮集合:', nodeId)
  
  // 使用vis-network内置的选中效果，与点击效果一致
  try {
    // 选中节点，这会触发与点击相同的视觉效果
    network.value.selectNodes([nodeId])
    
    // 触发点击事件，显示节点详情
    triggerNodeClick(nodeId)
    
    // 添加初始的选中脉冲效果
    setTimeout(() => {
      updateNodeHighlight(nodeId, true)
    }, 100) // 稍微延迟，让选中效果先显示
    
    console.log('🎯 节点已选中，效果与点击一致')
  } catch (error) {
    console.error('❌ 选中节点失败:', error)
    // 降级到自定义高亮
    updateNodeHighlight(nodeId, true)
  }
  
  // 自动取消高亮
  setTimeout(() => {
    console.log('⏰ 自动取消高亮:', nodeId)
    highlightedNodes.value.delete(nodeId)
    animationNodes.value.delete(nodeId)
    
    // 取消选中状态
    try {
      network.value.unselectAll()
    } catch (error) {
      console.error('❌ 取消选中失败:', error)
    }
    
    // 恢复节点样式
    updateNodeHighlight(nodeId, false)
  }, duration)
}

// 新增：更新节点高亮状态
const updateNodeHighlight = (nodeId, isHighlighted) => {
  if (!network.value) return
  
  // 获取原始节点数据
  const currentNodes = getCurrentNodes()
  const originalNode = currentNodes.find(n => n.id === nodeId)
  if (!originalNode) return
  
  const nodeColor = assignNodeColor(originalNode.type, originalNode.category)
  const isAnimated = animationNodes.value.has(nodeId)
  
  // 根据状态设置不同的颜色和样式
  let color, borderWidth, shadow
  
  if (isHighlighted) {
    if (isAnimated) {
      // 动画状态：增强的选中效果 + 波浪动画
      color = {
        background: nodeColor.background,
        border: '#3b82f6', // 蓝色边框，与选中效果一致
        highlight: {
          background: '#e0f2fe', // 浅蓝色背景
          border: '#0284c7'
        },
        hover: {
          background: '#e0f2fe',
          border: '#0284c7'
        }
      }
      borderWidth = 4 // 更粗的边框
      shadow = {
        enabled: true,
        color: 'rgba(59, 130, 246, 0.5)', // 蓝色阴影
        size: 12,
        x: 0,
        y: 0
      }
    } else {
      // 普通高亮状态 - 与vis-network默认选中效果一致
      color = {
        background: nodeColor.background,
        border: '#3b82f6', // 蓝色边框
        highlight: {
          background: '#e0f2fe', // 浅蓝色背景
          border: '#0284c7'
        },
        hover: {
          background: '#e0f2fe',
          border: '#0284c7'
        }
      }
      borderWidth = 3
      shadow = {
        enabled: true,
        color: 'rgba(59, 130, 246, 0.3)',
        size: 8,
        x: 0,
        y: 0
      }
    }
  } else {
    // 恢复正常状态
    color = {
      background: nodeColor.background,
      border: nodeColor.border,
      highlight: {
        background: nodeColor.background,
        border: '#000000'
      },
      hover: {
        background: nodeColor.background,
        border: '#666666'
      }
    }
    borderWidth = 2
    shadow = {
      enabled: true,
      color: 'rgba(0,0,0,0.2)',
      size: 5,
      x: 2,
      y: 2
    }
  }
  
  // 使用 vis-network 的正确方法更新节点
  try {
    // 方法1：直接更新节点数据
    const nodes = network.value.getNodes()
    const edges = network.value.getEdges()
    
    // 找到要更新的节点并修改其属性
    const updatedNodes = nodes.map(node => {
      if (node.id === nodeId) {
        return {
          ...node,
          color,
          borderWidth,
          shadow
        }
      }
      return node
    })
    
    // 重新设置数据
    network.value.setData({ nodes: updatedNodes, edges })
  } catch (error) {
    console.error('更新节点高亮失败:', error)
  }
}

// 新增：清除所有高亮
const clearAllHighlights = () => {
  highlightedNodes.value.clear()
  animationNodes.value.clear()
  
  if (!network.value) return
  
  const nodes = network.value.getNodes()
  nodes.forEach(node => {
    updateNodeHighlight(node.id, false)
  })
}

// 新增：根据执行状态更新节点
const updateNodeByExecutionStatus = (nodeId, status) => {
  if (!network.value || !nodeId) return
  
  const currentNodes = getCurrentNodes()
  const originalNode = currentNodes.find(n => n.id === nodeId)
  if (!originalNode) return
  
  const nodeColor = assignNodeColor(originalNode.type, originalNode.category)
  
  let color, borderWidth, shadow
  
  switch (status) {
    case 'executing':
      // 执行中：橙色
      color = {
        background: '#f97316',
        border: '#ea580c',
        highlight: {
          background: '#f97316',
          border: '#c2410c'
        },
        hover: {
          background: '#f97316',
          border: '#c2410c'
        }
      }
      borderWidth = 3
      shadow = {
        enabled: true,
        color: 'rgba(249, 115, 22, 0.5)',
        size: 12,
        x: 0,
        y: 0
      }
      break
      
    case 'completed':
      // 已完成：绿色
      color = {
        background: '#10b981',
        border: '#059669',
        highlight: {
          background: '#10b981',
          border: '#047857'
        },
        hover: {
          background: '#10b981',
          border: '#047857'
        }
      }
      borderWidth = 3
      shadow = {
        enabled: true,
        color: 'rgba(16, 185, 129, 0.5)',
        size: 12,
        x: 0,
        y: 0
      }
      break
      
    case 'error':
      // 错误：红色
      color = {
        background: '#ef4444',
        border: '#dc2626',
        highlight: {
          background: '#ef4444',
          border: '#b91c1c'
        },
        hover: {
          background: '#ef4444',
          border: '#b91c1c'
        }
      }
      borderWidth = 3
      shadow = {
        enabled: true,
        color: 'rgba(239, 68, 68, 0.5)',
        size: 12,
        x: 0,
        y: 0
      }
      break
      
    default:
      // 默认状态
      color = {
        background: nodeColor.background,
        border: nodeColor.border,
        highlight: {
          background: nodeColor.background,
          border: '#000000'
        },
        hover: {
          background: nodeColor.background,
          border: '#666666'
        }
      }
      borderWidth = 2
      shadow = {
        enabled: true,
        color: 'rgba(0,0,0,0.2)',
        size: 5,
        x: 2,
        y: 2
      }
  }
  
  // 使用 vis-network 的正确方法更新节点
  try {
    const nodes = network.value.getNodes()
    const edges = network.value.getEdges()
    
    // 找到要更新的节点并修改其属性
    const updatedNodes = nodes.map(node => {
      if (node.id === nodeId) {
        return {
          ...node,
          color,
          borderWidth,
          shadow
        }
      }
      return node
    })
    
    // 重新设置数据
    network.value.setData({ nodes: updatedNodes, edges })
  } catch (error) {
    console.error('更新节点状态失败:', error)
  }
}

// 生命周期
onMounted(async () => {
  await nextTick()
  
  // 如果启用自动获取，先从API获取数据
  if (props.autoFetch) {
    await fetchGraphInfo()
  } else {
    // 否则使用props数据初始化
    initializeNetwork()
  }
})

// 监听数据变化
watch(() => [props.nodes, props.edges], () => {
  if (network.value && !props.autoFetch) {
    initializeNetwork()
  }
}, { deep: true })

// 监听当前图数据变化
watch(() => currentGraphData.value, () => {
  if (network.value) {
    console.log('📊 当前图数据变化，重新渲染:', currentGraphData.value.name)
  }
}, { deep: true })

// 新增：监听活跃节点变化
watch(() => props.activeNodeId, (newNodeId, oldNodeId) => {
  console.log('🔄 活跃节点变化:', { newNodeId, oldNodeId })
  if (newNodeId && newNodeId !== oldNodeId) {
    console.log('✨ 开始高亮节点:', newNodeId)
    // 高亮新节点
    highlightNode(newNodeId, 3000)
    
    // 聚焦到节点
    if (network.value) {
      try {
        network.value.focus(newNodeId, {
          scale: 1.2,
          animation: {
            duration: 800,
            easingFunction: 'easeInOutQuad'
          }
        })
        console.log('🎯 节点聚焦成功:', newNodeId)
      } catch (error) {
        console.error('❌ 节点聚焦失败:', error)
      }
    }
  }
})

// 新增：监听节点执行状态变化
watch(() => props.nodeExecutionStatus, (newStatus, oldStatus) => {
  if (!network.value) return
  
  // 检查状态变化
  Object.keys(newStatus).forEach(nodeId => {
    const currentStatus = newStatus[nodeId]
    const previousStatus = oldStatus[nodeId]
    
    if (currentStatus !== previousStatus) {
      updateNodeByExecutionStatus(nodeId, currentStatus)
      
      // 如果是执行中状态，添加波浪动画
      if (currentStatus === 'executing') {
        animationNodes.value.add(nodeId)
        setTimeout(() => {
          animationNodes.value.delete(nodeId)
        }, 2000)
      }
    }
  })
  
  // 清理不再存在的节点状态
  Object.keys(oldStatus).forEach(nodeId => {
    if (!(nodeId in newStatus)) {
      updateNodeByExecutionStatus(nodeId, 'default')
    }
  })
}, { deep: true })
</script>

<style scoped>
.graph-visualization {
  @apply w-full;
}

.graph-container {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: #ffffff;
  position: relative;
}

/* 波浪动画效果 - 与选中效果一致的蓝色主题 */
@keyframes wave-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.6);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 0 15px rgba(59, 130, 246, 0.3);
    transform: scale(1.02);
  }
  100% {
    box-shadow: 0 0 0 30px rgba(59, 130, 246, 0);
    transform: scale(1);
  }
}

@keyframes ripple {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(2.4);
    opacity: 0;
  }
}

/* 节点高亮动画 - 与点击选中效果一致 */
.node-highlight {
  animation: wave-pulse 2s infinite;
}

/* 选中状态增强动画 */
.node-selected {
  animation: selected-pulse 1.5s ease-in-out;
}

@keyframes selected-pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    transform: scale(1.03);
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.2);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
}

/* 执行状态动画 */
.node-executing {
  animation: wave-pulse 1.5s infinite;
}

.node-completed {
  animation: none;
  transition: all 0.3s ease-in-out;
}

.node-error {
  animation: none;
  transition: all 0.3s ease-in-out;
}

/* 加载动画 */
.loading-dots {
  display: inline-block;
}

.loading-dots::after {
  content: '';
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% {
    content: '';
  }
  40% {
    content: '.';
  }
  60% {
    content: '..';
  }
  80%, 100% {
    content: '...';
  }
}

/* 工具提示动画 */
.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.3s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
}

/* 节点状态指示器 */
.status-indicator {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid white;
  animation: pulse 2s infinite;
}

.status-executing {
  background-color: #f97316;
}

.status-completed {
  background-color: #10b981;
}

.status-error {
  background-color: #ef4444;
}

@keyframes pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 10px rgba(0, 0, 0, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(0, 0, 0, 0);
  }
}
</style>
