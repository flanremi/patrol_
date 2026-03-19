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
          <!-- 连接状态 -->
          <div class="hidden lg:flex items-center gap-3 px-3 py-1 bg-slate-50 rounded border border-slate-200">
            <div class="flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full"
                   :class="connectionStatus === 'connected' ? 'bg-green-500' : connectionStatus === 'connecting' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'"></div>
              <span class="text-xs text-slate-600">
                {{ connectionStatus === 'connected' ? '已连接' : connectionStatus === 'connecting' ? '连接中...' : '未连接' }}
              </span>
            </div>
          </div>

          <!-- Canvas 状态指示 -->
          <div v-if="showCanvas" class="hidden lg:flex items-center gap-1.5 px-3 py-1 bg-blue-50 rounded border border-blue-200">
            <DocumentTextIcon class="w-3.5 h-3.5 text-blue-600"/>
            <span class="text-xs text-blue-600 font-medium">
              {{ canvasMode === 'form' ? '工单编辑中' : '查看分析结果' }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主工作区 - 分为左右两栏 -->
    <main class="flex-1 overflow-hidden flex relative">
      <!-- 左侧聊天界面 (动态宽度) -->
      <div
        class="border-r border-slate-200 bg-white shadow-lg z-20 transition-all duration-700 ease-in-out relative"
        :class="showCanvas ? 'w-2/5' : 'w-full'"
      >
        <ModernChat
          ref="chatRef"
          :api-base-url="apiBaseUrl"
          @show-form="handleShowForm"
          @show-result="handleShowResult"
          @show-analyzing="handleShowAnalyzing"
          @hide-canvas="handleHideCanvas"
          @analysis-start="handleAnalysisStart"
          @analysis-step="handleAnalysisStep"
          @analysis-complete="handleAnalysisComplete"
          @analysis-error="handleAnalysisError"
        />

        <!-- Canvas 面板切换按钮 - 右侧中央 -->
        <button
          v-if="showCanvas"
          @click="toggleCanvas"
          class="absolute top-1/2 -translate-y-1/2 z-30 w-6 h-6 rounded-full p-1 hover:shadow-xl transition-all duration-200 flex items-center justify-center group border border-slate-200 -right-3 bg-white"
          title="隐藏面板"
        >
          <ChevronRightIcon
            class="w-4 h-4 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all"
          />
        </button>
      </div>

      <!-- 右侧 Canvas 面板 -->
      <div
        class="overflow-hidden relative transition-all duration-700 ease-in-out"
        :class="showCanvas ? 'flex-1 opacity-100' : 'w-0 opacity-0 pointer-events-none'"
      >
        <InspectionCanvas
          ref="canvasRef"
          :show-form="canvasMode === 'form'"
          :analysis-result="analysisResult"
          :prefill-data="prefillData"
          @submit="handleFormSubmit"
          @close="handleHideCanvas"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
// 页面元信息
useHead({
  title: '故障检测智能体',
  meta: [
    { name: 'description', content: '轨道交通故障检测智能分析系统' },
  ],
})

// 导入 Vue
import { nextTick } from 'vue'

// 导入组件
import WorkflowLogo from '~/components/workflow/WorkflowLogo.vue'
import ModernChat from '~/components/ModernChat.vue'
import InspectionCanvas from '~/components/InspectionCanvas.vue'
import { ChevronRightIcon, DocumentTextIcon } from '@heroicons/vue/24/outline'
import { ChatStoreKey, useChatStore } from '~/composables/useChatStore'

// 配置 - 使用运行时配置或环境变量
const config = useRuntimeConfig()
const apiBaseUrl = config.public.apiBaseUrl || 'http://123.151.89.76:8001'

// 创建聊天存储并提供给子组件
const chatStore = useChatStore()
provide(ChatStoreKey, chatStore)

// 响应式数据
const connectionStatus = ref('disconnected')
const showCanvas = ref(false)
const canvasMode = ref('form') // 'form' | 'result'
const analysisResult = ref(null)
const prefillData = ref(null)

// 组件引用
const chatRef = ref(null)
const canvasRef = ref(null)

// 切换 Canvas 显示
const toggleCanvas = () => {
  showCanvas.value = !showCanvas.value
}

// 显示表单
const handleShowForm = (data = null) => {
  prefillData.value = data
  canvasMode.value = 'form'
  showCanvas.value = true
}

// 显示分析结果
const handleShowResult = (result) => {
  analysisResult.value = result
  canvasMode.value = 'result'
  showCanvas.value = true
}

// 显示分析流程（不重置步骤，仅切换视图）
const handleShowAnalyzing = () => {
  canvasMode.value = 'analyzing'
  showCanvas.value = true
  nextTick(() => {
    if (canvasRef.value && canvasRef.value.showAnalyzingView) {
      canvasRef.value.showAnalyzingView()
    }
  })
}

// 隐藏 Canvas
const handleHideCanvas = () => {
  showCanvas.value = false
}

// 处理表单提交 - 发送包装好的工单查询信息
const handleFormSubmit = (formData) => {
  console.log('📝 工单提交:', formData)
  
  // 通过 WebSocket 发送表单数据（包含查询消息）
  if (chatRef.value && chatRef.value.sendFormData) {
    chatRef.value.sendFormData(formData)
  }
}

// 处理分析开始事件
const handleAnalysisStart = (data) => {
  console.log('🔄 分析开始:', data)
  
  // 展开 Canvas
  showCanvas.value = true
  canvasMode.value = 'analyzing'
  
  // 使用 nextTick 确保 DOM 更新后再调用组件方法
  nextTick(() => {
    if (canvasRef.value && canvasRef.value.startAnalyzing) {
      canvasRef.value.startAnalyzing()
      console.log('📢 已调用 Canvas.startAnalyzing()')
    } else {
      console.warn('⚠️ canvasRef 未就绪')
    }
  })
}

// 处理分析步骤事件
const handleAnalysisStep = (data) => {
  console.log('📊 分析步骤:', data)
  
  // 确保 Canvas 已展开
  if (!showCanvas.value) {
    showCanvas.value = true
  }
  
  // 使用 nextTick 确保组件已挂载
  nextTick(() => {
    if (canvasRef.value && canvasRef.value.addAnalysisStep) {
      canvasRef.value.addAnalysisStep(data)
      console.log('📢 已添加步骤:', data.node)
    }
  })
}

// 处理分析完成事件
const handleAnalysisComplete = (data) => {
  console.log('✅ 分析完成:', data)
  
  // 设置分析结果
  analysisResult.value = data
  canvasMode.value = 'result'
  
  // 自动展开 Canvas 显示报告
  showCanvas.value = true
  
  // 使用 nextTick 确保状态更新后调用方法
  nextTick(() => {
    if (canvasRef.value && canvasRef.value.completeAnalysis) {
      canvasRef.value.completeAnalysis(data)
      canvasRef.value.showResultView()  // 确保切换到结果视图
      console.log('📢 已调用 Canvas.completeAnalysis() 和 showResultView()')
    }
  })
}

// 处理分析错误事件
const handleAnalysisError = (data) => {
  console.error('❌ 分析错误:', data)
  
  nextTick(() => {
    if (canvasRef.value && canvasRef.value.setSubmitting) {
      canvasRef.value.setSubmitting(false)
    }
  })
}

// 监听聊天存储中的事件
chatStore.onChatStart(() => {
  connectionStatus.value = 'connected'
})

// 初始化
onMounted(() => {
  // 初始状态：不展开 Canvas
  showCanvas.value = false
})
</script>
