<template>
  <el-breadcrumb separator="/" class="breadcrumb">
    <el-breadcrumb-item
      v-for="item in breadcrumbList"
      :key="item.path"
      :to="item.path"
    >
      {{ item.title }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { translateRouteTitle } from '@/utils/uiLocale'

const route = useRoute()
const appStore = useAppStore()

const breadcrumbList = computed(() => {
  const matched = route.matched.filter(item => item.meta && item.meta.title)

  return matched.reduce<Array<{ path: string; title: string }>>((acc, item) => {
    const title = translateRouteTitle(item.meta.title as string, appStore.language)
    if (acc[acc.length - 1]?.title === title) {
      return acc
    }
    acc.push({
      path: item.path,
      title,
    })
    return acc
  }, [])
})
</script>

<style lang="scss" scoped>
.breadcrumb {
  font-size: 14px;
  :deep(.el-breadcrumb__inner),
  :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
    color: #dbeeff;
    font-weight: 600;
  }

  :deep(.el-breadcrumb__separator) {
    color: #5f7896;
  }

  :deep(.el-breadcrumb__item:not(:last-child) .el-breadcrumb__inner) {
    color: #89a2bf;
    font-weight: 500;
  }
}
</style>
