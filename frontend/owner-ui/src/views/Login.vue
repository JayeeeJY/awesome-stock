<template>
  <main class="login-page">
    <el-card class="login-card">
      <img src="/logo.svg" alt="Awesome Stock" width="48" height="48">
      <h1>{{ auth.initialized ? '登录本地账号' : '创建本地账号' }}</h1>
      <p>Awesome Stock · 你的个人投资工作区</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名"><el-input v-model="username" name="username" autocomplete="username" :disabled="busy" /></el-form-item>
        <el-form-item label="口令"><el-input v-model="password" type="password" name="password" :autocomplete="auth.initialized ? 'current-password' : 'new-password'" show-password :disabled="busy" /></el-form-item>
        <el-form-item v-if="!auth.initialized" label="确认口令"><el-input v-model="confirmation" type="password" autocomplete="new-password" show-password :disabled="busy" /></el-form-item>
        <p v-if="!auth.initialized">创建唯一的本地账号，口令需 12–128 个字符。</p>
        <el-button type="primary" native-type="submit" :loading="busy">{{ auth.initialized ? '登录' : '创建账号' }}</el-button>
      </el-form>
    </el-card>
  </main>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore(), router = useRouter()
const username = ref(''), password = ref(''), confirmation = ref(''), busy = ref(false), error = ref('')
async function submit() {
  if (busy.value) return
  error.value = ''
  if (!auth.initialized && password.value !== confirmation.value) { error.value = '两次口令不一致。'; return }
  busy.value = true
  try { await auth.login(username.value, password.value); password.value = ''; confirmation.value = ''; await router.replace('/portfolio/accounts') }
  catch (e) { error.value = e instanceof Error ? e.message : '登录失败' }
  finally { busy.value = false }
}
</script>
<style scoped>
.login-page{min-height:100dvh;display:grid;place-items:center;padding:24px}.login-card{width:min(440px,100%)}h1{font-size:26px;margin:18px 0 8px}p{color:var(--el-text-color-secondary);line-height:1.7}form{margin-top:22px}
</style>
