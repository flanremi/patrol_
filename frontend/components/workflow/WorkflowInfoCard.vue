<template>
  <div class="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
    <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
      <h3 class="m-0 text-sm font-semibold text-gray-900">
        <slot name="header"></slot>
      </h3>
    </div>
    <div class="p-4">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
// 通用信息卡片组件
// 使用 TailwindCSS 样式
</script>
