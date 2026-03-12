export default defineEventHandler(async (event) => {
  try {
    const { message } = await readBody(event)
    
    if (!message) {
      throw createError({
        statusCode: 400,
        statusMessage: '消息内容不能为空'
      })
    }

    // 调用Python后端API
    const response = await $fetch('http://0.0.0.0:8001/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: {
        message: message
      }
    })

    return {
      success: true,
      messages: response.messages || [],
      metadata: response.metadata || {}
    }

  } catch (error) {
    console.error('Chat API Error:', error)
    
    // 模拟响应（当后端不可用时）
    if (error.code === 'ECONNREFUSED' || error.statusCode === 500) {
      return {
        success: false,
        messages: [
          {
            id: Date.now(),
            type: 'system',
            content: '后端服务暂不可用，这是一个模拟响应。',
            timestamp: new Date().toISOString()
          },
          {
            id: Date.now() + 1,
            type: 'ai',
            content: `您说: "${message}"\n\n这是一个模拟的AI回复。实际系统会通过LangGraph处理您的请求，包括可能的工具调用和智能总结。`,
            timestamp: new Date().toISOString(),
            tool_calls: message.includes('图片') || message.includes('检测') ? [
              {
                name: 'yolo_detect_tool',
                args: { image_path: 'patrol_img/test.jpeg' }
              }
            ] : message.includes('天气') ? [
              {
                name: 'city_weather',
                args: { city: '北京' }
              }
            ] : undefined
          }
        ]
      }
    }

    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || '服务器内部错误'
    })
  }
})
