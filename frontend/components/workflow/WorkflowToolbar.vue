<template>
  <!-- 浮动工具栏 -->
  <div class="absolute bottom-3 h-7 items-center left-2 z-20 flex gap-px bg-white rounded-lg border shadow px-1">
    <!-- 锁定/解锁 -->
    <WorkflowNavButton
      @click="$emit('toggle-lock')"
      :primary="isLocked"
      title="锁定/解锁画布"
    >
      <template #icon>
        <LockClosedIcon v-if="isLocked"
                        class="w-3 h-3"/>
        <LockOpenIcon v-else
                      class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 分隔线 -->
    <div class="h-5 mx-2 w-px bg-slate-300"></div>

    <!-- 自动布局 -->
    <WorkflowNavButton
      @click="$emit('auto-layout')"
      title="自动布局"
    >
      <template #icon>
        <ArrowPathIcon class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 适应视图 -->
    <WorkflowNavButton
      @click="$emit('fit-view')"
      title="适应视图"
    >
      <template #icon>
        <MagnifyingGlassIcon class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 重置视图 -->
    <WorkflowNavButton
      @click="$emit('reset-view')"
      title="重置视图"
    >
      <template #icon>
        <HomeIcon class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 分隔线 -->
    <div class="h-5 mx-2 w-px bg-slate-300 "></div>

    <!-- 放大 -->
    <WorkflowNavButton
      @click="$emit('zoom-in')"
      title="放大"
    >
      <template #icon>
        <PlusIcon class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 缩放显示 -->
    <div class="flex items-center justify-center px-3 py-1">
      <span class="text-xs font-medium text-slate-600">{{Math.round(zoomLevel * 100)}}%</span>
    </div>

    <!-- 缩小 -->
    <WorkflowNavButton
      @click="$emit('zoom-out')"
      title="缩小"
    >
      <template #icon>
        <MinusIcon class="w-3 h-3"/>
      </template>
    </WorkflowNavButton>

    <!-- 分隔线 -->
    <div class="h-5 mx-2 w-px bg-slate-300 "></div>

    <!-- 切换小地图 -->
    <WorkflowNavButton
      @click="$emit('toggle-minimap')"
      :primary="showMinimap"
      title="切换小地图"
    >
      <template #icon>
        <svg class="w-3 h-3"
             fill="none"
             stroke="currentColor"
             viewBox="0 0 24 24">
          <path stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
      </template>
    </WorkflowNavButton>
  </div>
</template>

<script setup>
import WorkflowNavButton from './WorkflowNavButton.vue'
import {
  ArrowPathIcon,
  HomeIcon,
  LockClosedIcon,
  LockOpenIcon,
  MagnifyingGlassIcon,
  MinusIcon,
  PlusIcon,
} from '@heroicons/vue/24/outline'

defineProps({
  showMinimap: {
    type: Boolean,
    default: true,
  },
  zoomLevel: {
    type: Number,
    default: 1,
  },
  isLocked: {
    type: Boolean,
    default: false,
  },
})

defineEmits([
  'auto-layout',
  'fit-view',
  'reset-view',
  'zoom-in',
  'zoom-out',
  'toggle-minimap',
  'toggle-lock',
])
</script>

<style scoped>
/* 工具栏悬停时的微妙阴影效果 */
.fixed:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>
