<template><el-config-provider :locale="zhCn"><main v-if="auth.bootstrapError" class="bootstrap-error"><AppDataState tone="error" title="工作区暂时无法载入" :description="auth.bootstrapError" action-label="重新加载" @action="reload" /></main><router-view v-else /></el-config-provider></template>
<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAuthStore } from '@/stores/auth'
import AppDataState from '@/components/Global/AppDataState.vue'
const auth = useAuthStore()
const reload = () => window.location.reload()
</script>
<style scoped>.bootstrap-error{max-width:640px;margin:15vh auto;padding:24px}</style>
