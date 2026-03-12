<template>
  <div class="relative w-full h-full flex bg-slate-50">
    <!-- 画布容器（承载 VueFlow 与区域线框叠加层） -->
    <div ref="flowContainerRef"
         class="relative flex-1 bg-gray-200 overflow-hidden">
      <!-- 背景网格层（跟随视口移动） -->
      <div
        :style="backgroundGridStyle"
        class="absolute inset-0 pointer-events-none"
      ></div>

      <!-- Vue Flow 画布 -->
      <VueFlow
        v-model:edges="edges"
        v-model:nodes="nodes"
        :default-viewport="{ zoom: 1, x: 0, y: 0 }"
        :edges-updatable="!isLocked"
        :elements-selectable="!isLocked"
        :fit-view-on-init="true"
        :max-zoom="2"
        :min-zoom="0.2"
        :nodes-connectable="!isLocked"
        :nodes-draggable="!isLocked"
        :snap-grid="[15, 15]"
        :snap-to-grid="true"
        :auto-connect="false"
        class="absolute inset-0"
        style="background: transparent;"
        @nodes-initialized="onNodesInitialized"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
      >
        <!-- 自定义节点模板 - 根据类型动态渲染 -->
        <template #node-custom="{ data }">
          <!-- Start 节点 -->
          <StartNode
            v-if="data.type === 'start'"
            :execution-progress="getNodeProgress(data.id)"
            :execution-status="nodeExecutionStatus[data.id]"
            :is-highlighted="isNodeHighlighted(data.id)"
            :node-data="data"
          />
          <!-- End 节点 -->
          <EndNode
            v-else-if="data.type === 'end'"
            :execution-progress="getNodeProgress(data.id)"
            :execution-status="nodeExecutionStatus[data.id]"
            :is-highlighted="isNodeHighlighted(data.id)"
            :node-data="data"
          />
          <!-- Agent 节点 -->
          <AgentNode
            v-else-if="data.type === 'agent'"
            :execution-progress="getNodeProgress(data.id)"
            :execution-status="nodeExecutionStatus[data.id]"
            :is-highlighted="isNodeHighlighted(data.id)"
            :node-data="data"
          />
          <!-- SubAgent 节点 -->
          <SubAgentNode
            v-else-if="data.type === 'subagent'"
            :execution-progress="getNodeProgress(data.id)"
            :execution-status="nodeExecutionStatus[data.id]"
            :is-highlighted="isNodeHighlighted(data.id)"
            :node-data="data"
          />
          <!-- Tool 节点 -->
          <ToolNode
            v-else-if="data.type === 'tool' || data.type === 'tools'"
            :execution-progress="getNodeProgress(data.id)"
            :execution-status="nodeExecutionStatus[data.id]"
            :is-highlighted="isNodeHighlighted(data.id)"
            :node-data="data"
          />
          <!-- 默认节点（其他类型） -->
          <WorkflowNode
            v-else
            :execution-status="nodeExecutionStatus[data.id]"
            :node-data="data"
          />
        </template>

        <!-- 背景网格（禁用，使用 CSS 点阵） -->
        <Background
          :gap="20"
          :size="0"
          pattern-color="transparent"
          variant="dots"
        />

        <!-- 控制面板 -->
        <Controls
          :show-fit-view="false"
          :show-interactive="true"
          :show-zoom="false"
        />

        <!-- 小地图 -->
        <MiniMap
          v-if="showMinimap"
          :mask-color="'rgba(0, 0, 0, 0.05)'"
          :node-border-radius="8"
          :node-color="getNodeColor"
          pannable
          zoomable
        />
      </VueFlow>

      <!-- 区域线框覆盖层（随视图缩放/平移） -->
      <div v-if="showRegionFrames && regionFrames.length > 0"
           :style="overlayTransformStyle"
           class="pointer-events-none absolute inset-0 z-20 overflow-visible">
        <div v-for="frame in regionFrames"
             :key="frame.id"
             :style="{
               left: (frame.x - 8) + 'px',
               top: (frame.y - 8) + 'px',
               width: (frame.width + 16) + 'px',
               height: (frame.height + 16) + 'px',
               border: '2px dashed rgba(59,130,246,0.7)',
               backgroundColor: 'transparent',
             }"
             class="absolute rounded-md">
          <div class="absolute -top-7 left-0 text-xs font-medium text-blue-600 bg-white/80 px-1.5 py-0.5 rounded">
            阶段 {{frame.index + 1}} ({{frame.count}}个节点)
          </div>
        </div>
      </div>
    </div>

    <!-- 浮动工具栏 -->
    <WorkflowToolbar
      :is-locked="isLocked"
      :show-minimap="showMinimap"
      :zoom-level="viewport.zoom"
      @auto-layout="autoLayout"
      @fit-view="fitView"
      @reset-view="resetView"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @toggle-minimap="toggleMinimap"
      @toggle-lock="toggleLock"
    />

    <!-- 加载状态 -->
    <div v-if="loading"
         class="absolute inset-0 flex items-center justify-center bg-white/95 z-1000">
      <div class="text-center p-8">
        <div class="w-12 h-12 mx-auto mb-4 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin"></div>
        <p class="text-gray-600">加载图结构中...</p>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error"
         class="absolute inset-0 flex items-center justify-center bg-white/95 z-1000">
      <div class="text-center p-8">
        <span class="text-5xl mb-4 block">⚠️</span>
        <p class="text-red-600 font-medium mb-4">{{error}}</p>
        <button class="px-5 py-2 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-md cursor-pointer transition-colors duration-200"
                @click="retry">
          重试
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useVueFlow, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import dagre from 'dagre'
import WorkflowNode from './WorkflowNode.vue'
import StartNode from './StartNode.vue'
import EndNode from './EndNode.vue'
import AgentNode from './AgentNode.vue'
import SubAgentNode from './SubAgentNode.vue'
import ToolNode from './ToolNode.vue'
import WorkflowToolbar from './WorkflowToolbar.vue'
import { getNodeSize, useNodeControl } from '~/composables/useNodeControl'

const props = defineProps({
  graphData: {
    type: Object,
    default: () => ({ nodes: [], edges: [] }),
  },
  apiBaseUrl: {
    type: String,
    default: 'http://0.0.0.0:8001',
  },
  activeNodeId: {
    type: String,
    default: null,
  },
  nodeExecutionStatus: {
    type: Object,
    default: () => ({}),
  },
  // 布局配置
  layoutConfig: {
    type: Object,
    default: () => ({
      nodesep: 20,      // 节点间距（垂直）
      ranksep: 60,      // 层级间距（水平）
      marginx: 20,      // 画布左右边距
      marginy: 20,      // 画布上下边距
      maxRanks: 0,      // 最大列数，超过则换行（0 表示不换行）
      wrapGap: 100,      // 换行后的垂直间距
      layoutMaxWidth: 16000, // 布局最大宽度（固定值，确保不同屏幕布局一致）
      regionGapX: 20,    // 区域水平间距
      regionGapY: 20,    // 区域垂直间距
    }),
  },
})

const emit = defineEmits([
  'node-click',
  'edge-click',
  'graph-loaded',
  'graph-error',
  'refresh-graph',
])

// Vue Flow 实例
const {
  fitView: vueFlowFitView,
  zoomIn: vueFlowZoomIn,
  zoomOut: vueFlowZoomOut,
  viewport,
  setViewport,
} = useVueFlow()

// 节点控制 API
const nodeControl = useNodeControl()

// 响应式数据
const nodes = ref([])
const edges = ref([])
const loading = ref(false)
const error = ref(null)
const showMinimap = ref(true)
const selectedNode = ref(null)
const isLocked = ref(true)
// 区域线框相关
const flowContainerRef = ref(null)
const showRegionFrames = ref(true)
const regionFrames = ref([])

// 叠加层与画布的同步（根据当前 viewport 缩放/平移）
const overlayTransformStyle = computed(() => {
  const z = viewport.value?.zoom || 1
  const x = viewport.value?.x || 0
  const y = viewport.value?.y || 0
  // VueFlow 内部坐标到屏幕：先缩放再平移，这里用 CSS 反向抵消，使框与节点重合
  return {
    transform: `translate(${x}px, ${y}px) scale(${z})`,
    transformOrigin: 'top left',
  }
})

// 背景网格样式（跟随视口移动和缩放）
const backgroundGridStyle = computed(() => {
  const z = viewport.value?.zoom || 1
  const x = viewport.value?.x || 0
  const y = viewport.value?.y || 0
  const gridSize = 20 * z // 网格大小随缩放变化
  const dotSize = 1 // 圆点大小保持不变

  return {
    backgroundImage: `radial-gradient(circle, #cbd5e1 ${dotSize}px, transparent ${dotSize}px)`,
    backgroundSize: `${gridSize}px ${gridSize}px`,
    backgroundPosition: `${x}px ${y}px`,
  }
})

// 监听外部数据变化
watch(() => props.graphData, (newData, oldData) => {
  if (newData && (newData.nodes?.length > 0 || newData.edges?.length > 0)) {
    loadGraphData(newData)
  } else {
  }
}, { deep: true, immediate: true })

// 监听活跃节点变化
watch(() => props.activeNodeId, (nodeId) => {
  if (nodeId) {
    highlightNode(nodeId)
  }
})

// 递归展平嵌套节点结构
const flattenNodes = (nodes, parentId = null, level = 0) => {
  const flatNodes = []
  const flatEdges = []

  nodes.forEach(node => {
    // 添加当前节点
    const flatNode = {
      ...node,
      level,
      parentId,
      // 保留原始的子节点信息，但不在渲染时使用
      hasChildren: !!(node.nodes && node.nodes.length > 0),
    }
    flatNodes.push(flatNode)

    // 如果节点有子节点，递归展平
    if (node.nodes && node.nodes.length > 0) {
      const { nodes: childNodes, edges: childEdges } = flattenNodes(
        node.nodes,
        node.id,
        level + 1,
      )
      flatNodes.push(...childNodes)

      // 添加子图内部的边
      if (node.edges && node.edges.length > 0) {
        flatEdges.push(...node.edges)
      }

      // 添加子图递归产生的边
      if (childEdges && childEdges.length > 0) {
        flatEdges.push(...childEdges)
      }
    }
  })

  return { nodes: flatNodes, edges: flatEdges }
}

// 合并相同 ID 的节点（保留层级最低的，即最顶层的）
const mergeNodesById = (nodes) => {
  const nodeMap = new Map()

  nodes.forEach(node => {
    const existingNode = nodeMap.get(node.id)

    if (!existingNode) {
      // 第一次遇到该节点，直接添加
      nodeMap.set(node.id, node)
    } else {
      // 已存在相同 ID 的节点
      // 保留层级更低的节点（层级 0 优先于层级 1）
      if (node.level < existingNode.level) {
        nodeMap.set(node.id, node)
      } else {
      }
    }
  })

  return Array.from(nodeMap.values())
}

// 生成隐式边（父节点到其 __start__ 子节点的连接）
const generateImplicitEdges = (nodes) => {
  const implicitEdges = []

  // 为每个节点查找其可能的 __start__ 子节点
  nodes.forEach(parentNode => {
    const parentId = parentNode.id

    // 查找形如 "parentId.__start__" 的节点
    const startChildId = `${parentId}.__start__`
    const hasStartChild = nodes.some(n => n.id === startChildId)

    if (hasStartChild) {
      implicitEdges.push({
        from: parentId,
        to: startChildId,
        label: '进入',
        type: 'direct',
        implicit: true,  // 标记为隐式边
      })
    }

    // 同样查找 __end__ 子节点（从 __end__ 到父节点）
    const endChildId = `${parentId}.__end__`
    const hasEndChild = nodes.some(n => n.id === endChildId)

    if (hasEndChild) {
      implicitEdges.push({
        from: endChildId,
        to: parentId,
        label: '返回',
        type: 'direct',
        implicit: true,
      })
    }
  })

  return implicitEdges
}

// 判断节点是否应该被隐藏
const shouldHideNode = (node) => {
  const nodeId = node.id.toLowerCase()

  // 只保留顶层（level 0）的 __start__ 和 __end__ 节点
  if (node.type === 'start' || node.type === 'end') {
    // 只显示 level 0 的开始/结束节点，隐藏子图的开始/结束节点
    if (node.level === 0 && (node.id === '__start__' || node.id === '__end__')) {
      return false
    }
    // 隐藏其他所有的 start/end 节点（子图的）
    return true
  }

  // 隐藏以这些后缀结尾的节点
  const hiddenSuffixes = ['__start__', '__end__', 'agent', 'tools']

  return hiddenSuffixes.some(suffix => nodeId.endsWith(suffix.toLowerCase()))
}

// 重新路由边，跳过隐藏的节点并处理子流程
const rerouteEdges = (edges, nodes) => {
  const hiddenNodeIds = new Set(
    nodes.filter(shouldHideNode).map(n => n.id),
  )

  if (hiddenNodeIds.size === 0) {
    return edges
  }

  // 构建节点的出边映射
  const outgoingEdges = new Map()
  edges.forEach(edge => {
    const source = edge.from || edge.source
    if (!outgoingEdges.has(source)) {
      outgoingEdges.set(source, [])
    }
    outgoingEdges.get(source).push(edge)
  })

  // 检查节点是否有 __start__ 子节点（即有子流程）
  const hasSubflow = (nodeId) => {
    const startChildId = `${nodeId}.__start__`
    return nodes.some(n => n.id === startChildId)
  }

  // 查找节点的所有结束子节点（__end__ 以及子流程中的其他结束节点）
  const findEndNodes = (parentNodeId) => {
    const endNodes = []

    // 1. 查找直接的 __end__ 子节点
    const directEndId = `${parentNodeId}.__end__`
    if (nodes.some(n => n.id === directEndId)) {
      endNodes.push(directEndId)
    }

    // 2. 查找所有以 parentNodeId 开头的子节点，且它们没有出边（是结束节点）
    const subflowNodes = nodes.filter(n =>
      n.id.startsWith(`${parentNodeId}.`) &&
      !shouldHideNode(n),
    )

    subflowNodes.forEach(node => {
      const nodeOutEdges = outgoingEdges.get(node.id) || []

      // 过滤掉指向隐藏节点的边
      const visibleOutEdges = nodeOutEdges.filter(edge => {
        const target = edge.to || edge.target
        return !hiddenNodeIds.has(target) && !target.startsWith(`${parentNodeId}.`)
      })

      // 如果没有指向外部的可见出边，这是一个结束节点
      if (visibleOutEdges.length === 0 && nodeOutEdges.length > 0) {
        // 检查是否只连接到 __end__ 或父节点
        const onlyInternalEdges = nodeOutEdges.every(edge => {
          const target = edge.to || edge.target
          return target === directEndId || target === parentNodeId
        })

        if (onlyInternalEdges) {
          endNodes.push(node.id)
        }
      }
    })

    return endNodes
  }

  // 递归查找所有最终目标节点（跳过所有隐藏节点）
  const findFinalTargets = (nodeId, visited = new Set()) => {
    if (visited.has(nodeId)) {
      return [] // 防止循环
    }
    visited.add(nodeId)

    if (!hiddenNodeIds.has(nodeId)) {
      return [nodeId] // 找到非隐藏节点
    }

    // 如果是隐藏节点，查找它的所有下一个节点
    const nextEdges = outgoingEdges.get(nodeId) || []
    if (nextEdges.length === 0) {
      return [] // 没有后续节点
    }

    // 处理所有出边，递归查找最终目标
    const finalTargets = []
    nextEdges.forEach(nextEdge => {
      const nextTarget = nextEdge.to || nextEdge.target
      const targets = findFinalTargets(nextTarget, new Set(visited))
      finalTargets.push(...targets)
    })

    return finalTargets
  }

  // 重新路由边
  const reroutedEdges = []

  edges.forEach(edge => {
    const source = edge.from || edge.source
    const target = edge.to || edge.target

    // 如果源节点被隐藏，跳过这条边（会由前面的节点连接过来）
    if (hiddenNodeIds.has(source)) {
      return
    }

    // 如果目标节点被隐藏，查找所有最终目标
    if (hiddenNodeIds.has(target)) {
      const finalTargets = findFinalTargets(target)

      // 为每个最终目标创建一条边
      finalTargets.forEach(finalTarget => {
        if (finalTarget && finalTarget !== source) {
          reroutedEdges.push({
            ...edge,
            to: finalTarget,
            target: finalTarget,
            label: edge.label || '跳过隐藏节点',
            rerouted: true,
          })
        }
      })
    } else {
      // 目标节点不隐藏
      // 检查源节点是否有子流程
      if (hasSubflow(source)) {
        // 如果源节点有子流程，将边从源节点的所有结束节点连接到目标节点
        const endNodes = findEndNodes(source)

        if (endNodes.length > 0) {
          endNodes.forEach(endNode => {
            reroutedEdges.push({
              ...edge,
              from: endNode,
              source: endNode,
              to: target,
              target: target,
              label: edge.label || '子流程结束',
              subflowEnd: true,  // 标记为子流程结束边
            })
          })

          // 不保留原边（已被子流程结束节点的边替代）
        } else {
          // 没找到结束节点，保留原边
          reroutedEdges.push(edge)
        }
      } else {
        // 源节点没有子流程，保留原边
        reroutedEdges.push(edge)
      }
    }
  })

  return reroutedEdges
}

// 过滤主流程节点（只保留有边连接的节点）
const filterMainFlowNodes = (nodes, edges) => {
  // 先隐藏指定后缀的节点
  const visibleNodes = nodes.filter(node => !shouldHideNode(node))

  const hiddenCount = nodes.length - visibleNodes.length

  // 收集所有在边中出现的节点 ID
  const connectedNodeIds = new Set()

  edges.forEach(edge => {
    const sourceId = edge.from || edge.source
    const targetId = edge.to || edge.target
    if (sourceId) connectedNodeIds.add(sourceId)
    if (targetId) connectedNodeIds.add(targetId)
  })

  // 找到起始节点（start 类型或 __start__，但不以 __start__ 结尾）
  const startNodes = visibleNodes.filter(node =>
    (node.type === 'start' || node.id === '__start__' || node.id === 'start') &&
    !shouldHideNode(node),
  )

  // 如果有起始节点，即使它没有入边，也要保留
  startNodes.forEach(node => {
    connectedNodeIds.add(node.id)
  })

  // 找到结束节点（end 类型或 __end__）
  const endNodes = visibleNodes.filter(node =>
    (node.type === 'end' || node.id === '__end__' || node.id === 'end') &&
    !shouldHideNode(node),
  )

  // 如果有结束节点，即使它没有出边，也要保留
  endNodes.forEach(node => {
    connectedNodeIds.add(node.id)
  })

  // 过滤节点，只保留在主流程中的可见节点
  const mainFlowNodes = visibleNodes.filter(node => connectedNodeIds.has(node.id))

  const removedCount = visibleNodes.length - mainFlowNodes.length
  return mainFlowNodes
}

// 加载图数据
const loadGraphData = (data) => {
  try {
    // 1. 展平嵌套的节点结构
    const { nodes: flatNodes, edges: nestedEdges } = flattenNodes(data.nodes || [])
    // 2. 合并相同 ID 的节点
    const mergedNodes = mergeNodesById(flatNodes)

    // 3. 合并顶层边和嵌套边
    const allEdges = [
      ...(data.edges || []),
      ...nestedEdges,
    ]

    // 3.5. 生成隐式边（父节点到 __start__ 子节点的连接）
    const implicitEdges = generateImplicitEdges(mergedNodes)
    const allEdgesWithImplicit = [
      ...allEdges,
      ...implicitEdges,
    ]
    // 3.6. 重新路由边，跳过隐藏的节点
    const reroutedEdges = rerouteEdges(allEdgesWithImplicit, mergedNodes)

    // 4. 过滤主流程节点（只保留有边连接的节点，排除隐藏节点）
    const mainFlowNodes = filterMainFlowNodes(mergedNodes, reroutedEdges)

    // 5. 过滤边，只保留两端节点都存在的边
    const mainFlowNodeIds = new Set(mainFlowNodes.map(n => n.id))
    const validEdges = reroutedEdges.filter(edge => {
      const sourceId = edge.from || edge.source
      const targetId = edge.to || edge.target
      return mainFlowNodeIds.has(sourceId) && mainFlowNodeIds.has(targetId)
    })

    // 6. 转换节点数据
    const transformedNodes = mainFlowNodes.map(node => ({
      id: node.id,
      type: 'custom',
      data: {
        ...node,
        id: node.id,
        label: node.label || node.name || node.id,
        type: node.type || 'default',
        description: node.description,
        config: node.config,
        tools: node.tools,
        metadata: node.metadata,
        level: node.level,
        parentId: node.parentId,
        hasChildren: node.hasChildren,
        category: node.category,
      },
      position: node.position || { x: 0, y: 0 },
    }))

    // 7. 转换边数据
    const transformedEdges = validEdges.map((edge, index) => ({
      id: edge.id || `edge-${index}`,
      source: edge.from || edge.source,
      target: edge.to || edge.target,
      label: edge.label,
      type: getEdgeType(edge.type),
      animated: edge.animated || edge.implicit || false,  // 隐式边默认带动画
      markerEnd: 'arrowclosed',  // 有向箭头
      style: getEdgeStyle(edge.type, edge.implicit),
      labelStyle: {
        fontSize: 11,
        fill: edge.implicit ? '#3b82f6' : '#6b7280',  // 隐式边标签为蓝色
      },
      labelBgStyle: { fill: 'white', fillOpacity: 0.9 },
    }))

    // 先保存边数据的副本
    const edgesCopy = [...transformedEdges]

    nodes.value = transformedNodes
    edges.value = transformedEdges

    // 应用自动布局
    nextTick(() => {
      applyDagreLayout()
      // 确保在布局完成后再次检查并发出事件
      nextTick(() => {
        // 如果 edges 被意外清空，恢复它
        if (edges.value.length === 0 && edgesCopy.length > 0) {
          edges.value = edgesCopy
        }
        emit('graph-loaded', { nodes: nodes.value, edges: edges.value })
      })

      setTimeout((() => {
        applyDagreLayout()
      }))
    })
  } catch (err) {
    console.error('加载图数据失败:', err)
    error.value = `加载失败: ${err.message}`
    emit('graph-error', err)
  }
}


// 获取节点类型对应的尺寸
const getNodeSizeForType = (nodeType) => {
  return getNodeSize(nodeType)
}

// 获取节点进度
const getNodeProgress = (nodeId) => {
  const state = nodeControl.getNodeState(nodeId)
  return state.progress || 0
}

// 检查节点是否高亮
const isNodeHighlighted = (nodeId) => {
  return nodeControl.isNodeHighlighted(nodeId)
}

// 应用 Dagre 布局算法
const applyDagreLayout = () => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  // 使用配置的布局参数
  const config = props.layoutConfig
  dagreGraph.setGraph({
    rankdir: 'LR', // 从左到右布局
    nodesep: config.nodesep,   // 节点间距（可配置）
    ranksep: config.ranksep,   // 层级间距（可配置）
    marginx: config.marginx,   // 左右边距（可配置）
    marginy: config.marginy,    // 上下边距（可配置）
  })

  // 添加节点（使用动态尺寸）
  nodes.value.forEach(node => {
    const nodeSize = getNodeSizeForType(node.data?.type || 'default')
    dagreGraph.setNode(node.id, {
      width: nodeSize.width,
      height: nodeSize.height,
    })
  })

  // 添加边
  edges.value.forEach(edge => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  // 计算布局
  dagre.layout(dagreGraph)

  // 应用布局到节点（带换行支持）
  // 使用平均节点宽度计算换行阈值
  const avgNodeWidth = nodes.value.reduce((sum, node) => {
    const size = getNodeSizeForType(node.data?.type || 'default')
    return sum + size.width
  }, 0) / (nodes.value.length || 1)

  const columnUnitWidth = avgNodeWidth + config.ranksep
  const maxWidth = props.layoutConfig?.layoutMaxWidth || 1600
  const computedCapacity = Math.max(1, Math.floor((maxWidth - config.marginx * 2) / columnUnitWidth))

  const effectiveMaxRanks = (config.maxRanks && config.maxRanks > 0)
    ? Math.min(config.maxRanks, computedCapacity)
    : 0
  const maxRanks = effectiveMaxRanks
  const wrapGap = config.wrapGap || 100

  // 先获取所有节点的位置和尺寸
  const nodePositions = nodes.value.map(node => {
    const nodeWithPosition = dagreGraph.node(node.id)
    const nodeSize = getNodeSizeForType(node.data?.type || 'default')
    return {
      node,
      x: nodeWithPosition.x,
      y: nodeWithPosition.y,
      width: nodeSize.width,
      height: nodeSize.height,
    }
  })

  // 如果启用换行（maxRanks > 0）
  if (maxRanks > 0 && nodePositions.length > 0) {
    // 1. 按 x 坐标对节点进行分组（识别列）
    const xCoords = [...new Set(nodePositions.map(np => np.x))].sort((a, b) => a - b)

    // 为每个节点分配列索引（rank）
    nodePositions.forEach(np => {
      np.rank = xCoords.indexOf(np.x)
    })

    const maxRank = Math.max(...nodePositions.map(np => np.rank))

    if (maxRanks > 0 && maxRank >= maxRanks) {
      // 2. 按列分组节点
      const columnGroups = new Map()
      nodePositions.forEach(np => {
        if (!columnGroups.has(np.rank)) {
          columnGroups.set(np.rank, [])
        }
        columnGroups.get(np.rank).push(np)
      })

      // 3. 计算每列的高度范围
      const columnHeights = new Map()
      columnGroups.forEach((nodes, rank) => {
        const yValues = nodes.map(n => n.y)
        const minY = Math.min(...yValues)
        const maxY = Math.max(...yValues)
        columnHeights.set(rank, { minY, maxY, height: maxY - minY + 160 })
      })

      // 4. 计算每行的高度（每行包含 maxRanks 列）
      const totalRows = Math.ceil((maxRank + 1) / maxRanks)

      const rowHeights = []
      for (let row = 0; row < totalRows; row++) {
        const startRank = row * maxRanks
        const endRank = Math.min(startRank + maxRanks - 1, maxRank)

        // 找出这一行所有列的最大高度
        let maxHeight = 0
        let minY = Infinity
        let maxY = -Infinity

        for (let rank = startRank; rank <= endRank; rank++) {
          if (columnHeights.has(rank)) {
            const colHeight = columnHeights.get(rank)
            minY = Math.min(minY, colHeight.minY)
            maxY = Math.max(maxY, colHeight.maxY)
            maxHeight = Math.max(maxHeight, colHeight.height)
          }
        }

        rowHeights.push({
          row,
          startRank,
          endRank,
          minY,
          maxY,
          height: maxY - minY + 160,
        })
      }

      // 5. 计算每行的 Y 偏移量
      let cumulativeYOffset = 0
      const rowYOffsets = []

      rowHeights.forEach((rowInfo, index) => {
        rowYOffsets.push({
          row: index,
          yOffset: cumulativeYOffset,
          originalMinY: rowInfo.minY,
        })
        cumulativeYOffset += rowInfo.height + wrapGap
      })

      // 6. 计算每行的 X 偏移量（保留 dagre 计算的相对位置）
      // 关键：dagre 已经正确计算了节点间距，我们只需要将每行平移到正确位置
      const rowXOffsets = []
      for (let row = 0; row < totalRows; row++) {
        const startRank = row * maxRanks
        const endRank = Math.min(startRank + maxRanks - 1, maxRank)

        // 找出这一行第一列的原始 X 坐标
        const firstColumnNodes = columnGroups.get(startRank) || []
        const firstColumnX = firstColumnNodes.length > 0 ? firstColumnNodes[0].x : 0

        // 计算该行应该从哪里开始（左边距）
        const targetStartX = config.marginx

        // X 偏移量 = 目标位置 - 原始位置
        const xOffset = targetStartX - firstColumnX

        rowXOffsets.push({
          row,
          startRank,
          endRank,
          xOffset,
          originalFirstX: firstColumnX,
        })

      }

      // 7. 重新计算每个节点的位置（保留 dagre 的相对间距）
      nodePositions.forEach(np => {
        const currentRow = Math.floor(np.rank / maxRanks)
        const rowOffset = rowXOffsets[currentRow]
        const yOffset = rowYOffsets[currentRow]

        // X 坐标：使用 dagre 计算的原始 X + 行偏移
        // 这样可以保留 dagre 计算的精确间距
        np.newX = np.x + rowOffset.xOffset

        // Y 坐标：保持节点在列内的相对位置
        const relativeY = np.y - yOffset.originalMinY
        np.newY = yOffset.yOffset + relativeY + (np.height / 2)
      })
    } else {
      // 不需要换行，使用原始位置
      nodePositions.forEach(np => {
        np.newX = np.x
        np.newY = np.y
      })
    }
  } else {
    // 不启用换行，使用原始位置
    nodePositions.forEach(np => {
      np.newX = np.x
      np.newY = np.y
    })
  }

  // 应用最终位置
  nodes.value = nodePositions.map(np => ({
    ...np.node,
    position: {
      x: np.newX - (np.width / 2), // 使用实际节点宽度的一半居中对齐
      y: np.newY - (np.height / 2), // 使用实际节点高度的一半居中对齐
    },
  }))

  // 在初步布局完成后，基于已处理的图数据进行区域检测并重新组合
  detectAndRecomposeRegions()
}

// 自动布局
const autoLayout = () => {
  applyDagreLayout()
  nextTick(() => {
    vueFlowFitView({ padding: 0.05, duration: 400 })
  })
}

// 适应视图
const fitView = () => {
  vueFlowFitView({ padding: 0.05, duration: 400 })
}

// 重置视图
const resetView = () => {
  setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 400 })
}

// 缩放控制
const zoomIn = () => {
  vueFlowZoomIn({ duration: 200 })
}

const zoomOut = () => {
  vueFlowZoomOut({ duration: 200 })
}

// 切换小地图
const toggleMinimap = () => {
  showMinimap.value = !showMinimap.value
}

// 切换锁定状态
const toggleLock = () => {
  isLocked.value = !isLocked.value
}

// 获取边类型
const getEdgeType = (type) => {
  const typeMap = {
    conditional: 'smoothstep',  // 条件边使用平滑折线
    direct: 'default',          // 使用贝塞尔曲线
    default: 'default',          // 默认使用贝塞尔曲线
  }
  return typeMap[type] || 'default'
}

// 获取边样式
const getEdgeStyle = (type, isImplicit = false) => {
  if (isImplicit) {
    // 隐式边：使用虚线和特殊颜色
    return {
      stroke: '#3b82f6',  // 蓝色
      strokeWidth: 2,
      strokeDasharray: '3,3',  // 短虚线
    }
  }

  if (type === 'conditional') {
    return {
      stroke: '#f59e0b',
      strokeWidth: 2,
      strokeDasharray: '5,5',
    }
  }
  return {
    stroke: '#6b7280',
    strokeWidth: 2.5,  // 稍微加粗箭头
  }
}

// 获取节点颜色（用于小地图）
const getNodeColor = (node) => {
  const colorMap = {
    start: '#10b981',
    end: '#ef4444',
    chatbot: '#8b5cf6',
    tool: '#f59e0b',
    tools: '#f59e0b',
    summary: '#06b6d4',
    agent: '#ec4899',
    default: '#6b7280',
  }
  return colorMap[node.data?.type] || colorMap.default
}

// —— 区域检测与重排 ——
// 根据节点name中包含"智能体"的节点来划分阶段，一个智能体就是一个阶段
const detectAndRecomposeRegions = () => {
  if (!nodes.value || nodes.value.length === 0 || !edges.value) return

  // 构建度信息和邻接表
  const indegree = new Map()
  const outdegree = new Map()
  const idToNode = new Map(nodes.value.map(n => [n.id, n]))

  nodes.value.forEach(n => {
    indegree.set(n.id, 0)
    outdegree.set(n.id, 0)
  })
  edges.value.forEach(e => {
    const s = e.source
    const t = e.target
    if (idToNode.has(s) && idToNode.has(t)) {
      indegree.set(t, (indegree.get(t) || 0) + 1)
      outdegree.set(s, (outdegree.get(s) || 0) + 1)
    }
  })

  const adjacency = new Map()
  nodes.value.forEach(n => adjacency.set(n.id, []))
  edges.value.forEach(e => {
    if (adjacency.has(e.source)) adjacency.get(e.source).push(e.target)
  })

  // 检查节点name是否包含"智能体"
  const isAgentNode = (node) => {
    return node.data?.name && node.data.name.includes('智能体')
  }

  // 找到所有智能体节点
  const agentNodes = nodes.value.filter(isAgentNode)
  
  if (agentNodes.length === 0) {
    // 如果没有智能体节点，使用原来的逻辑
    return detectAndRecomposeRegionsOriginal()
  }

  // 拓扑排序
  const indegreeCopy = new Map(indegree)
  const queue = []
  nodes.value.forEach(n => {
    if ((indegreeCopy.get(n.id) || 0) === 0) queue.push(n.id)
  })

  const topo = []
  while (queue.length) {
    const u = queue.shift()
    topo.push(u)
    const outs = adjacency.get(u) || []
    outs.forEach(v => {
      if (!indegreeCopy.has(v)) return
      indegreeCopy.set(v, (indegreeCopy.get(v) || 0) - 1)
      if ((indegreeCopy.get(v) || 0) === 0) queue.push(v)
    })
  }

  if (topo.length === 0) return

  // 为每个智能体节点创建阶段
  const regions = []
  const processedNodes = new Set()

  // 按拓扑顺序处理节点
  topo.forEach(nodeId => {
    const node = idToNode.get(nodeId)
    if (!node || processedNodes.has(nodeId)) return

    // 如果是智能体节点，创建一个新阶段
    if (isAgentNode(node)) {
      const regionNodes = new Set([nodeId])
      processedNodes.add(nodeId)

      // 收集该智能体节点及其后续节点，直到遇到下一个智能体节点或结束
      const collectNodesForAgent = (currentNodeId) => {
        const outs = adjacency.get(currentNodeId) || []
        
        for (const nextNodeId of outs) {
          if (processedNodes.has(nextNodeId)) continue
          
          const nextNode = idToNode.get(nextNodeId)
          if (!nextNode) continue

          // 如果遇到下一个智能体节点，停止收集
          if (isAgentNode(nextNode)) {
            break
          }

          // 添加到当前阶段
          regionNodes.add(nextNodeId)
          processedNodes.add(nextNodeId)

          // 递归收集后续节点
          collectNodesForAgent(nextNodeId)
        }
      }

      // 收集该智能体的所有相关节点
      collectNodesForAgent(nodeId)
      
      // 将阶段添加到区域列表
      regions.push(Array.from(regionNodes))
    }
  })

  // 处理剩余的未处理节点（没有智能体的部分）
  const remainingNodes = topo.filter(id => !processedNodes.has(id))
  
  // 如果还有未处理的节点，尝试将它们合并到第一个智能体阶段中
  if (remainingNodes.length > 0 && regions.length > 0) {
    // 检查剩余节点是否都是start节点
    const remainingNodeTypes = remainingNodes.map(id => {
      const node = idToNode.get(id)
      return node?.data?.type || 'default'
    })
    
    const allStartNodes = remainingNodeTypes.every(type => type === 'start')
    
    if (allStartNodes && remainingNodes.length === 1) {
      // 如果只有一个start节点，将其合并到第一个智能体阶段中
      const firstRegion = regions[0]
      firstRegion.unshift(remainingNodes[0])
      processedNodes.add(remainingNodes[0])
    } else if (!allStartNodes || remainingNodes.length > 1) {
      // 如果有非start节点或多个节点，创建独立阶段
      regions.push(remainingNodes)
    }
  } else if (remainingNodes.length > 0 && regions.length === 0) {
    // 如果没有智能体节点，但有剩余节点，检查是否需要创建阶段
    const remainingNodeTypes = remainingNodes.map(id => {
      const node = idToNode.get(id)
      return node?.data?.type || 'default'
    })
    
    const hasNonStartNodes = remainingNodeTypes.some(type => type !== 'start')
    const hasMultipleNodes = remainingNodes.length > 1
    
    if (hasNonStartNodes || hasMultipleNodes) {
      regions.push(remainingNodes)
    }
  }

  if (regions.length <= 0) return

  // 应用区域布局
  applyRegionLayout(regions)
}

// 原来的区域检测逻辑（作为备用方案）
const detectAndRecomposeRegionsOriginal = () => {
  if (!nodes.value || nodes.value.length === 0 || !edges.value) return

  // 构建度信息
  const indegree = new Map()
  const outdegree = new Map()
  const idToNode = new Map(nodes.value.map(n => [n.id, n]))

  nodes.value.forEach(n => {
    indegree.set(n.id, 0)
    outdegree.set(n.id, 0)
  })
  edges.value.forEach(e => {
    const s = e.source
    const t = e.target
    if (idToNode.has(s) && idToNode.has(t)) {
      indegree.set(t, (indegree.get(t) || 0) + 1)
      outdegree.set(s, (outdegree.get(s) || 0) + 1)
    }
  })

  const isStartNode = (n) => (n.data?.type === 'start' || n.id === 'start' || (indegree.get(n.id) || 0) === 0)
  const isEndNode = (n) => (n.data?.type === 'end' || n.id === 'end')
  const isJoinNode = (n) => ((indegree.get(n.id) || 0) >= 2)

  // 拓扑排序（Kahn）按当前边关系
  const indegreeCopy = new Map(indegree)
  const queue = []
  nodes.value.forEach(n => {
    if ((indegreeCopy.get(n.id) || 0) === 0) queue.push(n.id)
  })

  const adjacency = new Map()
  nodes.value.forEach(n => adjacency.set(n.id, []))
  edges.value.forEach(e => {
    if (adjacency.has(e.source)) adjacency.get(e.source).push(e.target)
  })

  const topo = []
  while (queue.length) {
    const u = queue.shift()
    topo.push(u)
    const outs = adjacency.get(u) || []
    outs.forEach(v => {
      if (!indegreeCopy.has(v)) return
      indegreeCopy.set(v, (indegreeCopy.get(v) || 0) - 1)
      if ((indegreeCopy.get(v) || 0) === 0) queue.push(v)
    })
  }

  if (topo.length === 0) return

  // 为"分支-收束"区域识别做准备：
  // 1) topoIndex: 用于选择最早出现的共同可达节点
  // 2) 可达性计算：从每个子分支做 BFS，求交集得到共同可达集合
  const topoIndex = new Map()
  topo.forEach((nid, idx) => topoIndex.set(nid, idx))

  const bfsReachable = (startId) => {
    const visited = new Set([startId])
    const q = [startId]
    while (q.length) {
      const u = q.shift()
      const outs = adjacency.get(u) || []
      outs.forEach(v => {
        if (!visited.has(v)) {
          visited.add(v)
          q.push(v)
        }
      })
    }
    return visited
  }

  const findFirstCommonReachable = (childrenIds) => {
    if (!childrenIds || childrenIds.length === 0) return null
    // 先求第一个孩子的可达集
    let common = bfsReachable(childrenIds[0])
    // 依次与其他孩子的可达集求交
    for (let i = 1; i < childrenIds.length; i++) {
      const r = bfsReachable(childrenIds[i])
      common = new Set([...common].filter(x => r.has(x)))
      if (common.size === 0) break
    }
    if (common.size === 0) return null
    // 优先选择 indegree>=2 的节点作为"收束"候选
    const candidates = [...common].filter(id => (indegree.get(id) || 0) >= 2)
    const pool = candidates.length > 0 ? candidates : [...common]
    // 选择拓扑序最靠前的节点
    let best = null
    let bestIdx = Infinity
    pool.forEach(id => {
      const idx = topoIndex.has(id) ? topoIndex.get(id) : Infinity
      if (idx < bestIdx) {
        bestIdx = idx
        best = id
      }
    })
    return best
  }

  // 根据增强规则划分区域：
  // - 当遇到多出边的"分支"节点时，计算其所有直接子节点的共同可达首个节点，
  //   将当前区域延伸到该节点之前（不包含该节点）。
  // - 在受控"分支-收束"期间，忽略其他非目标的汇聚节点，不提前截断区域。
  const regions = []
  let currentRegionSet = new Set()
  let convergenceTarget = null
  const pushRegionIfAny = () => {
    if (currentRegionSet.size > 0) {
      regions.push(Array.from(currentRegionSet))
      currentRegionSet = new Set()
    }
  }

  topo.forEach(id => {
    const node = idToNode.get(id)
    if (!node) return

    // 新起点前收束已有区域（仅当当前没有进行"分支-收束"跟踪时）
    if (!convergenceTarget && isStartNode(node) && currentRegionSet.size > 0) {
      pushRegionIfAny()
    }

    // 如果到达当前跟踪的收束目标：在该收束节点之前结束区域
    if (convergenceTarget && id === convergenceTarget) {
      pushRegionIfAny()
      convergenceTarget = null
      // 继续处理该节点（可作为下一区域的起点）
    } else if (!convergenceTarget && (isJoinNode(node) || isEndNode(node))) {
      // 未处于受控"分支-收束"阶段时，普通的汇聚/结束节点作为边界（不包含该节点）
      pushRegionIfAny()
    }

    // 将当前节点纳入区域（作为新的区域的一部分或延续）
    currentRegionSet.add(id)

    // 若当前未跟踪收束目标，且该节点为分支（多出边），则计算并锁定收束点
    if (!convergenceTarget && (outdegree.get(id) || 0) >= 2) {
      const children = adjacency.get(id) || []
      const target = findFirstCommonReachable(children)
      if (target) {
        convergenceTarget = target
      }
    }
  })
  pushRegionIfAny()

  if (regions.length <= 0) return

  // 应用区域布局
  applyRegionLayout(regions)
}

// 应用区域布局的通用函数
const applyRegionLayout = (regions) => {
  // 计算每个区域的包围盒
  const GAP_X = props.layoutConfig?.regionGapX || 20 // 区域水平间距（可配置）
  const GAP_Y = props.layoutConfig?.regionGapY || 20 // 区域垂直间距（可配置）
  const BASE_MARGIN_X = (props.layoutConfig?.marginx || 20)
  const BASE_MARGIN_Y = (props.layoutConfig?.marginy || 20)

  // 构建节点映射
  const idToNode = new Map(nodes.value.map(n => [n.id, n]))

  // 计算每个区域的当前包围盒
  const regionBoxes = regions.map(regionIds => {
    const nodesInRegion = regionIds.map(id => idToNode.get(id)).filter(Boolean)

    // 计算区域内所有节点的实际边界（考虑每个节点的实际尺寸）
    let minX = Infinity
    let maxX = -Infinity
    let minY = Infinity
    let maxY = -Infinity

    nodesInRegion.forEach(n => {
      const nodeSize = getNodeSizeForType(n.data?.type || 'default')
      const x = n.position?.x || 0
      const y = n.position?.y || 0

      // 节点的左上角是 position，计算节点的实际边界
      minX = Math.min(minX, x)
      maxX = Math.max(maxX, x + nodeSize.width)
      minY = Math.min(minY, y)
      maxY = Math.max(maxY, y + nodeSize.height)
    })

    // 添加一些内边距，确保包围盒完全包含节点
    const padding = 8
    minX -= padding
    minY -= padding
    maxX += padding
    maxY += padding

    const width = maxX - minX
    const height = maxY - minY

    const box = {
      ids: regionIds,
      minX,
      maxX,
      minY,
      maxY,
      width,
      height,
    }
    return box
  })

  // 基于实际区域宽度的密铺算法（真正的瀑布流）
  // 每个区域放置在当前最低的位置，实现紧密排列
  // 使用固定最大宽度，确保不同屏幕上布局一致
  const layoutMaxWidth = props.layoutConfig?.layoutMaxWidth || 1600
  const availableWidth = layoutMaxWidth - BASE_MARGIN_X * 2

  // 存储每个区域的最终位置信息
  const placedRegions = []

  // 已放置区域的占用信息（用于检测可放置位置）
  // 每个元素：{ x, y, width, height, bottom, right }
  const occupiedRects = []

  const startX = BASE_MARGIN_X + (regionBoxes[0]?.minX ?? 0)
  const startY = BASE_MARGIN_Y + (regionBoxes[0]?.minY ?? 0)

  // 检查指定位置是否与已放置的区域重叠（考虑间距）
  const isOverlapping = (x, y, width, height) => {
    return occupiedRects.some(rect => {
      // 考虑间距的碰撞检测
      const hasHorizontalOverlap = x < rect.right + GAP_X && x + width + GAP_X > rect.x
      const hasVerticalOverlap = y < rect.bottom + GAP_Y && y + height + GAP_Y > rect.y
      return hasHorizontalOverlap && hasVerticalOverlap
    })
  }

  // 找到可以放置当前区域的最佳位置（最低、最左）
  const findBestPosition = (boxWidth, boxHeight) => {
    // 候选位置列表
    const candidates = []

    // 候选1：起始位置（如果没有占用）
    if (!isOverlapping(startX, startY, boxWidth, boxHeight)) {
      candidates.push({ x: startX, y: startY })
    }

    // 候选2：每个已放置区域的右侧
    occupiedRects.forEach(rect => {
      const x = rect.right + GAP_X
      const y = rect.y
      // 检查是否在容器宽度范围内
      if (x + boxWidth <= startX + availableWidth) {
        if (!isOverlapping(x, y, boxWidth, boxHeight)) {
          candidates.push({ x, y })
        }
      }
    })

    // 候选3：每个已放置区域的下方
    occupiedRects.forEach(rect => {
      const x = rect.x
      const y = rect.bottom + GAP_Y
      if (!isOverlapping(x, y, boxWidth, boxHeight)) {
        candidates.push({ x, y })
      }
    })

    // 候选4：尝试在第一行找空隙（从左到右扫描）
    if (occupiedRects.length > 0) {
      // 按X坐标排序已占用区域
      const sortedByX = [...occupiedRects].sort((a, b) => a.x - b.x)

      // 检查起始位置到第一个区域之间的空隙
      if (sortedByX[0].x - startX >= boxWidth + GAP_X) {
        const x = startX
        const y = startY
        if (!isOverlapping(x, y, boxWidth, boxHeight)) {
          candidates.push({ x, y })
        }
      }

      // 检查相邻区域之间的空隙
      for (let i = 0; i < sortedByX.length - 1; i++) {
        const current = sortedByX[i]
        const next = sortedByX[i + 1]
        const gapX = next.x - current.right

        if (gapX >= boxWidth + GAP_X * 2) {
          const x = current.right + GAP_X
          // 尝试多个Y位置
          const yPositions = [startY, current.y, next.y]
          for (const y of yPositions) {
            if (!isOverlapping(x, y, boxWidth, boxHeight)) {
              candidates.push({ x, y })
            }
          }
        }
      }
    }

    // 如果没有找到合适的位置，放在最底部
    if (candidates.length === 0) {
      const lowestBottom = occupiedRects.length > 0
        ? Math.max(...occupiedRects.map(r => r.bottom))
        : startY
      candidates.push({ x: startX, y: lowestBottom + GAP_Y })
    }

    // 选择最佳位置：优先选择Y最小的，Y相同则选择X最小的
    candidates.sort((a, b) => {
      if (Math.abs(a.y - b.y) < 1) {
        return a.x - b.x
      }
      return a.y - b.y
    })

    return candidates[0]
  }

  regionBoxes.forEach((box, index) => {
    // 找到最佳放置位置
    const position = findBestPosition(box.width, box.height)

    placedRegions.push({
      box,
      x: position.x,
      y: position.y,
    })

    // 记录占用区域
    occupiedRects.push({
      x: position.x,
      y: position.y,
      width: box.width,
      height: box.height,
      right: position.x + box.width,
      bottom: position.y + box.height,
    })
  })

  // 生成新坐标：保持区域内相对坐标
  const newPositions = new Map()
  placedRegions.forEach(({ box, x, y }) => {
    const offsetX = x - box.minX
    const offsetY = y - box.minY
    box.ids.forEach(id => {
      const n = idToNode.get(id)
      if (!n) return
      const oldX = n.position?.x || 0
      const oldY = n.position?.y || 0
      newPositions.set(id, { x: oldX + offsetX, y: oldY + offsetY })
    })
  })

  // 应用新的节点坐标
  nodes.value = nodes.value.map(n => {
    if (newPositions.has(n.id)) {
      const pos = newPositions.get(n.id)
      return {
        ...n,
        position: { x: pos.x, y: pos.y },
      }
    }
    return n
  })

  // 生成区域线框用于展示
  regionFrames.value = placedRegions.map((region, index) => ({
    id: `region-${index}`,
    index,
    x: region.x,
    y: region.y,
    width: region.box.width,
    height: region.box.height,
    count: region.box.ids.length,
  }))
}

// 节点点击事件
const onNodeClick = ({ node }) => {
  selectedNode.value = node
  emit('node-click', node)
}

// 边点击事件
const onEdgeClick = ({ edge }) => {
  emit('edge-click', edge)
}

// 节点初始化完成
const onNodesInitialized = () => {
  fitView()
}

// 高亮节点
const highlightNode = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    // 更新节点选中状态
    nodes.value = nodes.value.map(n => ({
      ...n,
      data: {
        ...n.data,
        selected: n.id === nodeId,
      },
    }))

    // 滚动到节点位置
    nextTick(() => {
      focusNode(nodeId)
    })
  }
}

// 聚焦到节点（移动画布并调整缩放）
const focusNode = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) {
    console.warn('节点不存在:', nodeId)
    return
  }

  // 计算节点中心点
  const nodeWidth = node.data?.width || 240
  const nodeHeight = node.data?.height || 120
  const nodeCenterX = node.position.x + nodeWidth / 2
  const nodeCenterY = node.position.y + nodeHeight / 2

  // 获取画布容器尺寸
  const container = flowContainerRef.value
  if (!container) {
    console.warn('画布容器未找到')
    return
  }

  const containerRect = container.getBoundingClientRect()
  const containerWidth = containerRect.width
  const containerHeight = containerRect.height

  // 计算合适的缩放级别（确保节点可见且有足够的边距）
  const targetZoom = 0.7 // 稍微放大一点，让节点更清晰

  // 计算节点在当前视口中的屏幕坐标
  const currentZoom = viewport.value?.zoom || 1
  const currentX = viewport.value?.x || 0
  const currentY = viewport.value?.y || 0

  // 节点中心点在屏幕上的位置
  const nodeScreenX = nodeCenterX * currentZoom + currentX
  const nodeScreenY = nodeCenterY * currentZoom + currentY

  // 屏幕中心点
  const screenCenterX = containerWidth / 2
  const screenCenterY = containerHeight / 2

  // 计算节点与屏幕中心的距离
  const distanceX = Math.abs(nodeScreenX - screenCenterX)
  const distanceY = Math.abs(nodeScreenY - screenCenterY)

  // 定义中心区域的阈值（容器尺寸的 20%）
  // 如果节点在这个范围内，就认为已经在视口中心，不需要移动
  const thresholdX = containerWidth * 0.5
  const thresholdY = containerHeight * 0.5

  // 检查节点是否已经在视口中心区域
  const isInCenterArea = distanceX < thresholdX && distanceY < thresholdY

  // 检查缩放级别是否接近目标值（允许 5% 的误差）
  const zoomDiff = Math.abs(currentZoom - targetZoom)
  const isZoomClose = zoomDiff < 0.05

  if (isInCenterArea && isZoomClose) {
    return
  }

  // 计算视口位置，使节点居中
  const x = containerWidth / 2 - nodeCenterX * targetZoom
  const y = containerHeight / 2 - nodeCenterY * targetZoom

  // 平滑移动到节点位置
  setViewport(
    { x, y, zoom: targetZoom },
    { duration: 600 }, // 600ms 的动画时间
  )
}

// 重试
const retry = () => {
  error.value = null
  emit('refresh-graph')
}

// 暴露方法给父组件
defineExpose({
  autoLayout,
  fitView,
  resetView,
  highlightNode,
  focusNode,
  toggleLock,
  // 暴露节点控制 API
  nodeControl,
})
</script>


<!-- Vue Flow 样式 -->
<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';
@import '@vue-flow/minimap/dist/style.css';


/* 过渡动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 自定义 Vue Flow 样式 */
.vue-flow__node {
  cursor: pointer;
}

.vue-flow__edge-path {
  stroke-width: 2;
}

.vue-flow__edge.selected .vue-flow__edge-path {
  stroke: #3b82f6 !important;
  stroke-width: 3;
}

.vue-flow__minimap {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.vue-flow__controls {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.vue-flow__controls-button {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  transition: all 0.2s ease;
}

.vue-flow__controls-button:hover {
  background: #f9fafb;
}

.vue-flow__controls-button svg {
  fill: #374151;
}
</style>


