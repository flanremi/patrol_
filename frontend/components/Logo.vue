<script setup
        lang="ts">

</script>

<template>
  <div class="relative  flex items-center justify-center">
    <svg viewBox="0 0 32 32"
         class="w-full h-full">
      <!-- 原子核 -->
      <circle cx="16"
              cy="16"
              r="3"
              fill="#2563eb"/>
      <!-- 原子轨道 - 三个轨道 -->
      <ellipse cx="16"
               cy="16"
               rx="12"
               ry="5"
               fill="none"
               stroke="#2563eb"
               stroke-width="1.5"
               opacity="0.8"
               transform="rotate(0 16 16)"/>
      <ellipse cx="16"
               cy="16"
               rx="12"
               ry="5"
               fill="none"
               stroke="#2563eb"
               stroke-width="1.5"
               opacity="0.8"
               transform="rotate(60 16 16)"/>
      <ellipse cx="16"
               cy="16"
               rx="12"
               ry="5"
               fill="none"
               stroke="#2563eb"
               stroke-width="1.5"
               opacity="0.8"
               transform="rotate(-60 16 16)"/>
      <!-- 电子 -->
      <circle cx="28"
              cy="16"
              r="1.5"
              fill="#2563eb"/>
      <circle cx="4"
              cy="16"
              r="1.5"
              fill="#2563eb"/>
      <circle cx="16"
              cy="4"
              r="1.5"
              fill="#2563eb"/>
      <circle cx="16"
              cy="28"
              r="1.5"
              fill="#2563eb"/>
      <circle cx="24.5"
              cy="7.5"
              r="1.5"
              fill="#2563eb"/>
      <circle cx="7.5"
              cy="24.5"
              r="1.5"
              fill="#2563eb"/>
    </svg>
  </div>
</template>
