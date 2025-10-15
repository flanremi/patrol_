<template>
  <div class="flex flex-col h-screen bg-slate-50 overflow-hidden">
    <!-- 头部 -->
    <header class="bg-white border-b border-slate-200 shadow-sm z-20">
      <div class="flex items-center justify-between max-w-full px-4 py-2">
        <div class="flex items-center gap-3">
          <!-- Logo -->
          <WorkflowLogo/>
        </div>

        <div class="flex items-center gap-2">
          <!-- 统计信息快捷显示 -->
          <div class="hidden lg:flex items-center gap-3 px-3 py-1 bg-slate-50 rounded border border-slate-200">
            <div class="flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
              <span class="text-xs text-slate-600">智能体节点 <span class="text-slate-900 font-medium">{{nodeCount}}</span></span>
            </div>
            <div class="w-px h-3 bg-slate-300"></div>
            <div class="flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full bg-blue-400"></div>
              <span class="text-xs text-slate-600">推理连接 <span class="text-slate-900 font-medium">{{edgeCount}}</span></span>
            </div>
            <div class="w-px h-3 bg-slate-300"></div>
            <div class="flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full"
                   :class="graphStatus === '正常' ? 'bg-green-500' : graphStatus === '加载中' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'"></div>
              <span class="text-xs text-slate-600">{{graphStatus}}</span>
            </div>
          </div>

          <WorkflowHeaderButton
            @click="showStatsDrawer = true"
            title="统计信息"
            class="lg:hidden"
          >
            <ChartBarIcon class="w-4 h-4"/>
          </WorkflowHeaderButton>

          <WorkflowHeaderButton
            @click="navigateToHome"
            title="返回首页"
          >
            <HomeIcon class="w-4 h-4"/>
          </WorkflowHeaderButton>

          <WorkflowHeaderButton
            @click="refreshGraph"
            :disabled="loading"
            :loading="loading"
            title="刷新图结构"
          >
            <ArrowPathIcon class="w-4 h-4"
                           :class="loading ? 'animate-spin' : ''"/>
          </WorkflowHeaderButton>
        </div>
      </div>
    </header>

    <!-- 主工作区 - 分为左右两栏 -->
    <main class="flex-1 overflow-hidden flex relative">
      <!-- 左侧聊天界面 (动态宽度) -->
      <div
        class="border-r border-slate-200 bg-white shadow-lg z-20  transition-all duration-700 ease-in-out relative"
        :class="showWorkflow ? 'w-1/3' : 'w-full'"
      >
        <ModernChat :api-base-url="apiBaseUrl"/>

        <!-- 工作流面板切换按钮 - 右侧中央 -->
        <button
          @click="toggleWorkflow"
          class="absolute top-1/2 -translate-y-1/2 z-30 w-6 h-6 rounded-full p-1  hover:shadow-xl transition-all duration-200 flex items-center justify-center group border border-slate-200 "
          :class="{
            '-right-3 bg-white': showWorkflow,
            'right-1 bg-blue-500 text-white': !showWorkflow
          }"
          :title="showWorkflow ? '隐藏工作流' : '显示工作流'"
        >
          <ChevronRightIcon
            v-if="showWorkflow"
            class="w-4 h-4  group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all"
          />
          <ChevronLeftIcon
            v-else
            class="w-4 h-4  group-hover:text-blue-500 group-hover:-translate-x-0.5 transition-all"
          />
        </button>
      </div>

      <!-- 右侧工作流画布 (始终渲染，通过样式控制显示) -->
      <div
        class="overflow-hidden relative transition-all duration-700 ease-in-out"
        :class="showWorkflow ? 'flex-1 opacity-100' : 'w-0 opacity-0 pointer-events-none'"
      >
        <WorkflowCanvas
          ref="canvasRef"
          :graph-data="graphData"
          :api-base-url="apiBaseUrl"
          :active-node-id="activeNodeId"
          :node-execution-status="nodeExecutionStatus"
          :layout-config="layoutConfig"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @graph-loaded="handleGraphLoaded"
          @graph-error="handleGraphError"
        />

        <!-- 节点详情抽屉 -->
        <NodeDetailDrawer
          :selected-node="selectedNode"
          @close="selectedNode = null"
        />

        <!-- 遮罩层 -->
        <transition name="fade">
          <div
            v-if="showStatsDrawer"
            @click="showStatsDrawer = false"
            class="lg:hidden absolute inset-0 bg-black/20 z-40"
          ></div>
        </transition>
      </div>
    </main>
  </div>
</template>

<script setup>
// 页面元信息
useHead({
  title: '工作流可视化 - LangGraph',
  meta: [
    { name: 'description', content: '类似 ComfyUI 的 LangGraph 工作流可视化引擎' },
  ],
})

// 导入组件
import NodeDetailDrawer from '~/components/workflow/NodeDetailDrawer.vue'
import WorkflowLogo from '~/components/workflow/WorkflowLogo.vue'
import ModernChat from '~/components/ModernChat.vue'
import { ArrowPathIcon, ChartBarIcon, ChevronLeftIcon, ChevronRightIcon, HomeIcon } from '@heroicons/vue/24/outline'
import { ChatStoreKey, useChatStore } from '~/composables/useChatStore'

// 配置
const apiBaseUrl = 'http://localhost:8001'

// 创建聊天存储并提供给子组件
const chatStore = useChatStore()
provide(ChatStoreKey, chatStore)


// 布局配置（可调整以压缩间距）
const layoutConfig = ref({
  nodesep: 20,      // 节点间距（垂直），默认 20
  ranksep: 60,      // 层级间距（水平），默认 60
  marginx: 20,      // 画布左右边距，默认 20
  marginy: 20,      // 画布上下边距，默认 20
  maxRanks: 0,      // 最大列数，超过则换行（0 表示不换行），默认 8
  wrapGap: 100,      // 换行后的垂直间距，默认 100
  layoutMaxWidth: 2000,
  regionGapX: 100,
  regionGapY: 100,
})

// 响应式数据
const graphData = ref({
  nodes: [],
  edges: [],
})
const loading = ref(false)
const graphStatus = ref('未加载')
const selectedNode = ref(null)
const activeNodeId = ref(null)
const nodeExecutionStatus = ref({})
const lastUpdateTime = ref('--')
const connectionStatus = ref('disconnected')
const showStatsDrawer = ref(false)
const showWorkflow = ref(false) // 控制工作流画布的显示

// 画布引用
const canvasRef = ref(null)

// 节点和边的计数（从 Canvas 组件获取实际渲染的数量）
const nodeCount = ref(0)
const edgeCount = ref(0)

// 方法
const navigateToHome = () => {
  navigateTo('/')
}

const toggleWorkflow = () => {
  showWorkflow.value = !showWorkflow.value

  // 如果展开工作流，延迟后执行 fitView
  if (showWorkflow.value) {
    setTimeout(() => {
      if (canvasRef.value && canvasRef.value.fitView) {
        canvasRef.value.fitView()
      }
    }, 700) // 等待 700ms 动画完成
  }
}

const refreshGraph = async () => {
  loading.value = true
  graphStatus.value = '加载中'

  try {
    // 参照 GraphVisualization.vue 的方式，直接调用后端接口
    const response = await fetch(`${apiBaseUrl}/graph/info`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    if (data.error) {
      throw new Error(data.error)
    }

    // GraphVisualization 返回的数据结构包含 graph_structure
    if (data.graph_structure) {
      graphData.value = {
        nodes: data.graph_structure.nodes || [],
        edges: data.graph_structure.edges || [],
      }
    } else if (data.nodes && data.edges) {
      // 兼容直接返回 nodes 和 edges 的格式
      graphData.value = {
        nodes: data.nodes,
        edges: data.edges,
      }
    } else {
      throw new Error('无效的图数据格式')
    }

    graphStatus.value = '正常'
    connectionStatus.value = 'connected'
    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
  } catch (error) {
    console.error('❌ 刷新图结构失败:', error)
    graphStatus.value = '错误'
    connectionStatus.value = 'disconnected'
    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')

    // 不使用默认数据，显示错误状态
    graphData.value = {
      nodes: [],
      edges: [],
    }
  } finally {
    loading.value = false
  }
}

const handleNodeClick = (node) => {
  selectedNode.value = node
  activeNodeId.value = node.id

  // 3秒后清除高亮
  setTimeout(() => {
    if (activeNodeId.value === node.id) {
      activeNodeId.value = null
    }
  }, 3000)
}

const handleEdgeClick = (edge) => {
}

const handleGraphLoaded = (data) => {
  graphStatus.value = '正常'
  connectionStatus.value = 'connected'
  // 更新实际渲染的节点和边数量
  if (data && data.nodes && data.edges) {
    nodeCount.value = data.nodes.length
    edgeCount.value = data.edges.length
  }
}

const handleGraphError = (error) => {
  graphStatus.value = '错误'
  connectionStatus.value = 'disconnected'
  nodeCount.value = 0
  edgeCount.value = 0
}

// 处理节点高亮（从聊天组件触发）
const handleNodeHighlight = ({ nodeId, duration = 3000 }) => {
  // 使用 WorkflowCanvas 的 nodeControl API
  if (canvasRef.value && canvasRef.value.nodeControl) {
    canvasRef.value.nodeControl.highlightNode(nodeId)

    // 自动移动画布到该节点并调整缩放
    nextTick(() => {
      if (canvasRef.value && canvasRef.value.focusNode) {
        canvasRef.value.focusNode(nodeId)
      }
    })
  } else {
    console.warn('⚠️ WorkflowCanvas ref 或 nodeControl 未就绪')
  }

  // 保留旧的逻辑作为备用
  activeNodeId.value = nodeId
}

// 处理节点取消高亮（从聊天组件触发）
const handleNodeUnhighlight = ({ nodeId }) => {
  // 使用 WorkflowCanvas 的 nodeControl API
  if (canvasRef.value && canvasRef.value.nodeControl) {
    canvasRef.value.nodeControl.unhighlightNode(nodeId)
  }

  // 清除旧的逻辑
  if (activeNodeId.value === nodeId) {
    activeNodeId.value = null
  }
}

// 处理节点状态变化（从聊天组件触发）
const handleNodeStatusChange = ({ nodeId, status }) => {
  // 使用 WorkflowCanvas 的 nodeControl API
  if (canvasRef.value && canvasRef.value.nodeControl) {
    if (status === 'default') {
      // 重置节点状态
      canvasRef.value.nodeControl.setNodeStatus(nodeId, null)
      canvasRef.value.nodeControl.unhighlightNode(nodeId)
    } else if (status === 'executing') {
      // 开始执行
      canvasRef.value.nodeControl.startNodeExecution(nodeId)
    } else if (status === 'completed') {
      // 执行完成 - 停止高亮
      canvasRef.value.nodeControl.completeNodeExecution(nodeId)
      // completeNodeExecution 内部会调用 unhighlightNode，但我们再次确保
      canvasRef.value.nodeControl.unhighlightNode(nodeId)
    } else if (status === 'error') {
      // 执行失败 - 停止高亮
      canvasRef.value.nodeControl.failNodeExecution(nodeId, '执行失败')
      // failNodeExecution 内部会调用 unhighlightNode，但我们再次确保
      canvasRef.value.nodeControl.unhighlightNode(nodeId)
    }
  } else {
    console.warn('⚠️ WorkflowCanvas ref 或 nodeControl 未就绪')
  }

  // 保留旧的逻辑作为备用
  if (status === 'default') {
    delete nodeExecutionStatus.value[nodeId]
  } else {
    nodeExecutionStatus.value[nodeId] = status
  }

  if (status === 'executing') {
    activeNodeId.value = nodeId
  }

  if (status === 'completed' || status === 'error') {
    // 立即清除活跃状态
    if (activeNodeId.value === nodeId) {
      activeNodeId.value = null
    }
  }
}
// 处理聊天开始（显示工作流画布）
const handleChatStart = async () => {
  showWorkflow.value = true

  // 等待动画完成后，自动 fitView
  await nextTick()
  setTimeout(() => {
    if (canvasRef.value && canvasRef.value.fitView) {
      canvasRef.value.fitView()
    }
  }, 700) // 等待 700ms 动画完成
}

// 注册聊天事件处理
chatStore.onNodeHighlight(handleNodeHighlight)
chatStore.onNodeUnhighlight(handleNodeUnhighlight)
chatStore.onNodeStatusChange(handleNodeStatusChange)
chatStore.onChatStart(handleChatStart)


// 初始化
onMounted(async () => {
  await refreshGraph()
})
</script>

