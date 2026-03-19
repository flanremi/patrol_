<template>
  <div class="inspection-canvas h-full w-full bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 overflow-hidden flex flex-col">
    <!-- 头部标题栏 -->
    <div class="flex-shrink-0 px-6 py-4 bg-white/80 backdrop-blur-sm border-b border-slate-200/60">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <ClipboardDocumentListIcon class="w-5 h-5 text-white"/>
          </div>
          <div>
            <h2 class="text-lg font-bold text-slate-800">
              {{ viewTitle }}
            </h2>
            <p class="text-sm text-slate-500">
              {{ viewSubtitle }}
            </p>
          </div>
        </div>
        
        <!-- 视图切换 -->
        <div class="flex items-center gap-2">
          <!-- 分析进行中的状态 -->
          <div v-if="currentView === 'analyzing'" class="flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg">
            <ArrowPathIcon class="w-4 h-4 animate-spin"/>
            <span class="text-sm font-medium">分析中...</span>
          </div>
          <button
            v-if="canSwitchView"
            @click="toggleView"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
            :class="currentView === 'form' 
              ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
              : 'bg-amber-100 text-amber-700 hover:bg-amber-200'"
          >
            <span v-if="currentView === 'form'">查看分析结果</span>
            <span v-else>返回工单</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div ref="scrollContainer" class="flex-1 overflow-y-auto p-6">
      <!-- 工单表单视图 -->
      <div v-if="currentView === 'form'" class="max-w-3xl mx-auto">
        <div class="bg-white rounded-2xl shadow-xl border border-slate-200/60 overflow-hidden">
          <!-- 表单头部装饰 -->
          <div class="h-2 bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-400"></div>
          
          <div class="p-8">
            <!-- 工单编号 -->
            <div class="flex items-center justify-between mb-8 pb-4 border-b border-slate-100">
              <div class="flex items-center gap-3">
                <div class="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-sm font-mono font-semibold">
                  工单号: {{ workOrderNo }}
                </div>
                <div class="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-sm">
                  {{ formData.detect_time || '待填写' }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full animate-pulse"
                      :class="isSubmitting ? 'bg-amber-500' : 'bg-green-500'"></span>
                <span class="text-sm text-slate-500">{{ isSubmitting ? '分析中...' : '待提交' }}</span>
              </div>
            </div>

            <!-- 表单字段 -->
            <form @submit.prevent="handleSubmit" class="space-y-6">
              <!-- 基本信息区块 -->
              <div class="space-y-4">
                <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                  <div class="w-1 h-4 bg-blue-500 rounded-full"></div>
                  基本信息
                </h3>
                
                <div class="grid grid-cols-2 gap-4">
                  <!-- 检测时间 -->
                  <div class="form-group">
                    <label class="block text-sm font-semibold text-slate-600 mb-2">
                      <span class="text-red-500 mr-1">*</span>检测时间
                    </label>
                    <input
                      type="datetime-local"
                      v-model="formData.detect_time"
                      required
                      class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all text-slate-800 bg-slate-50/50"
                    />
                  </div>

                  <!-- 检测置信度 -->
                  <div class="form-group">
                    <label class="block text-sm font-semibold text-slate-600 mb-2">
                      检测置信度
                      <span class="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-bold">
                        {{ (formData.detect_confidence * 100).toFixed(0) }}%
                      </span>
                    </label>
                    <input
                      type="range"
                      v-model.number="formData.detect_confidence"
                      min="0"
                      max="1"
                      step="0.01"
                      class="w-full h-3 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div class="flex justify-between text-xs text-slate-400 mt-1">
                      <span>低</span>
                      <span>高</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 故障信息区块 -->
              <div class="space-y-4">
                <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                  <div class="w-1 h-4 bg-amber-500 rounded-full"></div>
                  故障信息
                </h3>
                
                <div class="grid grid-cols-2 gap-4">
                  <!-- 部件名称 -->
                  <div class="form-group">
                    <label class="block text-sm font-semibold text-slate-600 mb-2">
                      <span class="text-red-500 mr-1">*</span>部件名称
                    </label>
                    <input
                      type="text"
                      v-model="formData.part_name"
                      required
                      placeholder="如：辅助逆变器、轴承、制动器"
                      class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all text-slate-800 placeholder-slate-400 bg-slate-50/50"
                    />
                  </div>

                  <!-- 部件位置 -->
                  <div class="form-group">
                    <label class="block text-sm font-semibold text-slate-600 mb-2">
                      部件位置
                    </label>
                    <input
                      type="text"
                      v-model="formData.part_position"
                      placeholder="如：0116车、A轴、前转向架"
                      class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all text-slate-800 placeholder-slate-400 bg-slate-50/50"
                    />
                  </div>
                </div>

                <!-- 缺陷类型 -->
                <div class="form-group">
                  <label class="block text-sm font-semibold text-slate-600 mb-2">
                    <span class="text-red-500 mr-1">*</span>缺陷类型
                  </label>
                  <input
                    type="text"
                    v-model="formData.defect_type"
                    required
                    placeholder="如：显黄、温度异常、振动过大、噪音异常"
                    class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all text-slate-800 placeholder-slate-400 bg-slate-50/50"
                  />
                </div>

                <!-- 故障描述 -->
                <div class="form-group">
                  <label class="block text-sm font-semibold text-slate-600 mb-2">
                    故障描述（可选）
                  </label>
                  <textarea
                    v-model="formData.description"
                    rows="3"
                    placeholder="详细描述故障现象、发现时间、运行环境等信息..."
                    class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all text-slate-800 placeholder-slate-400 bg-slate-50/50 resize-none"
                  ></textarea>
                </div>
              </div>

              <!-- 提交按钮 -->
              <div class="pt-6 border-t border-slate-100">
                <div class="flex items-center gap-4">
                  <button
                    type="submit"
                    :disabled="isSubmitting || !isFormValid"
                    class="flex-1 px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 hover:from-blue-600 hover:to-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none flex items-center justify-center gap-3"
                  >
                    <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
                    <PaperAirplaneIcon v-else class="w-5 h-5"/>
                    <span>{{ isSubmitting ? '分析中...' : '发送工单' }}</span>
                  </button>
                  <button
                    type="button"
                    @click="resetForm"
                    :disabled="isSubmitting"
                    class="px-6 py-4 bg-slate-100 text-slate-700 font-semibold rounded-xl hover:bg-slate-200 transition-all duration-200 disabled:opacity-50"
                  >
                    重置
                  </button>
                </div>
                <!-- 发送说明 -->
                <p class="text-xs text-slate-500 mt-3 text-center">
                  点击发送后，系统将基于工单信息进行智能故障分析
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- 分析进行中视图 - 实时展示思考过程 -->
      <div v-else-if="currentView === 'analyzing'" class="max-w-4xl mx-auto">
        <!-- 任务进度头部 - 置顶 sticky -->
        <div class="sticky top-0 z-10 bg-white rounded-2xl shadow-xl border border-slate-200/60 overflow-hidden mb-4">
          <div class="h-1.5 bg-gradient-to-r from-blue-500 via-cyan-400 to-blue-500 animate-gradient"></div>
          <div class="p-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center shadow-lg relative">
                  <CpuChipIcon class="w-6 h-6 text-white"/>
                  <span class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></span>
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-800">智能分析进行中</h3>
                  <p class="text-sm text-slate-500">{{ currentStepTitle || '正在初始化...' }}</p>
                </div>
              </div>
              <div class="text-right">
                <div class="text-xl font-bold text-blue-600">{{ analysisSteps.length }}</div>
                <div class="text-xs text-slate-500">已完成步骤</div>
              </div>
            </div>
            <!-- 进度条 - 更慢的进度 -->
            <div class="mt-3 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-1000 ease-out rounded-full"
                   :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="flex justify-between mt-1">
              <span class="text-xs text-slate-400">进度</span>
              <span class="text-xs text-blue-600 font-medium">{{ Math.round(progressPercent) }}%</span>
            </div>
          </div>
        </div>

        <!-- 实时思考过程列表 -->
        <div class="space-y-3" ref="stepsContainer">
          <TransitionGroup name="step-list">
            <div v-for="(step, index) in analysisSteps" :key="step.id || index"
                 class="bg-white rounded-xl shadow-md border border-slate-200/60 overflow-hidden transform transition-all duration-300"
                 :class="{ 'ring-2 ring-blue-400 ring-opacity-50': index === analysisSteps.length - 1 }">
              <!-- 步骤头部 -->
              <div class="px-4 py-3 flex items-center gap-3 cursor-pointer"
                   :class="getStepHeaderClass(step)"
                   @click="toggleStepExpand(index)">
                <!-- 步骤序号 -->
                <div class="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600 flex-shrink-0">
                  {{ index + 1 }}
                </div>
                <!-- 状态图标 -->
                <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                     :class="getStepIconClass(step)">
                  <component :is="getStepIcon(step)" class="w-4 h-4"/>
                </div>
                <!-- 步骤信息 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-mono px-2 py-0.5 rounded"
                          :class="getStepBadgeClass(step)">{{ step.node }}</span>
                    <span class="text-sm font-semibold text-slate-700 truncate">{{ step.title }}</span>
                  </div>
                  <p v-if="step.summary" class="text-xs text-slate-500 mt-0.5 truncate">{{ step.summary }}</p>
                </div>
                <!-- 展开/收起图标 -->
                <ChevronDownIcon class="w-5 h-5 text-slate-400 transition-transform flex-shrink-0"
                                 :class="{ 'rotate-180': expandedSteps.has(index) }"/>
              </div>
              <!-- 步骤详情 -->
              <Transition name="expand">
                <div v-if="expandedSteps.has(index)" class="px-4 pb-4 border-t border-slate-100">
                  <div class="pt-3 space-y-2">
                    <!-- 步骤详细内容 -->
                    <div v-if="step.content" class="text-sm text-slate-600 whitespace-pre-wrap bg-slate-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                      {{ step.content }}
                    </div>
                    <!-- 步骤数据 -->
                    <div v-if="step.data" class="text-xs">
                      <template v-if="step.data.entities">
                        <div class="flex flex-wrap gap-1 mt-2">
                          <span v-for="entity in step.data.entities.slice(0, 10)" :key="entity"
                                class="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">{{ entity }}</span>
                          <span v-if="step.data.entities.length > 10" class="px-2 py-0.5 bg-slate-100 text-slate-500 rounded">
                            +{{ step.data.entities.length - 10 }} 更多
                          </span>
                        </div>
                      </template>
                      <template v-if="step.data.docs_count !== undefined">
                        <p class="text-slate-500 mt-1">检索到 {{ step.data.docs_count }} 条相关记录</p>
                      </template>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </TransitionGroup>
        </div>

        <!-- 等待更多步骤的提示 -->
        <div v-if="isAnalyzing" class="flex items-center justify-center py-6 gap-2 text-slate-500">
          <ArrowPathIcon class="w-4 h-4 animate-spin"/>
          <span class="text-sm">正在处理下一步...</span>
        </div>
      </div>

      <!-- 分析结果视图 -->
      <div v-else-if="currentView === 'result'" class="max-w-4xl mx-auto space-y-6">
        <!-- 结果头部 -->
        <div class="bg-white rounded-2xl shadow-xl border border-slate-200/60 overflow-hidden">
          <div class="h-2 bg-gradient-to-r from-green-500 via-emerald-400 to-cyan-400"></div>
          <div class="p-6">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
                  <CheckCircleIcon class="w-7 h-7 text-white"/>
                </div>
                <div>
                  <h3 class="text-xl font-bold text-slate-800">分析完成</h3>
                  <p class="text-slate-500">{{ analysisResult?.timestamp || '刚刚' }}</p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm font-semibold">
                  检索次数: {{ analysisResult?.retry_count || 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 故障信息摘要 -->
        <div class="bg-white rounded-2xl shadow-lg border border-slate-200/60 p-6">
          <h4 class="text-sm font-bold text-slate-700 uppercase tracking-wide mb-4 flex items-center gap-2">
            <DocumentTextIcon class="w-4 h-4"/>
            故障信息摘要
          </h4>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-slate-50 rounded-xl p-4">
              <p class="text-xs text-slate-500 mb-1">部件名称</p>
              <p class="font-semibold text-slate-800">{{ analysisResult?.input?.part_name || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-xl p-4">
              <p class="text-xs text-slate-500 mb-1">部件位置</p>
              <p class="font-semibold text-slate-800">{{ analysisResult?.input?.part_position || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-xl p-4">
              <p class="text-xs text-slate-500 mb-1">缺陷类型</p>
              <p class="font-semibold text-slate-800">{{ analysisResult?.input?.defect_type || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-xl p-4">
              <p class="text-xs text-slate-500 mb-1">检测置信度</p>
              <p class="font-semibold text-slate-800">{{ ((analysisResult?.input?.detect_confidence || 0) * 100).toFixed(0) }}%</p>
            </div>
          </div>
        </div>

        <!-- 最终分析报告 -->
        <div v-if="analysisReportContent" class="bg-white rounded-2xl shadow-lg border border-slate-200/60 overflow-hidden">
          <div class="px-6 py-4 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-slate-200">
            <h4 class="text-sm font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
              <SparklesIcon class="w-4 h-4 text-blue-500"/>
              智能分析报告
            </h4>
          </div>
          <div class="p-6">
            <div class="prose prose-slate max-w-none" v-html="renderMarkdown(analysisReportContent)"></div>
          </div>
        </div>

        <!-- 思考过程（可折叠抽屉）-->
        <div v-if="analysisSteps.length > 0" class="bg-white rounded-2xl shadow-lg border border-slate-200/60 overflow-hidden">
          <!-- 抽屉头部 -->
          <div class="px-6 py-4 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-200 cursor-pointer flex items-center justify-between hover:from-amber-100 hover:to-orange-100 transition-colors"
               @click="showThinkingProcess = !showThinkingProcess">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                <LightBulbIcon class="w-4 h-4 text-amber-600"/>
              </div>
              <div>
                <h4 class="text-sm font-bold text-amber-800 flex items-center gap-2">
                  智能体思考过程
                  <span class="px-2 py-0.5 bg-amber-200 text-amber-800 rounded-full text-xs font-medium">
                    {{ analysisSteps.length }} 步
                  </span>
                </h4>
                <p class="text-xs text-amber-600">{{ showThinkingProcess ? '点击折叠' : '点击展开查看分析过程' }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs text-amber-600 font-medium">{{ showThinkingProcess ? '收起' : '展开' }}</span>
              <ChevronDownIcon class="w-5 h-5 text-amber-600 transition-transform duration-300" 
                               :class="{ 'rotate-180': showThinkingProcess }"/>
            </div>
          </div>
          
          <!-- 抽屉内容 -->
          <Transition name="drawer">
            <div v-if="showThinkingProcess" class="border-t border-amber-100">
              <div class="p-4 space-y-3 max-h-[400px] overflow-y-auto bg-gradient-to-b from-amber-50/30 to-white">
                <div v-for="(step, index) in analysisSteps" :key="step.id || index"
                     class="bg-white rounded-xl p-4 border-l-4 shadow-sm hover:shadow-md transition-shadow"
                     :class="getStepBorderClass(step)">
                  <div class="flex items-center gap-3 mb-2">
                    <!-- 步骤序号 -->
                    <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500">
                      {{ index + 1 }}
                    </div>
                    <!-- 步骤图标 -->
                    <div class="w-7 h-7 rounded-lg flex items-center justify-center"
                         :class="getStepIconClass(step)">
                      <component :is="getStepIcon(step)" class="w-3.5 h-3.5"/>
                    </div>
                    <div class="flex-1">
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-mono px-2 py-0.5 rounded"
                              :class="getStepBadgeClass(step)">{{ step.node }}</span>
                        <span class="text-sm font-semibold text-slate-700">{{ step.title }}</span>
                      </div>
                    </div>
                  </div>
                  <p v-if="step.summary" class="text-sm text-slate-600 pl-16">{{ step.summary }}</p>
                  <!-- 展开详细内容 -->
                  <div v-if="step.content" class="mt-2 pl-16">
                    <details class="group">
                      <summary class="text-xs text-blue-600 cursor-pointer hover:text-blue-800">
                        查看详细内容
                      </summary>
                      <div class="mt-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3 max-h-32 overflow-y-auto whitespace-pre-wrap">
                        {{ step.content }}
                      </div>
                    </details>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="h-full flex items-center justify-center">
        <div class="text-center">
          <div class="w-24 h-24 mx-auto mb-6 bg-slate-100 rounded-full flex items-center justify-center">
            <ClipboardDocumentListIcon class="w-12 h-12 text-slate-400"/>
          </div>
          <h3 class="text-lg font-semibold text-slate-600 mb-2">暂无内容</h3>
          <p class="text-slate-400">请通过对话触发故障分析</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, reactive, watch, nextTick } from 'vue'
import { marked } from 'marked'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ClipboardDocumentListIcon,
  CpuChipIcon,
  DocumentTextIcon,
  LightBulbIcon,
  MagnifyingGlassIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  CogIcon,
  BeakerIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/vue/24/outline'

// 滚动容器引用
const scrollContainer = ref(null)
const stepsContainer = ref(null)

// Props
const props = defineProps({
  // 是否显示表单
  showForm: {
    type: Boolean,
    default: false,
  },
  // 分析结果
  analysisResult: {
    type: Object,
    default: null,
  },
  // 预填充数据
  prefillData: {
    type: Object,
    default: null,
  },
})

// Emits
const emit = defineEmits(['submit', 'close'])

// 工单编号
const workOrderNo = ref(`FD${Date.now().toString().slice(-8)}`)

// 当前视图: 'form' | 'analyzing' | 'result'
const currentView = ref('form')

// 表单数据 - 预填充示例数据
const formData = reactive({
  detect_time: new Date().toISOString().slice(0, 16),
  part_name: '辅助逆变器',
  part_position: '0116车',
  defect_type: '显黄',
  detect_confidence: 0.95,
  description: '',
})

// 状态
const isSubmitting = ref(false)
const isAnalyzing = ref(false)
const isAnalysisComplete = ref(false) // 分析是否完成
const showThinkingProcess = ref(false)

// 分析步骤列表
const analysisSteps = ref([])
const expandedSteps = ref(new Set())
const currentStepTitle = ref('')

// 预估步骤数（固定值，避免进度条抖动）
const estimatedSteps = ref(17) // 初始预估 17 步

// 是否检测到补充检索（如果检测到，进度直接跳到90%）
const hasSupplementaryRetrieval = ref(false)

// 视图标题和副标题
const viewTitle = computed(() => {
  switch (currentView.value) {
    case 'form': return '故障检测工单'
    case 'analyzing': return '智能分析进行中'
    case 'result': return '故障分析报告'
    default: return '巡检分析'
  }
})

const viewSubtitle = computed(() => {
  switch (currentView.value) {
    case 'form': return '填写缺陷信息进行智能分析'
    case 'analyzing': return `已完成 ${analysisSteps.value.length} 个分析步骤`
    case 'result': return '查看详细分析结果'
    default: return ''
  }
})

// 进度百分比（平滑计算，避免抖动）
const progressPercent = computed(() => {
  // 如果分析已完成，显示 100%
  if (isAnalysisComplete.value) {
    return 100
  }
  
  // 如果检测到补充检索，直接显示 90%
  if (hasSupplementaryRetrieval.value) {
    return 90
  }
  
  const steps = analysisSteps.value.length
  const currentEstimated = estimatedSteps.value
  
  // 初始状态
  if (steps === 0) return 3
  
  // 使用平滑的对数函数计算进度，避免频繁变化
  // 基于固定预估步骤数，不再动态调整
  const logProgress = Math.log(steps + 1) / Math.log(currentEstimated + 1) * 85
  
  // 线性进度作为辅助
  const linearProgress = (steps / currentEstimated) * 80
  
  // 混合计算，更平滑
  const weight = steps < currentEstimated * 0.5 ? 0.6 : 0.4
  const mixedProgress = logProgress * weight + linearProgress * (1 - weight)
  
  // 不超过 85%（留给补充检索时跳到90%）
  return Math.min(Math.max(mixedProgress, 3), 85)
})

// 是否可以切换视图
const canSwitchView = computed(() => {
  return (currentView.value === 'form' && props.analysisResult) ||
         (currentView.value === 'result' && true)
})

// 是否有分析结果
const hasAnalysisResult = computed(() => !!props.analysisResult)

// 获取分析报告内容（兼容多种字段名）
const analysisReportContent = computed(() => {
  if (!props.analysisResult) return ''
  // 优先使用 final_report，其次是 report_markdown
  return props.analysisResult.final_report || props.analysisResult.report_markdown || ''
})

// 表单验证
const isFormValid = computed(() => {
  return formData.part_name?.trim() && formData.defect_type?.trim()
})

// 监听预填充数据
watch(() => props.prefillData, (newData) => {
  if (newData) {
    Object.assign(formData, newData)
  }
}, { immediate: true })

// 监听分析结果，自动切换视图
watch(() => props.analysisResult, (newResult) => {
  if (newResult) {
    currentView.value = 'result'
    isSubmitting.value = false
    isAnalyzing.value = false
    // 结果视图默认折叠思考过程
    showThinkingProcess.value = false
  }
})

// 监听 showForm
watch(() => props.showForm, (show) => {
  if (show && !hasAnalysisResult.value) {
    currentView.value = 'form'
  }
})

// 切换视图
const toggleView = () => {
  if (currentView.value === 'form') {
    currentView.value = 'result'
  } else {
    currentView.value = 'form'
  }
}

// 切换步骤展开/收起
const toggleStepExpand = (index) => {
  if (expandedSteps.value.has(index)) {
    expandedSteps.value.delete(index)
  } else {
    expandedSteps.value.add(index)
  }
  // 触发响应式更新
  expandedSteps.value = new Set(expandedSteps.value)
}

// 获取步骤图标
const getStepIcon = (step) => {
  const iconMap = {
    'retrieval': MagnifyingGlassIcon,
    'extraction': BeakerIcon,
    'fault_analysis': CogIcon,
    'reflection': LightBulbIcon,
    'maintenance': WrenchScrewdriverIcon,
    'error': ExclamationTriangleIcon,
    'complete': CheckCircleIcon,
  }
  return iconMap[step.node] || CpuChipIcon
}

// 获取步骤头部样式
const getStepHeaderClass = (step) => {
  if (step.status === 'error') return 'bg-red-50'
  if (step.status === 'complete') return 'bg-green-50'
  return 'bg-slate-50'
}

// 获取步骤图标样式
const getStepIconClass = (step) => {
  if (step.status === 'error') return 'bg-red-100 text-red-600'
  if (step.status === 'complete') return 'bg-green-100 text-green-600'
  
  const colorMap = {
    'retrieval': 'bg-blue-100 text-blue-600',
    'extraction': 'bg-purple-100 text-purple-600',
    'fault_analysis': 'bg-amber-100 text-amber-600',
    'reflection': 'bg-cyan-100 text-cyan-600',
    'maintenance': 'bg-emerald-100 text-emerald-600',
  }
  return colorMap[step.node] || 'bg-slate-100 text-slate-600'
}

// 获取步骤标签样式
const getStepBadgeClass = (step) => {
  if (step.status === 'error') return 'bg-red-100 text-red-700'
  
  const colorMap = {
    'retrieval': 'bg-blue-100 text-blue-700',
    'extraction': 'bg-purple-100 text-purple-700',
    'fault_analysis': 'bg-amber-100 text-amber-700',
    'reflection': 'bg-cyan-100 text-cyan-700',
    'maintenance': 'bg-emerald-100 text-emerald-700',
  }
  return colorMap[step.node] || 'bg-slate-100 text-slate-700'
}

// 获取步骤边框样式
const getStepBorderClass = (step) => {
  const colorMap = {
    'retrieval': 'border-blue-400',
    'extraction': 'border-purple-400',
    'fault_analysis': 'border-amber-400',
    'reflection': 'border-cyan-400',
    'maintenance': 'border-emerald-400',
  }
  return colorMap[step.node] || 'border-slate-400'
}

// 提交表单 - 发送包装好的工单查询信息
const handleSubmit = () => {
  if (!isFormValid.value || isSubmitting.value) return
  
  isSubmitting.value = true
  
  // 构建包装好的工单查询信息
  const queryMessage = `请根据以下故障检测工单进行分析：
- 检测时间：${formData.detect_time}
- 部件名称：${formData.part_name}
- 部件位置：${formData.part_position || '未指定'}
- 缺陷类型：${formData.defect_type}
- 检测置信度：${(formData.detect_confidence * 100).toFixed(0)}%
${formData.description ? `- 故障描述：${formData.description}` : ''}

请进行故障原因分析并给出维护建议。`
  
  // 发送表单数据和查询消息
  emit('submit', { 
    ...formData,
    queryMessage // 包装好的查询消息
  })
}

// 重置表单
const resetForm = () => {
  formData.detect_time = new Date().toISOString().slice(0, 16)
  formData.part_name = ''
  formData.part_position = ''
  formData.defect_type = ''
  formData.detect_confidence = 0.95
  formData.description = ''
  workOrderNo.value = `FD${Date.now().toString().slice(-8)}`
}

// 添加分析步骤
const addAnalysisStep = (step) => {
  console.log('📥 InspectionCanvas.addAnalysisStep:', step)
  
  const stepWithId = {
    ...step,
    id: `step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
  }
  
  // 检测反思节点或补充检索，如果检测到，进度直接跳到90%
  const nodeName = step.node || step.node_name || ''
  const title = step.title || ''
  const content = step.content || ''
  
  // 如果检测到反思节点或补充检索相关的内容，标记为补充检索
  if (
    nodeName.includes('反思') || 
    nodeName.includes('reflection') ||
    title.includes('信息不足') ||
    title.includes('补充检索') ||
    content.includes('补充检索') ||
    content.includes('信息不足')
  ) {
    // 检测到反思或补充检索，进度直接跳到90%
    if (!hasSupplementaryRetrieval.value) {
      hasSupplementaryRetrieval.value = true
      console.log('🔄 检测到补充检索，进度跳到90%')
    }
  }
  
  // 使用新数组来触发响应式更新
  analysisSteps.value = [...analysisSteps.value, stepWithId]
  currentStepTitle.value = step.title || '处理中...'
  
  // 自动展开最新步骤
  const newExpandedSteps = new Set(expandedSteps.value)
  newExpandedSteps.add(analysisSteps.value.length - 1)
  expandedSteps.value = newExpandedSteps
  
  console.log('📊 当前步骤数:', analysisSteps.value.length, '预估步骤数:', estimatedSteps.value, '当前视图:', currentView.value)
  
  // 自动滚动到底部
  scrollToBottom()
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTo({
        top: scrollContainer.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

// 开始分析
const startAnalyzing = () => {
  console.log('🚀 InspectionCanvas.startAnalyzing() 被调用')
  
  isAnalyzing.value = true
  isAnalysisComplete.value = false // 重置完成状态
  currentView.value = 'analyzing'
  analysisSteps.value = []
  expandedSteps.value = new Set()
  currentStepTitle.value = '正在初始化...'
  estimatedSteps.value = 17 // 重置为初始预估 17 步
  hasSupplementaryRetrieval.value = false // 重置补充检索标志
  
  console.log('📊 视图已切换到:', currentView.value, '初始预估步骤数:', estimatedSteps.value)
}

// 完成分析
const completeAnalysis = (result) => {
  console.log('✅ InspectionCanvas.completeAnalysis:', result)
  
  isAnalyzing.value = false
  isAnalysisComplete.value = true // 标记分析完成，进度条显示 100%
  currentView.value = 'result'
  
  // 将最终报告中的思考过程合并到 analysisSteps
  if (result?.thinking_processes && Array.isArray(result.thinking_processes)) {
    // 如果 thinking_processes 是对象数组，使用它们
    // 如果是字符串数组，转换为对象格式
    const formattedSteps = result.thinking_processes.map((step, index) => {
      if (typeof step === 'object') {
        return { ...step, id: `final-step-${index}` }
      }
      return {
        id: `final-step-${index}`,
        node: 'process',
        title: `步骤 ${index + 1}`,
        summary: step,
      }
    })
    
    // 如果当前没有步骤，使用这些步骤
    if (analysisSteps.value.length === 0) {
      analysisSteps.value = formattedSteps
    }
  }
  
  // 默认不展开思考过程（折叠状态）
  showThinkingProcess.value = false
  
  // 滚动到顶部查看结果
  scrollToTop()
  
  console.log('📊 分析完成，视图切换到:', currentView.value)
}

// 滚动到顶部
const scrollToTop = () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
  })
}

// 清空步骤
const clearSteps = () => {
  analysisSteps.value = []
  expandedSteps.value = new Set()
  currentStepTitle.value = ''
  isAnalysisComplete.value = false
  hasSupplementaryRetrieval.value = false
  estimatedSteps.value = 17
}

// Markdown 渲染
const renderMarkdown = (content) => {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (error) {
    return content
  }
}

// 暴露方法
defineExpose({
  resetForm,
  setSubmitting: (value) => { isSubmitting.value = value },
  showFormView: () => { currentView.value = 'form' },
  showAnalyzingView: () => { currentView.value = 'analyzing' },
  showResultView: () => { currentView.value = 'result' },
  startAnalyzing,
  addAnalysisStep,
  completeAnalysis,
  clearSteps,
  // 获取当前分析步骤
  getAnalysisSteps: () => analysisSteps.value,
})
</script>

<style scoped>
.inspection-canvas {
  --scrollbar-width: 6px;
}

/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: var(--scrollbar-width);
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Range slider 样式 */
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.4);
}

input[type="range"]::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 50%;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.4);
}

/* Prose 样式增强 */
.prose :deep(h1),
.prose :deep(h2),
.prose :deep(h3) {
  color: #1e293b;
  font-weight: 700;
}

.prose :deep(h1) {
  font-size: 1.5rem;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.prose :deep(h2) {
  font-size: 1.25rem;
  margin-top: 1.25rem;
  margin-bottom: 0.75rem;
}

.prose :deep(h3) {
  font-size: 1.125rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.prose :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.7;
}

.prose :deep(ul),
.prose :deep(ol) {
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
}

.prose :deep(li) {
  margin-bottom: 0.25rem;
}

.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.875rem;
}

.prose :deep(th),
.prose :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.prose :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}

.prose :deep(code) {
  background: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

.prose :deep(pre) {
  background: #1e293b;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
}

.prose :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #f8fafc;
}

/* 步骤列表动画 */
.step-list-enter-active {
  transition: all 0.4s ease-out;
}

.step-list-leave-active {
  transition: all 0.3s ease-in;
}

.step-list-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.step-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.step-list-move {
  transition: transform 0.3s ease;
}

/* 展开/收起动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
}

/* 抽屉动画 */
.drawer-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.drawer-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.drawer-enter-from {
  opacity: 0;
  max-height: 0;
  transform: translateY(-10px);
}

.drawer-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-10px);
}

.drawer-enter-to,
.drawer-leave-from {
  opacity: 1;
  max-height: 500px;
  transform: translateY(0);
}

/* 渐变动画背景 */
@keyframes gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animate-gradient {
  background-size: 200% 200%;
  animation: gradient 2s ease infinite;
}
</style>

