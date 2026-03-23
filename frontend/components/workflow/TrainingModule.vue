<template>
  <div class="training-module bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl border-2 border-purple-200 p-6 shadow-lg animate-fade-in">
    <!-- 组件头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center border-2 border-purple-200">
        <AcademicCapIcon class="w-5 h-5 text-purple-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">员工培训系统</h3>
        <p class="text-sm text-gray-600">{{ currentPhaseDescription }}</p>
      </div>
    </div>

    <!-- 阶段 1: 主题输入 -->
    <div v-if="phase === 'input'" class="space-y-4">
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          培训主题
        </label>
        <input
          type="text"
          v-model="trainingTopic"
          placeholder="例如：轴承故障处置、隧道安全巡检、道岔故障应急"
          class="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 快捷主题 -->
      <div class="flex flex-wrap gap-2">
        <button
          v-for="topic in quickTopics"
          :key="topic"
          @click="trainingTopic = topic"
          class="px-3 py-1.5 text-sm rounded-full border-2 transition-all"
          :class="trainingTopic === topic 
            ? 'border-purple-400 bg-purple-100 text-purple-700' 
            : 'border-gray-200 text-gray-600 hover:border-purple-300'"
        >
          {{ topic }}
        </button>
      </div>

      <button
        @click="generateQuiz"
        :disabled="isLoading || !trainingTopic.trim()"
        class="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-indigo-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        <ArrowPathIcon v-if="isLoading" class="w-5 h-5 animate-spin"/>
        <AcademicCapIcon v-else class="w-5 h-5"/>
        <span>{{ isLoading ? '等待 Agent 响应...' : '开始培训' }}</span>
      </button>
    </div>

    <!-- 阶段 2: 试题作答 -->
    <div v-else-if="phase === 'quiz' && quiz" class="space-y-6">
      <!-- 试题标题 -->
      <div class="bg-white rounded-xl p-4 border border-purple-200">
        <h4 class="text-lg font-bold text-purple-700">{{ quiz.quiz_title }}</h4>
        <div class="flex items-center gap-4 mt-2 text-sm text-gray-600">
          <span>共 {{ quiz.total_questions }} 题</span>
          <span>已答 {{ answeredCount }} 题</span>
        </div>
      </div>

      <!-- 题目列表 -->
      <div class="space-y-4">
        <div
          v-for="(question, index) in quiz.questions"
          :key="question.id"
          class="bg-white rounded-xl p-5 border-2 transition-all"
          :class="userAnswers[question.id] ? 'border-purple-200' : 'border-gray-200'"
        >
          <!-- 题目 -->
          <div class="flex items-start gap-3 mb-4">
            <span class="flex-shrink-0 w-7 h-7 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold">
              {{ index + 1 }}
            </span>
            <p class="text-gray-800 font-medium leading-relaxed">{{ question.question }}</p>
          </div>

          <!-- 选项 -->
          <div class="space-y-2 ml-10">
            <label
              v-for="(optionText, optionKey) in question.options"
              :key="optionKey"
              class="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all"
              :class="userAnswers[question.id] === optionKey 
                ? 'bg-purple-100 border-2 border-purple-400' 
                : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'"
            >
              <input
                type="radio"
                :name="`question_${question.id}`"
                :value="optionKey"
                v-model="userAnswers[question.id]"
                class="w-4 h-4 text-purple-600 focus:ring-purple-500"
              />
              <span class="font-semibold text-gray-600">{{ optionKey }}.</span>
              <span class="text-gray-700">{{ optionText }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 提交按钮 -->
      <button
        @click="submitAnswers"
        :disabled="isLoading || answeredCount < quiz.total_questions"
        class="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-indigo-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        <ArrowPathIcon v-if="isLoading" class="w-5 h-5 animate-spin"/>
        <PaperAirplaneIcon v-else class="w-5 h-5"/>
        <span>{{ isLoading ? '批改中...' : '提交作业' }}</span>
      </button>
    </div>

    <!-- 阶段 3: 批改结果 -->
    <div v-else-if="phase === 'result' && gradeResult" class="space-y-6">
      <!-- 成绩卡片 -->
      <div class="bg-white rounded-xl p-6 border-2 border-purple-200 text-center">
        <div
          class="w-20 h-20 rounded-full mx-auto mb-4 flex items-center justify-center text-3xl font-bold"
          :class="gradeResult.score >= 60 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'"
        >
          {{ Math.round(gradeResult.score) }}
        </div>
        <h4 class="text-xl font-bold text-gray-800">
          {{ gradeResult.score >= 60 ? '🎉 恭喜通过！' : '📚 需要加强学习' }}
        </h4>
        <p class="text-gray-600 mt-2">
          正确 {{ gradeResult.correct_count }} / {{ gradeResult.total_count }} 题
        </p>
      </div>

      <!-- 详细结果 -->
      <div class="space-y-3">
        <div
          v-for="result in gradeResult.results"
          :key="result.question_id"
          class="bg-white rounded-xl p-4 border-2"
          :class="result.is_correct ? 'border-green-200' : 'border-red-200'"
        >
          <div class="flex items-start gap-3">
            <div
              class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
              :class="result.is_correct ? 'bg-green-100' : 'bg-red-100'"
            >
              <CheckIcon v-if="result.is_correct" class="w-4 h-4 text-green-600" />
              <XMarkIcon v-else class="w-4 h-4 text-red-600" />
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-700 font-medium">{{ result.question }}</p>
              <div class="mt-2 text-sm">
                <p>
                  <span class="text-gray-500">你的答案：</span>
                  <span :class="result.is_correct ? 'text-green-600' : 'text-red-600'">
                    {{ result.user_answer || '未作答' }}
                  </span>
                </p>
                <p v-if="!result.is_correct">
                  <span class="text-gray-500">正确答案：</span>
                  <span class="text-green-600 font-medium">{{ result.correct_answer }}</span>
                </p>
              </div>
              <p v-if="!result.is_correct && result.explanation" class="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded-lg">
                💡 {{ result.explanation }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-3">
        <button
          @click="getCourseware"
          :disabled="isLoading"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isLoading" class="w-5 h-5 animate-spin"/>
          <BookOpenIcon v-else class="w-5 h-5"/>
          <span>{{ isLoading ? '等待 Agent 响应...' : '获取培训课件' }}</span>
        </button>
        <button
          @click="restart"
          class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-all"
        >
          重新开始
        </button>
      </div>
    </div>

    <!-- 阶段 4: 培训课件 -->
    <div v-else-if="phase === 'courseware' && courseware" class="space-y-4">
      <div class="bg-white rounded-xl p-6 border-2 border-purple-200 max-h-96 overflow-y-auto">
        <div class="prose prose-sm max-w-none" v-html="renderMarkdown(courseware)"></div>
      </div>

      <button
        @click="restart"
        class="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center gap-2"
      >
        <ArrowPathIcon class="w-5 h-5"/>
        <span>开始新的培训</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import {
  AcademicCapIcon,
  ArrowPathIcon,
  BookOpenIcon,
  CheckIcon,
  PaperAirplaneIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const emit = defineEmits(['generate-quiz', 'submit-answers', 'get-courseware', 'cancel'])

const phase = ref('input') // input | quiz | result | courseware
const trainingTopic = ref('')
const quiz = ref(null)
const userAnswers = ref({})
const gradeResult = ref(null)
const courseware = ref(null)
const isLoading = ref(false)

const quickTopics = [
  '轴承故障处置',
  '道岔故障应急',
  '隧道安全规范',
  '车门故障处理',
  '制动系统检修'
]

const currentPhaseDescription = computed(() => {
  switch (phase.value) {
    case 'input': return '输入培训主题，系统将自动生成试题'
    case 'quiz': return '请认真作答以下试题'
    case 'result': return '查看您的答题结果'
    case 'courseware': return '学习培训课件'
    default: return ''
  }
})

const answeredCount = computed(() => {
  return Object.keys(userAnswers.value).length
})

const generateQuiz = () => {
  if (!trainingTopic.value.trim()) return
  isLoading.value = true
  emit('generate-quiz', { topic: trainingTopic.value })
}

const submitAnswers = () => {
  isLoading.value = true
  emit('submit-answers', { answers: { ...userAnswers.value } })
}

const getCourseware = () => {
  isLoading.value = true
  emit('get-courseware')
}

const restart = () => {
  phase.value = 'input'
  trainingTopic.value = ''
  quiz.value = null
  userAnswers.value = {}
  gradeResult.value = null
  courseware.value = null
  isLoading.value = false
}

const renderMarkdown = (content) => {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (error) {
    return content
  }
}

const setQuiz = (quizData) => {
  quiz.value = quizData
  userAnswers.value = {}
  phase.value = 'quiz'
  isLoading.value = false
}

const setGradeResult = (result) => {
  gradeResult.value = result
  phase.value = 'result'
  isLoading.value = false
}

const setCourseware = (content) => {
  courseware.value = content
  phase.value = 'courseware'
  isLoading.value = false
}

const resetLoading = () => {
  isLoading.value = false
}

defineExpose({
  setQuiz,
  setGradeResult,
  setCourseware,
  resetLoading,
  restart
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

.prose {
  color: #374151;
}

.prose h1, .prose h2, .prose h3 {
  color: #1f2937;
  font-weight: 700;
}

.prose code {
  background: #f3f4f6;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
}
</style>
