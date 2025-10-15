export default defineEventHandler(async (event) => {
  try {
    // 尝试连接Python后端获取状态
    const response = await $fetch('http://localhost:8001/status', {
      method: 'GET',
      timeout: 5000
    })

    return {
      connected: true,
      nodes_count: response.nodes_count || 4,
      tools_count: response.tools_count || 2,
      last_update: new Date().toISOString(),
      backend_status: response
    }

  } catch (error) {
    console.error('Status API Error:', error)
    
    // 返回模拟状态（当后端不可用时）
    return {
      connected: false,
      nodes_count: 4,
      tools_count: 2,
      last_update: new Date().toISOString(),
      error: '后端服务不可用',
      mock: true
    }
  }
})
