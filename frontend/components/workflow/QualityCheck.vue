<template>
  <div class="quality-check bg-gradient-to-br from-emerald-50 to-teal-50 rounded-2xl border-2 border-emerald-200 p-6 shadow-lg animate-fade-in">
    <!-- 组件头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center border-2 border-emerald-200">
        <ClipboardDocumentCheckIcon class="w-5 h-5 text-emerald-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">工单质量检查</h3>
        <p class="text-sm text-gray-600">上传或粘贴工单内容进行质量审核</p>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="space-y-4">
      <!-- 文件上传区域 -->
      <div
        class="upload-zone relative border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer"
        :class="isDragging 
          ? 'border-emerald-400 bg-emerald-50' 
          : 'border-gray-300 hover:border-emerald-400 hover:bg-emerald-50/50'"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleFileDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".txt,.json,.md"
          class="hidden"
          @change="handleFileSelect"
        />
        
        <div class="flex flex-col items-center gap-3">
          <div class="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
            <ArrowUpTrayIcon class="w-6 h-6 text-emerald-600" />
          </div>
          <div>
            <p class="text-sm font-semibold text-gray-700">
              {{ uploadedFileName || '点击上传或拖拽文件到此处' }}
            </p>
            <p class="text-xs text-gray-500 mt-1">支持 .txt, .json, .md 格式</p>
          </div>
        </div>
      </div>

      <!-- 或者分隔线 -->
      <div class="flex items-center gap-4">
        <div class="flex-1 h-px bg-gray-200"></div>
        <span class="text-xs text-gray-400 font-medium">或者</span>
        <div class="flex-1 h-px bg-gray-200"></div>
      </div>

      <!-- 文本输入区域 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          粘贴工单内容
        </label>
        <textarea
          v-model="workOrderContent"
          rows="10"
          placeholder="在此粘贴工单内容，包括：
- 工单编号
- 维修日期和时间
- 维修人员信息
- 设备/位置信息
- 缺陷描述
- 维修内容
- 维修前后数据
- 照片记录说明"
          class="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all text-gray-900 placeholder-gray-400 resize-none font-mono text-sm"
        ></textarea>
        <div class="flex justify-between mt-1.5">
          <span class="text-xs text-gray-500">
            {{ workOrderContent.length }} 字符
          </span>
          <button
            v-if="workOrderContent"
            @click="clearContent"
            class="text-xs text-gray-500 hover:text-red-500 transition-colors"
          >
            清空内容
          </button>
        </div>
      </div>

      <!-- 审核按钮 -->
      <div class="flex items-center gap-3 pt-2">
        <button
          @click="handleSubmit"
          :disabled="isSubmitting || !hasContent"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-emerald-600 hover:to-teal-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
          <ClipboardDocumentCheckIcon v-else class="w-5 h-5"/>
          <span>{{ isSubmitting ? '审核中...' : '开始审核' }}</span>
        </button>
        <button
          @click="handleCancel"
          :disabled="isSubmitting"
          class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-all duration-200 disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </div>

    <!-- 审核结果展示 -->
    <div v-if="checkResult" class="mt-6 pt-6 border-t border-emerald-200">
      <!-- 结果头部 -->
      <div class="flex items-center gap-3 mb-4">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center"
          :class="checkResult.passed ? 'bg-green-100' : 'bg-red-100'"
        >
          <CheckCircleIcon v-if="checkResult.passed" class="w-6 h-6 text-green-600" />
          <XCircleIcon v-else class="w-6 h-6 text-red-600" />
        </div>
        <div>
          <h4 class="text-lg font-bold" :class="checkResult.passed ? 'text-green-700' : 'text-red-700'">
            {{ checkResult.passed ? '✅ 审核通过' : '❌ 审核不通过' }}
          </h4>
          <p class="text-sm text-gray-600">
            发现 {{ checkResult.issues?.length || 0 }} 个问题
          </p>
        </div>
      </div>

      <!-- 问题列表 -->
      <div v-if="checkResult.issues?.length > 0" class="space-y-2">
        <div
          v-for="(issue, index) in checkResult.issues"
          :key="index"
          class="flex items-start gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200"
        >
          <ExclamationTriangleIcon class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <span class="text-sm text-red-700">{{ issue.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  ArrowPathIcon,
  ArrowUpTrayIcon,
  CheckCircleIcon,
  ClipboardDocumentCheckIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from '@heroicons/vue/24/outline'

const emit = defineEmits(['submit', 'cancel'])

const fileInput = ref(null)
const workOrderContent = ref('')
const uploadedFileName = ref('')
const isDragging = ref(false)
const isSubmitting = ref(false)
const checkResult = ref(null)

const hasContent = computed(() => {
  return workOrderContent.value.trim().length > 0
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    readFile(file)
  }
}

const handleFileDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    readFile(file)
  }
}

const readFile = (file) => {
  uploadedFileName.value = file.name
  
  const reader = new FileReader()
  reader.onload = (e) => {
    workOrderContent.value = e.target?.result || ''
  }
  reader.readAsText(file)
}

const clearContent = () => {
  workOrderContent.value = ''
  uploadedFileName.value = ''
  checkResult.value = null
}

const handleSubmit = () => {
  if (!hasContent.value) return

  isSubmitting.value = true
  emit('submit', {
    content: workOrderContent.value,
    fileName: uploadedFileName.value
  })
}

const handleCancel = () => {
  emit('cancel')
}

const setCheckResult = (result) => {
  checkResult.value = result
  isSubmitting.value = false
}

const resetSubmitting = () => {
  isSubmitting.value = false
}

defineExpose({
  resetSubmitting,
  setCheckResult
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.upload-zone {
  min-height: 120px;
}
</style>
