<template>
  <div class="field-guidance bg-gradient-to-br from-teal-50 to-cyan-50 rounded-2xl border-2 border-teal-200 p-6 shadow-lg animate-fade-in">
    <!-- 表单头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-teal-100 flex items-center justify-center border-2 border-teal-200">
        <MapPinIcon class="w-5 h-5 text-teal-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">现场作业指导</h3>
        <p class="text-sm text-gray-600">{{ message || '支持语音、拍照、位置感知的智能指导' }}</p>
      </div>
    </div>

    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- 位置信息 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <MapPinIcon class="w-4 h-4 inline-block mr-1 text-teal-500"/>
          当前位置
        </label>
        <div class="flex gap-2">
          <input
            type="text"
            v-model="formData.location"
            placeholder="例如：1号线 K12+500 区段"
            class="flex-1 px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-teal-400 focus:ring-2 focus:ring-teal-100 transition-all text-gray-900 placeholder-gray-400"
          />
          <button
            type="button"
            @click="getLocation"
            :disabled="isGettingLocation"
            class="px-4 py-2.5 bg-teal-100 text-teal-700 rounded-xl hover:bg-teal-200 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <ArrowPathIcon v-if="isGettingLocation" class="w-4 h-4 animate-spin"/>
            <MapPinIcon v-else class="w-4 h-4"/>
            <span class="hidden sm:inline">{{ isGettingLocation ? '获取中' : '定位' }}</span>
          </button>
        </div>
        <p v-if="locationError" class="text-xs text-red-500 mt-1">{{ locationError }}</p>
      </div>

      <!-- 问题描述 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>问题描述
        </label>
        <div class="relative">
          <textarea
            v-model="formData.question"
            rows="3"
            required
            placeholder="描述您遇到的问题，例如：这个焊缝裂纹该用什么标准评判？"
            class="w-full px-4 py-2.5 pr-12 rounded-xl border-2 border-gray-200 focus:border-teal-400 focus:ring-2 focus:ring-teal-100 transition-all text-gray-900 placeholder-gray-400 resize-none"
          ></textarea>
          <!-- 语音输入按钮 -->
          <button
            type="button"
            @click="toggleVoiceInput"
            class="absolute right-3 top-3 w-8 h-8 rounded-full flex items-center justify-center transition-all"
            :class="isRecording ? 'bg-red-500 text-white animate-pulse' : 'bg-gray-100 text-gray-600 hover:bg-teal-100 hover:text-teal-600'"
            :title="isRecording ? '停止录音' : '语音输入'"
          >
            <MicrophoneIcon class="w-4 h-4"/>
          </button>
        </div>
        <p v-if="isRecording" class="text-xs text-red-500 mt-1 flex items-center gap-1">
          <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          正在录音... 点击麦克风按钮停止
        </p>
      </div>

      <!-- 图片上传 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <CameraIcon class="w-4 h-4 inline-block mr-1 text-teal-500"/>
          现场照片（可选）
        </label>
        <div class="flex flex-wrap gap-3">
          <!-- 已上传的图片预览 -->
          <div
            v-for="(image, index) in uploadedImages"
            :key="index"
            class="relative w-24 h-24 rounded-xl overflow-hidden border-2 border-teal-200 group"
          >
            <img :src="image.preview" alt="预览" class="w-full h-full object-cover"/>
            <button
              type="button"
              @click="removeImage(index)"
              class="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <XMarkIcon class="w-4 h-4"/>
            </button>
          </div>
          
          <!-- 上传按钮 -->
          <label
            v-if="uploadedImages.length < maxImages"
            class="w-24 h-24 rounded-xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center cursor-pointer hover:border-teal-400 hover:bg-teal-50 transition-all"
          >
            <CameraIcon class="w-6 h-6 text-gray-400 mb-1"/>
            <span class="text-xs text-gray-500">拍照/上传</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              class="hidden"
              @change="handleImageUpload"
            />
          </label>
        </div>
        <p class="text-xs text-gray-500 mt-2">最多上传 {{ maxImages }} 张图片，支持拍照或从相册选择</p>
      </div>

      <!-- 快捷问题标签 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          常见问题
        </label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tag in quickTags"
            :key="tag"
            type="button"
            @click="applyQuickTag(tag)"
            class="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700 transition-all"
          >
            {{ tag }}
          </button>
        </div>
      </div>

      <!-- 按钮组 -->
      <div class="flex items-center gap-3 pt-4">
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-teal-600 hover:to-cyan-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
          <PaperAirplaneIcon v-else class="w-5 h-5"/>
          <span>{{ isSubmitting ? '咨询中...' : '获取指导' }}</span>
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
  CameraIcon,
  MapPinIcon,
  MicrophoneIcon,
  PaperAirplaneIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  message: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['submit', 'cancel'])

// 最大图片数量
const maxImages = 3

// 快捷问题标签
const quickTags = [
  '焊缝裂纹标准',
  '轮对磨耗限度',
  '轴承温度异常',
  '制动系统故障',
  '电气设备检查'
]

// 表单数据
const formData = reactive({
  question: '',
  location: '',
})

// 上传的图片
const uploadedImages = ref([])

// 状态
const isSubmitting = ref(false)
const isRecording = ref(false)
const isGettingLocation = ref(false)
const locationError = ref('')

// 语音识别相关
let recognition = null

// 表单验证
const isFormValid = computed(() => {
  return formData.question.trim()
})

// 处理图片上传
const handleImageUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  
  if (uploadedImages.value.length >= maxImages) {
    alert(`最多只能上传 ${maxImages} 张图片`)
    return
  }
  
  // 创建预览
  const preview = URL.createObjectURL(file)
  
  // 转换为 base64
  const base64 = await fileToBase64(file)
  
  uploadedImages.value.push({
    file,
    preview,
    base64
  })
  
  // 清空 input
  event.target.value = ''
}

// 文件转 base64
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onload = () => {
      // 移除 data:image/xxx;base64, 前缀
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
  })
}

// 移除图片
const removeImage = (index) => {
  const image = uploadedImages.value[index]
  URL.revokeObjectURL(image.preview)
  uploadedImages.value.splice(index, 1)
}

// 获取位置
const getLocation = async () => {
  if (!navigator.geolocation) {
    locationError.value = '您的浏览器不支持地理定位'
    return
  }
  
  isGettingLocation.value = true
  locationError.value = ''
  
  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      })
    })
    
    const { latitude, longitude } = position.coords
    // 实际项目中可以调用逆地理编码 API 获取地址
    // 这里简单显示坐标
    formData.location = `纬度: ${latitude.toFixed(6)}, 经度: ${longitude.toFixed(6)}`
  } catch (error) {
    console.error('获取位置失败:', error)
    switch (error.code) {
      case 1:
        locationError.value = '位置权限被拒绝，请在浏览器设置中允许'
        break
      case 2:
        locationError.value = '无法获取位置信息'
        break
      case 3:
        locationError.value = '获取位置超时'
        break
      default:
        locationError.value = '获取位置失败'
    }
  } finally {
    isGettingLocation.value = false
  }
}

// 切换语音输入
const toggleVoiceInput = () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

// 开始录音
const startRecording = () => {
  // 检查浏览器支持
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    alert('您的浏览器不支持语音识别，请使用 Chrome 或 Edge 浏览器')
    return
  }
  
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true
  
  recognition.onresult = (event) => {
    let transcript = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript
    }
    formData.question = transcript
  }
  
  recognition.onerror = (event) => {
    console.error('语音识别错误:', event.error)
    isRecording.value = false
    if (event.error === 'not-allowed') {
      alert('请允许麦克风权限')
    }
  }
  
  recognition.onend = () => {
    isRecording.value = false
  }
  
  recognition.start()
  isRecording.value = true
}

// 停止录音
const stopRecording = () => {
  if (recognition) {
    recognition.stop()
    recognition = null
  }
  isRecording.value = false
}

// 应用快捷标签
const applyQuickTag = (tag) => {
  formData.question = `${tag}：`
}

// 提交表单
const handleSubmit = () => {
  if (!isFormValid.value) return
  
  isSubmitting.value = true
  
  // 构建提交数据
  const submitData = {
    question: formData.question,
    location: formData.location,
    image_base64: uploadedImages.value.length > 0 ? uploadedImages.value[0].base64 : null,
    images: uploadedImages.value.map(img => img.base64)
  }
  
  emit('submit', submitData)
}

// 取消
const handleCancel = () => {
  emit('cancel')
}

// 重置提交状态
const resetSubmitting = () => {
  isSubmitting.value = false
}

// 暴露方法
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
