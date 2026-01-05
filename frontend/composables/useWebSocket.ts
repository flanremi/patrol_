/**
 * WebSocket 连接管理 Composable
 * 管理与后端的 WebSocket 通信
 */

import { ref, onUnmounted } from 'vue'

export interface WSMessage {
  type: 'system' | 'chat' | 'tool'
  action: string
  data?: Record<string, any>
  timestamp?: string
  message_id?: string
}

export interface WebSocketOptions {
  url: string
  autoReconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(options: WebSocketOptions) {
  const {
    url,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  // 状态
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const connectionId = ref<string | null>(null)
  const lastError = ref<string | null>(null)
  const reconnectAttempts = ref(0)

  // WebSocket 实例
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 事件回调
  const callbacks = {
    onMessage: [] as Array<(message: WSMessage) => void>,
    onConnect: [] as Array<() => void>,
    onDisconnect: [] as Array<() => void>,
    onError: [] as Array<(error: string) => void>,
  }

  /**
   * 连接 WebSocket
   */
  const connect = () => {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
      console.log('WebSocket 已连接或正在连接中')
      return
    }

    isConnecting.value = true
    lastError.value = null

    try {
      ws = new WebSocket(url)

      ws.onopen = () => {
        console.log('✅ WebSocket 连接成功')
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0
        callbacks.onConnect.forEach((cb) => cb())
      }

      ws.onclose = (event) => {
        console.log(`❌ WebSocket 断开连接: code=${event.code}`)
        isConnected.value = false
        isConnecting.value = false
        connectionId.value = null
        callbacks.onDisconnect.forEach((cb) => cb())

        // 自动重连
        if (autoReconnect && reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++
          console.log(`🔄 尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})...`)
          reconnectTimer = setTimeout(connect, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error)
        lastError.value = '连接错误'
        isConnecting.value = false
        callbacks.onError.forEach((cb) => cb('连接错误'))
      }

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (e) {
          console.error('解析消息失败:', e)
        }
      }
    } catch (error) {
      console.error('创建 WebSocket 失败:', error)
      isConnecting.value = false
      lastError.value = String(error)
    }
  }

  /**
   * 断开连接
   */
  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    reconnectAttempts.value = maxReconnectAttempts // 阻止自动重连

    if (ws) {
      ws.close()
      ws = null
    }

    isConnected.value = false
    isConnecting.value = false
    connectionId.value = null
  }

  /**
   * 发送消息
   */
  const send = (message: WSMessage) => {
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

  /**
   * 发送聊天消息
   */
  const sendChat = (content: string) => {
    return send({
      type: 'chat',
      action: 'send',
      data: { message: content },
    })
  }

  /**
   * 发送表单数据
   */
  const sendFormData = (formData: Record<string, any>) => {
    return send({
      type: 'tool',
      action: 'form_submit',
      data: { form_data: formData },
    })
  }

  /**
   * 发送 ping
   */
  const ping = () => {
    return send({
      type: 'system',
      action: 'ping',
    })
  }

  /**
   * 处理接收到的消息
   */
  const handleMessage = (message: WSMessage) => {
    // 处理连接消息
    if (message.type === 'system' && message.action === 'connected') {
      connectionId.value = message.data?.connection_id || null
    }

    // 触发回调
    callbacks.onMessage.forEach((cb) => cb(message))
  }

  /**
   * 注册消息回调
   */
  const onMessage = (callback: (message: WSMessage) => void) => {
    callbacks.onMessage.push(callback)
  }

  /**
   * 注册连接回调
   */
  const onConnect = (callback: () => void) => {
    callbacks.onConnect.push(callback)
  }

  /**
   * 注册断开回调
   */
  const onDisconnect = (callback: () => void) => {
    callbacks.onDisconnect.push(callback)
  }

  /**
   * 注册错误回调
   */
  const onError = (callback: (error: string) => void) => {
    callbacks.onError.push(callback)
  }

  // 组件卸载时断开连接
  onUnmounted(() => {
    disconnect()
  })

  return {
    // 状态
    isConnected,
    isConnecting,
    connectionId,
    lastError,
    reconnectAttempts,

    // 方法
    connect,
    disconnect,
    send,
    sendChat,
    sendFormData,
    ping,

    // 事件注册
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  }
}

// Symbol for provide/inject
export const WebSocketKey = Symbol('WebSocket')

