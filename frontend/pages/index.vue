<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50">
    <!-- 头部 -->
    <header class="bg-white/80 backdrop-blur-xl shadow-sm border-b border-slate-200/60">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <WorkflowLogo size="w-12 h-12" />
            <div>
              <h1 class="text-2xl font-bold text-slate-800">
                中车智能体平台
              </h1>
              <p class="text-slate-600 mt-1 text-sm">
                架构可视化 & 智能对话交互
              </p>
            </div>
          </div>
          <NuxtLink
            to="/workflow"
            class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-600 hover:from-blue-700 hover:to-blue-700 text-white font-semibold rounded-lg shadow-sm hover:shadow-md transition-all duration-200"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>工作流视图</span>
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <div class="max-w-7xl mx-auto px-4 py-6">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- 左侧：图架构可视化 -->
        <div class="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg border border-slate-200/60">
          <div class="border-b border-slate-200/60 px-6 py-4 bg-gradient-to-r from-blue-50/50 to-blue-50/50">
            <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              图架构可视化
            </h2>
            <p class="text-sm text-slate-600 mt-1">
              节点、边和路由关系图
            </p>
          </div>

          <div class="p-6">
            <GraphVisualization
              :auto-fetch="true"
              :api-base-url="'http://0.0.0.0:8001'"
              :active-node-id="activeNodeId"
              :node-execution-status="nodeExecutionStatus"
              @node-click="onNodeClick"
              @refresh-graph="fetchGraphInfo"
              @graph-loaded="onGraphLoaded"
              @graph-error="onGraphError"
            />
          </div>
        </div>

        <!-- 右侧：聊天交互界面 (占2列宽度) -->
        <div class="lg:col-span-2 bg-white/80 backdrop-blur-xl rounded-xl shadow-lg border border-slate-200/60 overflow-hidden" style="height: 700px;">
          <ModernChat
            api-base-url="http://0.0.0.0:8001"
            @node-highlight="handleNodeHighlight"
            @node-status-change="handleNodeStatusChange"
          />
        </div>
      </div>

      <!-- 底部信息面板 -->
      <div class="mt-6 bg-white/80 backdrop-blur-xl rounded-xl shadow-lg border border-slate-200/60">
        <div class="border-b border-slate-200/60 px-6 py-4 bg-gradient-to-r from-slate-50/50 to-blue-50/50">
          <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
            <svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            系统信息
          </h2>
        </div>

        <div class="p-6">
          <SystemInfo :system-status="systemStatus" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 页面元信息
useHead({
  title: 'LangGraph 可视化工具',
  meta: [
    { name: 'description', content: 'LangGraph架构可视化和交互工具' }
  ]
})

// 启动时直接重定向到 workflow 页面
onMounted(() => {
  navigateTo('/workflow')
})
</script>
