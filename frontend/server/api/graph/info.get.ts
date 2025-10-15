export default defineEventHandler(async (event) => {
  try {
    // 尝试从后端获取图架构信息
    const response = await $fetch('http://localhost:8000/graph/info', {
      method: 'GET',
      timeout: 5000
    })

    return {
      success: true,
      nodes: response.nodes || [],
      edges: response.edges || [],
      tools: response.tools || [],
      timestamp: new Date().toISOString()
    }

  } catch (error) {
    console.error('Graph Info API Error:', error)
    
    // 返回默认的图架构信息（当后端不可用时）
    return {
      success: false,
      nodes: [
        { id: 'start', name: 'START', type: 'start', label: 'START' },
        { id: 'chatbot', name: 'ChatbotNode', type: 'chatbot', label: 'ChatbotNode' },
        { id: 'tool', name: 'ToolNode', type: 'tool', label: 'ToolNode' },
        { id: 'summary', name: 'SummaryNode', type: 'summary', label: 'SummaryNode' },
        { id: 'end', name: 'END', type: 'end', label: 'END' }
      ],
      edges: [
        { from: 'start', to: 'chatbot', type: 'direct', label: '开始' },
        { from: 'chatbot', to: 'tool', type: 'conditional', label: '有工具调用' },
        { from: 'chatbot', to: 'summary', type: 'conditional', label: '无工具调用' },
        { from: 'tool', to: 'summary', type: 'direct', label: '工具完成' },
        { from: 'summary', to: 'end', type: 'direct', label: '总结完成' }
      ],
      tools: [
        { name: 'yolo_detect_tool', description: 'YOLO图像检测工具' },
        { name: 'city_weather', description: '天气查询工具' }
      ],
      error: '后端服务不可用，使用默认配置',
      mock: true,
      timestamp: new Date().toISOString()
    }
  }
})
