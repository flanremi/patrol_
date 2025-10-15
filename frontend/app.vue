<template>
  <div>
    <!-- 全局布局 -->
    <NuxtPage/>

    <!-- 全局通知 -->
    <div id="toast-container"
         class="fixed top-4 right-4 z-50"></div>
  </div>
</template>

<script setup>
// 全局样式和配置
useHead({
  htmlAttrs: {
    lang: 'zh-CN',
  },
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
    },
  ],
})
</script>

<style>
/* 全局样式重置 */
html {
  scroll-behavior: smooth;
  font-size: 18px;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #374151;
  background-color: #f9fafb;
  font-size: 18px;
}

/* 选择文本样式 */
::selection {
  background-color: #3b82f6;
  color: white;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 动画类 */
.animate-fade-in {
  animation: fadeIn 0.5s ease-in-out;
}

.animate-slide-up {
  animation: slideUp 0.3s ease-out;
}

/* 工具提示 */
.tooltip {
  @apply relative;
}

.tooltip::after {
  @apply absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 pointer-events-none transition-opacity;
  content: attr(data-tooltip);
}

.tooltip:hover::after {
  @apply opacity-100;
}

/* 响应式图片 */
img {
  max-width: 100%;
  height: auto;
}

/* 表单元素样式增强 */
.form-input {
  @apply block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors;
}

.form-input:disabled {
  @apply bg-gray-50 text-gray-500 cursor-not-allowed;
}

/* 按钮样式 */
.btn {
  @apply inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
}

.btn-secondary {
  @apply bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500;
}

.btn-success {
  @apply bg-green-600 text-white hover:bg-green-700 focus:ring-green-500;
}

.btn-warning {
  @apply bg-yellow-600 text-white hover:bg-yellow-700 focus:ring-yellow-500;
}

.btn-danger {
  @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
}

/* 卡片样式 */
.card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden;
}

.card-header {
  @apply px-6 py-4 border-b border-gray-200 bg-gray-50;
}

.card-body {
  @apply p-6;
}

.card-footer {
  @apply px-6 py-4 border-t border-gray-200 bg-gray-50;
}

/* 加载状态 */
.loading {
  @apply opacity-50 pointer-events-none;
}

.skeleton {
  @apply bg-gray-200 animate-pulse rounded;
}

/* 打字机效果 */
.typewriter {
  overflow: hidden;
  border-right: 2px solid #3b82f6;
  white-space: nowrap;
  animation: typing 2s steps(40, end), blink-caret 0.75s step-end infinite;
}

@keyframes typing {
  from {
    width: 0;
  }
  to {
    width: 100%;
  }
}

@keyframes blink-caret {
  from, to {
    border-color: transparent;
  }
  50% {
    border-color: #3b82f6;
  }
}
</style>
