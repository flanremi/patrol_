<template>
  <div class="planning-form bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl border-2 border-green-200 p-6 shadow-lg animate-fade-in">
    <!-- 表单头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center border-2 border-green-200">
        <CalendarDaysIcon class="w-5 h-5 text-green-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">巡检计划生成</h3>
        <p class="text-sm text-gray-600">{{ message || '请填写以下信息以生成巡检计划' }}</p>
      </div>
    </div>

    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- 计划类型 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>计划类型
        </label>
        <div class="flex gap-3">
          <label
            v-for="type in planTypes"
            :key="type.value"
            class="flex-1 flex items-center gap-2 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
            :class="formData.plan_type === type.value
              ? 'border-green-400 bg-green-50'
              : 'border-gray-200 hover:border-green-300'"
          >
            <input
              type="radio"
              v-model="formData.plan_type"
              :value="type.value"
              class="w-4 h-4 text-green-600 focus:ring-green-500"
            />
            <span class="text-sm font-medium text-gray-700">{{ type.label }}</span>
          </label>
        </div>
      </div>

      <!-- 计划时间范围 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>计划时间范围
        </label>
        <div class="grid grid-cols-2 gap-3">
          <input
            type="date"
            v-model="formData.start_date"
            required
            class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900"
          />
          <input
            type="date"
            v-model="formData.end_date"
            required
            class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900"
          />
        </div>
      </div>

      <!-- 历史缺陷分布 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          历史缺陷分布
        </label>
        <textarea
          v-model="formData.defect_history"
          rows="3"
          placeholder="例如：隧道区段：本月故障3次；道岔区域：本月故障2次"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 设备台账 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          设备台账
        </label>
        <textarea
          v-model="formData.equipment_list"
          rows="2"
          placeholder="例如：1号线全线设备，重点关注隧道区段和道岔"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 天窗时间 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          天窗时间
        </label>
        <input
          type="text"
          v-model="formData.window_time"
          placeholder="例如：每日 00:30-04:30"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 人员排班 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          人员排班
        </label>
        <textarea
          v-model="formData.staff_schedule"
          rows="2"
          placeholder="例如：巡检组A（周一、三、五）、巡检组B（周二、四、六）"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 特殊要求 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          特殊要求
        </label>
        <textarea
          v-model="formData.special_requirements"
          rows="2"
          placeholder="例如：周二优先安排隧道区段巡检"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-green-400 focus:ring-2 focus:ring-green-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
        ></textarea>
      </div>

      <!-- 按钮组 -->
      <div class="flex items-center gap-3 pt-4">
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-green-600 hover:to-emerald-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
          <CalendarDaysIcon v-else class="w-5 h-5"/>
          <span>{{ isSubmitting ? '等待 Agent 响应...' : '生成计划' }}</span>
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
  CalendarDaysIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  message: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['submit', 'cancel'])

const planTypes = [
  { value: 'weekly', label: '周度计划' },
  { value: 'monthly', label: '月度计划' }
]

const getDefaultDates = () => {
  const today = new Date()
  const nextWeek = new Date(today)
  nextWeek.setDate(today.getDate() + 7)
  
  return {
    start: today.toISOString().slice(0, 10),
    end: nextWeek.toISOString().slice(0, 10)
  }
}

const defaultDates = getDefaultDates()

const formData = reactive({
  plan_type: 'weekly',
  start_date: defaultDates.start,
  end_date: defaultDates.end,
  defect_history: '',
  equipment_list: '',
  window_time: '',
  staff_schedule: '',
  special_requirements: ''
})

const isSubmitting = ref(false)

const isFormValid = computed(() => {
  return formData.plan_type && formData.start_date && formData.end_date
})

const handleSubmit = () => {
  if (!isFormValid.value) return

  isSubmitting.value = true
  
  const submitData = {
    plan_type: formData.plan_type === 'weekly' ? '周度计划' : '月度计划',
    date_range: `${formData.start_date} - ${formData.end_date}`,
    defect_history: formData.defect_history,
    equipment_list: formData.equipment_list,
    window_time: formData.window_time,
    staff_schedule: formData.staff_schedule,
    special_requirements: formData.special_requirements
  }
  
  emit('submit', submitData)
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
