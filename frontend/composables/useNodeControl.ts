/**
 * 节点控制 API
 * 提供统一的节点控制接口，用于管理节点的执行状态、高亮、进度等
 */

import { reactive } from 'vue'

export interface NodeExecutionState {
  status: 'pending' | 'executing' | 'completed' | 'error' | null
  progress: number // 0-100
  startTime?: number
  endTime?: number
  error?: string
  output?: any
}

export interface NodeHighlightState {
  isHighlighted: boolean
  highlightColor?: string
}

export interface NodeControlAPI {
  // 执行状态管理
  setNodeStatus: (nodeId: string, status: NodeExecutionState['status']) => void
  setNodeProgress: (nodeId: string, progress: number) => void
  setNodeError: (nodeId: string, error: string) => void
  setNodeOutput: (nodeId: string, output: any) => void
  getNodeState: (nodeId: string) => NodeExecutionState

  // 高亮控制
  highlightNode: (nodeId: string, color?: string) => void
  unhighlightNode: (nodeId: string) => void
  isNodeHighlighted: (nodeId: string) => boolean

  // 批量操作
  resetAllNodes: () => void
  highlightPath: (nodeIds: string[]) => void
  unhighlightAll: () => void

  // 执行控制
  startNodeExecution: (nodeId: string) => void
  completeNodeExecution: (nodeId: string, output?: any) => void
  failNodeExecution: (nodeId: string, error: string) => void

  // 状态查询
  getExecutingNodes: () => string[]
  getCompletedNodes: () => string[]
  getErrorNodes: () => string[]
}

export function useNodeControl(): NodeControlAPI {
  // 节点执行状态存储
  const nodeStates = reactive<Record<string, NodeExecutionState>>({})

  // 节点高亮状态存储
  const nodeHighlights = reactive<Record<string, NodeHighlightState>>({})

  // 设置节点状态
  const setNodeStatus = (nodeId: string, status: NodeExecutionState['status']) => {
    if (!nodeStates[nodeId]) {
      nodeStates[nodeId] = {
        status: null,
        progress: 0,
      }
    }
    nodeStates[nodeId].status = status

    // 自动设置时间戳
    if (status === 'executing') {
      nodeStates[nodeId].startTime = Date.now()
      nodeStates[nodeId].progress = 0
    } else if (status === 'completed' || status === 'error') {
      nodeStates[nodeId].endTime = Date.now()
      nodeStates[nodeId].progress = 100
    }
  }

  // 设置节点进度
  const setNodeProgress = (nodeId: string, progress: number) => {
    if (!nodeStates[nodeId]) {
      nodeStates[nodeId] = {
        status: null,
        progress: 0,
      }
    }
    nodeStates[nodeId].progress = Math.max(0, Math.min(100, progress))
  }

  // 设置节点错误
  const setNodeError = (nodeId: string, error: string) => {
    if (!nodeStates[nodeId]) {
      nodeStates[nodeId] = {
        status: null,
        progress: 0,
      }
    }
    nodeStates[nodeId].error = error
    nodeStates[nodeId].status = 'error'
  }

  // 设置节点输出
  const setNodeOutput = (nodeId: string, output: any) => {
    if (!nodeStates[nodeId]) {
      nodeStates[nodeId] = {
        status: null,
        progress: 0,
      }
    }
    nodeStates[nodeId].output = output
  }

  // 获取节点状态
  const getNodeState = (nodeId: string): NodeExecutionState => {
    return nodeStates[nodeId] || {
      status: null,
      progress: 0,
    }
  }

  // 高亮节点
  const highlightNode = (nodeId: string, color?: string) => {
    nodeHighlights[nodeId] = {
      isHighlighted: true,
      highlightColor: color,
    }
  }

  // 取消高亮节点
  const unhighlightNode = (nodeId: string) => {
    if (nodeHighlights[nodeId]) {
      setTimeout(() => {
        nodeHighlights[nodeId].isHighlighted = false
      }, 2000)
    }
  }

  // 检查节点是否高亮
  const isNodeHighlighted = (nodeId: string): boolean => {
    return nodeHighlights[nodeId]?.isHighlighted || false
  }

  // 重置所有节点
  const resetAllNodes = () => {
    Object.keys(nodeStates).forEach(nodeId => {
      nodeStates[nodeId] = {
        status: null,
        progress: 0,
      }
    })
  }

  // 高亮路径
  const highlightPath = (nodeIds: string[]) => {
    nodeIds.forEach(nodeId => highlightNode(nodeId))
  }

  // 取消所有高亮
  const unhighlightAll = () => {
    Object.keys(nodeHighlights).forEach(nodeId => {
      nodeHighlights[nodeId].isHighlighted = false
    })
  }

  // 开始节点执行
  const startNodeExecution = (nodeId: string) => {
    setNodeStatus(nodeId, 'executing')
    highlightNode(nodeId)
  }

  // 完成节点执行
  const completeNodeExecution = (nodeId: string, output?: any) => {
    setNodeStatus(nodeId, 'completed')
    if (output !== undefined) {
      setNodeOutput(nodeId, output)
    }
    unhighlightNode(nodeId)
  }

  // 节点执行失败
  const failNodeExecution = (nodeId: string, error: string) => {
    setNodeError(nodeId, error)
    unhighlightNode(nodeId)
  }

  // 获取正在执行的节点
  const getExecutingNodes = (): string[] => {
    return Object.keys(nodeStates).filter(
      nodeId => nodeStates[nodeId].status === 'executing',
    )
  }

  // 获取已完成的节点
  const getCompletedNodes = (): string[] => {
    return Object.keys(nodeStates).filter(
      nodeId => nodeStates[nodeId].status === 'completed',
    )
  }

  // 获取错误节点
  const getErrorNodes = (): string[] => {
    return Object.keys(nodeStates).filter(
      nodeId => nodeStates[nodeId].status === 'error',
    )
  }

  return {
    // 状态管理
    setNodeStatus,
    setNodeProgress,
    setNodeError,
    setNodeOutput,
    getNodeState,

    // 高亮控制
    highlightNode,
    unhighlightNode,
    isNodeHighlighted,

    // 批量操作
    resetAllNodes,
    highlightPath,
    unhighlightAll,

    // 执行控制
    startNodeExecution,
    completeNodeExecution,
    failNodeExecution,

    // 状态查询
    getExecutingNodes,
    getCompletedNodes,
    getErrorNodes,
  }
}

// 导出节点大小配置
export const NODE_SIZES = {
  small: { width: 200, height: 100 },
  medium: { width: 250, height: 120 },
  large: { width: 280, height: 160 },
  xlarge: { width: 320, height: 200 },
}

// 节点类型到大小的映射
export const NODE_TYPE_SIZES: Record<string, { width: number; height: number }> = {
  start: { width: 80, height: 90 }, // 更小的圆形节点（64px圆 + 底部标签空间）
  end: { width: 120, height: 120 },   // 圆形节点，需要额外空间容纳底部标签
  agent: { width: 300, height: 300 },
  subagent: { width: 280, height: 65 },
  tool: { width: 230, height: 65 },
  chatbot: NODE_SIZES.medium,
  summary: NODE_SIZES.medium,
  router: NODE_SIZES.small,
  condition: NODE_SIZES.small,
  default: { width: 240, height: 65 },
}

// 获取节点尺寸
export function getNodeSize(nodeType: string): { width: number; height: number } {
  return NODE_TYPE_SIZES[nodeType] || NODE_TYPE_SIZES.default
}

