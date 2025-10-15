/**
 * Chat Store Composable
 * 管理聊天状态和消息，可通过 provide/inject 在组件间共享
 */

import { reactive, ref } from 'vue'

export interface ChatMessage {
  id: number | string
  type: 'user' | 'ai' | 'system' | 'tool_call'
  content: string
  timestamp: string
  error?: boolean
  node?: string
  node_path?: string
  metadata?: any
}

export interface ChatStoreAPI {
  // 消息相关
  messages: ReturnType<typeof ref<ChatMessage[]>>
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  getNodeMessages: (nodeId: string) => ChatMessage[]

  // 状态相关
  loading: ReturnType<typeof ref<boolean>>
  streamingStatus: ReturnType<typeof ref<string>>

  // 节点相关事件
  onNodeHighlight: (callback: (data: { nodeId: string; duration?: number }) => void) => void
  onNodeUnhighlight: (callback: (data: { nodeId: string }) => void) => void
  onNodeStatusChange: (callback: (data: { nodeId: string; status: string }) => void) => void
  emitNodeHighlight: (nodeId: string, duration?: number) => void
  emitNodeUnhighlight: (nodeId: string) => void
  emitNodeStatusChange: (nodeId: string, status: string) => void

  // 聊天状态事件
  onChatStart: (callback: () => void) => void
  emitChatStart: () => void
}

export function useChatStore(): ChatStoreAPI {
  // 消息列表
  const messages = ref<ChatMessage[]>([])

  // 加载状态
  const loading = ref(false)

  // 流式状态
  const streamingStatus = ref('')

  // 事件回调存储
  const eventCallbacks = reactive({
    nodeHighlight: [] as Array<(data: { nodeId: string; duration?: number }) => void>,
    nodeUnhighlight: [] as Array<(data: { nodeId: string }) => void>,
    nodeStatusChange: [] as Array<(data: { nodeId: string; status: string }) => void>,
    chatStart: [] as Array<() => void>,
  })

  /**
   * 添加消息
   */
  const addMessage = (message: ChatMessage) => {
    messages.value.push({
      ...message,
      timestamp: message.timestamp || new Date().toISOString(),
    })
  }

  /**
   * 清空消息
   */
  const clearMessages = () => {
    messages.value = []
  }

  /**
   * 获取与特定节点相关的消息
   * 通过匹配 node 字段或 path 字段中包含的节点名称
   */
  const getNodeMessages = (nodeId: string): ChatMessage[] => {
    if (!nodeId) return []

    return messages.value.filter(msg => {
      // 直接匹配 node 字段
      if (msg.node === nodeId) return true

      // 匹配 path 中包含的节点
      // path 格式: "内容创建智能体 -> 知识匹配子图"
      // nodeId 格式: "内容创建智能体.知识匹配子图" 或单个节点名称
      if (msg.node_path) {
        return nodeId == convertPathToNodeId(msg.node_path, msg)
      }

      return false
    })
  }

  /**
   * 注册节点高亮回调
   */
  const onNodeHighlight = (callback: (data: { nodeId: string; duration?: number }) => void) => {
    eventCallbacks.nodeHighlight.push(callback)
  }

  /**
   * 注册节点取消高亮回调
   */
  const onNodeUnhighlight = (callback: (data: { nodeId: string }) => void) => {
    eventCallbacks.nodeUnhighlight.push(callback)
  }

  /**
   * 注册节点状态变化回调
   */
  const onNodeStatusChange = (callback: (data: { nodeId: string; status: string }) => void) => {
    eventCallbacks.nodeStatusChange.push(callback)
  }

  /**
   * 触发节点高亮事件
   */
  const emitNodeHighlight = (nodeId: string, duration = 3000) => {
    eventCallbacks.nodeHighlight.forEach(cb => cb({ nodeId, duration }))
  }

  /**
   * 触发节点取消高亮事件
   */
  const emitNodeUnhighlight = (nodeId: string) => {
    eventCallbacks.nodeUnhighlight.forEach(cb => cb({ nodeId }))
  }

  /**
   * 触发节点状态变化事件
   */
  const emitNodeStatusChange = (nodeId: string, status: string) => {
    eventCallbacks.nodeStatusChange.forEach(cb => cb({ nodeId, status }))
  }

  /**
   * 注册聊天开始回调
   */
  const onChatStart = (callback: () => void) => {
    eventCallbacks.chatStart.push(callback)
  }

  /**
   * 触发聊天开始事件
   */
  const emitChatStart = () => {
    eventCallbacks.chatStart.forEach(cb => cb())
  }

  return {
    // 消息
    messages,
    addMessage,
    clearMessages,
    getNodeMessages,

    // 状态
    loading,
    streamingStatus,

    // 事件
    onNodeHighlight,
    onNodeUnhighlight,
    onNodeStatusChange,
    emitNodeHighlight,
    emitNodeUnhighlight,
    emitNodeStatusChange,
    onChatStart,
    emitChatStart,
  }
}

// 用于 provide/inject 的 key
export const ChatStoreKey = Symbol('ChatStore')

export // 将 node_path 转换为节点 ID
// 例如: "内容创建智能体 -> 知识匹配子图" => "内容创建智能体.知识匹配子图"
// 如果消息中包含 tool_calls，则将末尾的"节点"替换为"工具"
const convertPathToNodeId = (node_path: string, messageData: any = null) => {
  if (!node_path) return null

  let nodePath = node_path.replace(/\s*->\s*/g, '.')

  // 检查是否有工具调用，如果有则替换末尾的"节点"为"工具"
  if (messageData && messageData.tool_calls && messageData.tool_calls.length > 0) {
    nodePath = nodePath.replace(/\.([^.]*节点)$/, (match, nodeName) => {
      return '.' + nodeName.replace('节点', '工具')
    })
  }

  return nodePath
}
