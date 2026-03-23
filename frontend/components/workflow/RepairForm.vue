<template>
  <div class="repair-form bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl border-2 border-orange-200 p-6 shadow-lg animate-fade-in">
    <!-- 表单头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center border-2 border-orange-200">
        <WrenchScrewdriverIcon class="w-5 h-5 text-orange-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">维修方案咨询</h3>
        <p class="text-sm text-gray-600">{{ message || '请填写缺陷信息以获取维修方案' }}</p>
      </div>
    </div>

    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- 缺陷描述 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>缺陷描述
        </label>
        <textarea
          v-model="formData.defect_description"
          rows="3"
          required
          placeholder="详细描述故障现象，例如：轴承运行时发出异常噪音，伴随轻微振动，温度比正常值高出15℃"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 缺陷位置 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>缺陷位置
        </label>
        <input
          type="text"
          v-model="formData.defect_location"
          required
          placeholder="例如：1号线0116车A转向架左侧一轴"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 紧急程度 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>紧急程度
        </label>
        <div class="flex gap-3">
          <label
            v-for="level in urgencyLevels"
            :key="level.value"
            class="flex-1 flex items-center gap-2 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
            :class="[
              formData.urgency_level === level.value
                ? `${level.selectedClass}`
                : 'border-gray-200 hover:border-gray-300'
            ]"
          >
            <input
              type="radio"
              v-model="formData.urgency_level"
              :value="level.value"
              class="w-4 h-4"
              :class="level.radioClass"
            />
            <span class="text-sm font-medium" :class="formData.urgency_level === level.value ? level.textClass : 'text-gray-700'">
              {{ level.icon }} {{ level.label }}
            </span>
          </label>
        </div>
      </div>

      <!-- 设备信息 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          设备信息
        </label>
        <input
          type="text"
          v-model="formData.equipment_info"
          placeholder="例如：SKF轴承，型号6208-2RS，已运行3年"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 补充信息 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          补充信息
        </label>
        <textarea
          v-model="formData.additional_info"
          rows="2"
          placeholder="其他相关信息，例如：上周例行检查时未发现异常"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 按钮组 -->
      <div class="flex items-center gap-3 pt-4">
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-orange-600 hover:to-amber-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
          <WrenchScrewdriverIcon v-else class="w-5 h-5"/>
          <span>{{ isSubmitting ? '咨询中...' : '获取方案' }}</span>
        </button>
        <button
          type="button"
          @click="handleCancel"
          :disabled="isSubmitting"
          class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-all duration-200 disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import {
  ArrowPathIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  message: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['submit', 'cancel'])

const urgencyLevels = [
  {
    value: 'urgent',
    label: '紧急',
    icon: '🔴',
    selectedClass: 'border-red-400 bg-red-50',
    textClass: 'text-red-700',
    radioClass: 'text-red-600 focus:ring-red-500'
  },
  {
    value: 'normal',
    label: '一般',
    icon: '🟡',
    selectedClass: 'border-yellow-400 bg-yellow-50',
    textClass: 'text-yellow-700',
    radioClass: 'text-yellow-600 focus:ring-yellow-500'
  },
  {
    value: 'deferred',
    label: '可延期',
    icon: '🟢',
    selectedClass: 'border-green-400 bg-green-50',
    textClass: 'text-green-700',
    radioClass: 'text-green-600 focus:ring-green-500'
  }
]

const formData = reactive({
  defect_description: '',
  defect_location: '',
  urgency_level: 'normal',
  equipment_info: '',
  additional_info: ''
})

const isSubmitting = ref(false)

const isFormValid = computed(() => {
  return formData.defect_description.trim() && 
         formData.defect_location.trim() && 
         formData.urgency_level
})

const handleSubmit = () => {
  if (!isFormValid.value) return

  isSubmitting.value = true
  emit('submit', { ...formData })
}

const handleCancel = () => {
  emit('cancel')
}

const resetSubmitting = () => {
  isSubmitting.value = false
}

defineExpose({
  resetSubmitting
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
</style>
