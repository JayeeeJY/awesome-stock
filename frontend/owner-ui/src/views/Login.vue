<template>
  <main class="login-page">
    <ParticleBackground />
    <div class="login-container">
      <header ref="headerRef" class="login-header">
        <div class="brand-lockup">
          <div class="logo-wrap"><img class="logo-icon" src="/logo.svg" alt="Awesome Stock logo" /></div>
          <div class="wordmark"><span class="wordmark-main">Awesome</span><span class="wordmark-accent">Stock</span></div>
        </div>
        <p class="subtitle">Evolve Every Trade.</p>
      </header>
      <section ref="cardRef" class="login-card" aria-labelledby="login-title">
        <p class="edition-label">COMMUNITY · 本地工作台</p>
        <h1 id="login-title">{{ auth.initialized ? '登录本地账号' : '创建本地账号' }}</h1>
        <p class="account-note">{{ auth.initialized ? '欢迎回来，继续你的投资进化。' : '在自己的电脑上，开始记录、研究与复盘。' }}</p>
        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon role="alert" />
        <el-form label-position="top" size="large" @submit.prevent="submit">
          <el-form-item label="用户名"><el-input v-model="username" name="username" autocomplete="username" :disabled="busy" /></el-form-item>
          <el-form-item label="口令"><el-input v-model="password" type="password" name="password" :autocomplete="auth.initialized ? 'current-password' : 'new-password'" show-password :disabled="busy" /></el-form-item>
          <el-form-item v-if="!auth.initialized" label="确认口令"><el-input v-model="confirmation" type="password" autocomplete="new-password" show-password :disabled="busy" /></el-form-item>
          <p v-if="!auth.initialized" class="setup-note">创建唯一的本地账号，口令需 12–128 个字符。</p>
          <el-button class="login-btn" type="primary" native-type="submit" :loading="busy" :disabled="busy">{{ auth.initialized ? '登录' : '创建账号' }}</el-button>
        </el-form>
      </section>
      <footer ref="footerRef" class="login-footer">
        <p>© 2026 Evan · AGPL-3.0-only</p>
        <p class="powered-by">Personal AI Decision OS</p>
        <p class="disclaimer">记录依据，审慎决策。AI 内容需自行核对，投资有风险。</p>
      </footer>
    </div>
  </main>
</template>
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import ParticleBackground from '@/components/ParticleBackground.vue'
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

const headerRef = ref<HTMLElement>(), cardRef = ref<HTMLElement>(), footerRef = ref<HTMLElement>()
const entranceAnimations: Animation[] = []
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  for (const [element, y, duration, wait] of [[headerRef.value, -40, 900, 0], [cardRef.value, 30, 750, 500], [footerRef.value, 20, 600, 850]] as const) {
    if (element) entranceAnimations.push(element.animate([{ transform: `translateY(${y}px)`, opacity: 0 }, { transform: 'translateY(0)', opacity: 1 }], { duration, delay: wait, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'both' }))
  }
})
onUnmounted(() => entranceAnimations.forEach(animation => animation.cancel()))
</script>
<style lang="scss" scoped>
.login-page {
  min-height: 100dvh;
  background:
    radial-gradient(circle at 8% 12%, rgba(255, 255, 255, 0.14) 0 0.9px, transparent 1.8px),
    radial-gradient(circle at 19% 44%, rgba(255, 255, 255, 0.1) 0 0.8px, transparent 1.6px),
    radial-gradient(circle at 27% 8%, rgba(167, 139, 250, 0.14) 0 0.9px, transparent 1.8px),
    radial-gradient(circle at 34% 58%, rgba(255, 255, 255, 0.1) 0 0.8px, transparent 1.7px),
    radial-gradient(circle at 46% 34%, rgba(56, 189, 248, 0.12) 0 0.9px, transparent 1.8px),
    radial-gradient(circle at 58% 8%, rgba(255, 255, 255, 0.12) 0 0.8px, transparent 1.7px),
    radial-gradient(circle at 67% 48%, rgba(255, 255, 255, 0.1) 0 0.8px, transparent 1.6px),
    radial-gradient(circle at 79% 18%, rgba(167, 139, 250, 0.14) 0 0.9px, transparent 1.8px),
    radial-gradient(circle at 91% 52%, rgba(56, 189, 248, 0.12) 0 0.9px, transparent 1.8px),
    radial-gradient(circle at 86% 84%, rgba(255, 255, 255, 0.1) 0 0.8px, transparent 1.6px),
    radial-gradient(circle at 12% 18%, rgba(255, 255, 255, 0.12) 0 1px, transparent 1.8px),
    radial-gradient(circle at 24% 72%, rgba(255, 255, 255, 0.11) 0 1.2px, transparent 2px),
    radial-gradient(circle at 36% 28%, rgba(255, 255, 255, 0.08) 0 1px, transparent 2px),
    radial-gradient(circle at 52% 16%, rgba(255, 255, 255, 0.1) 0 1.1px, transparent 2px),
    radial-gradient(circle at 64% 62%, rgba(255, 255, 255, 0.12) 0 1.2px, transparent 2.2px),
    radial-gradient(circle at 76% 24%, rgba(255, 255, 255, 0.1) 0 1px, transparent 2px),
    radial-gradient(circle at 88% 74%, rgba(255, 255, 255, 0.13) 0 1.3px, transparent 2.3px),
    radial-gradient(circle at 14% 86%, rgba(167, 139, 250, 0.16) 0 1.2px, transparent 2.2px),
    radial-gradient(circle at 84% 10%, rgba(56, 189, 248, 0.16) 0 1.3px, transparent 2.3px),
    radial-gradient(circle at 18% 22%, rgba(56, 189, 248, 0.16), transparent 18%),
    radial-gradient(circle at 82% 14%, rgba(167, 139, 250, 0.18), transparent 20%),
    radial-gradient(circle at 50% 78%, rgba(59, 130, 246, 0.1), transparent 22%),
    radial-gradient(ellipse at 20% 50%, #1e1b4b 0%, #0f0a2a 42%, #080814 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
  overflow: hidden;

  &::before,
  &::after {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  &::before {
    background:
      radial-gradient(circle at 10% 30%, rgba(255, 255, 255, 0.18) 0 0.9px, transparent 1.8px),
      radial-gradient(circle at 22% 12%, rgba(255, 255, 255, 0.15) 0 1px, transparent 2px),
      radial-gradient(circle at 31% 82%, rgba(255, 255, 255, 0.14) 0 0.9px, transparent 2px),
      radial-gradient(circle at 44% 20%, rgba(255, 255, 255, 0.16) 0 1px, transparent 2px),
      radial-gradient(circle at 57% 70%, rgba(255, 255, 255, 0.14) 0 1px, transparent 2px),
      radial-gradient(circle at 69% 18%, rgba(255, 255, 255, 0.16) 0 1.1px, transparent 2px),
      radial-gradient(circle at 81% 54%, rgba(255, 255, 255, 0.15) 0 1px, transparent 2px),
      radial-gradient(circle at 92% 26%, rgba(255, 255, 255, 0.18) 0 1.1px, transparent 2.1px);
    opacity: 0.76;
    animation: starPulseA 8.5s ease-in-out infinite alternate;
  }

  &::after {
    background:
      radial-gradient(circle at 16% 64%, rgba(56, 189, 248, 0.18) 0 1px, transparent 2px),
      radial-gradient(circle at 38% 14%, rgba(167, 139, 250, 0.18) 0 1.1px, transparent 2.1px),
      radial-gradient(circle at 48% 44%, rgba(255, 255, 255, 0.12) 0 0.9px, transparent 2px),
      radial-gradient(circle at 62% 84%, rgba(56, 189, 248, 0.16) 0 1px, transparent 2px),
      radial-gradient(circle at 74% 34%, rgba(167, 139, 250, 0.16) 0 1px, transparent 2px),
      radial-gradient(circle at 86% 68%, rgba(255, 255, 255, 0.14) 0 0.9px, transparent 1.9px),
      radial-gradient(circle at 12% 10%, rgba(255, 255, 255, 0.14) 0 0.8px, transparent 1.6px),
      radial-gradient(circle at 92% 88%, rgba(167, 139, 250, 0.16) 0 1px, transparent 2px),
      radial-gradient(circle at 42% 90%, rgba(255, 255, 255, 0.1) 0 0.8px, transparent 1.6px);
    opacity: 0.7;
    animation: starPulseB 11s ease-in-out infinite;
  }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  color: white;

  .brand-lockup {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .logo-wrap {
    display: flex;
    justify-content: center;
    position: relative;
    width: 102px;
    height: 88px;
    margin-left: auto;
    margin-right: auto;
    align-items: center;
    isolation: isolate;

    &::before,
    &::after {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 999px;
      pointer-events: none;
    }

    &::before {
      inset: 8px 10px 10px;
      background:
        radial-gradient(circle at 50% 44%, rgba(56, 189, 248, 0.18), transparent 56%),
        radial-gradient(circle at 38% 34%, rgba(96, 132, 255, 0.12), transparent 42%);
      filter: blur(12px);
      animation: logoHaloPulse 7s ease-in-out infinite alternate;
    }

    &::after {
      background:
        radial-gradient(circle at 16% 28%, rgba(255, 255, 255, 0.7) 0 1.1px, transparent 2px),
        radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.56) 0 0.9px, transparent 1.8px),
        radial-gradient(circle at 88% 58%, rgba(167, 139, 250, 0.58) 0 1px, transparent 2px),
        radial-gradient(circle at 22% 82%, rgba(56, 189, 248, 0.52) 0 1px, transparent 2px),
        radial-gradient(circle at 62% 88%, rgba(255, 255, 255, 0.42) 0 0.9px, transparent 1.8px);
      opacity: 0.34;
      animation: logoDustOrbit 12s linear infinite;
    }
  }

  .logo-icon {
    width: 94px;
    height: 76px;
    filter: drop-shadow(0 0 12px rgba(86, 214, 255, 0.12))
      drop-shadow(0 10px 18px rgba(8, 20, 50, 0.26));
    position: relative;
    z-index: 1;
    animation: logoFloat 6.5s ease-in-out infinite;
  }

  .wordmark {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    line-height: 1;
    white-space: nowrap;
  }

  .wordmark-main,
  .wordmark-accent {
    font-size: clamp(28px, 7vw, 34px);
    font-weight: 700;
    letter-spacing: -0.045em;
  }

  .wordmark-main {
    color: #edf5ff;
  }

  .wordmark-accent {
    color: #3193ff;
  }

  .subtitle {
    font-size: 15px;
    color: rgba(216, 234, 255, 0.72);
    margin: 0 0 8px 0;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }
}

.login-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.02));
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 20px;
  padding: 36px 32px 28px;
  box-shadow:
    0 22px 54px rgba(0, 0, 0, 0.34),
    0 0 0 1px rgba(167, 139, 250, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
  position: relative;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.04),
      transparent 22%,
      transparent 100%
    );
    pointer-events: none;
  }

  :deep(.el-form-item__label) {
    color: rgba(255, 255, 255, 0.7);
    font-size: 13px;
    font-weight: 500;
  }

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.055);
    border: 1px solid rgba(255, 255, 255, 0.11);
    box-shadow: none;
    border-radius: 10px;

    &:hover {
      border-color: rgba(167, 139, 250, 0.5);
    }

    &.is-focus {
      border-color: #a78bfa;
      background: rgba(255, 255, 255, 0.075);
      box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
    }
  }

  :deep(.el-input__inner) {
    color: rgba(255, 255, 255, 0.9);

    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
  }

  :deep(.el-input__prefix-icon) {
    color: rgba(255, 255, 255, 0.4);
  }

  :deep(.el-checkbox__label) {
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
  }

  :deep(.el-checkbox__inner) {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.3);
  }

  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
}

.auth-mode-switch {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 22px;
  padding: 5px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.08);

  button {
    height: 36px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: rgba(216, 234, 255, 0.62);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition:
      color 0.22s ease,
      background 0.22s ease,
      box-shadow 0.22s ease;

    &.active {
      color: #f8fbff;
      background: linear-gradient(135deg, rgba(49, 147, 255, 0.44), rgba(109, 40, 217, 0.4));
      box-shadow: 0 10px 24px rgba(49, 147, 255, 0.16);
    }
  }
}

.auth-note {
  position: relative;
  z-index: 1;
  margin: 6px 0 0;
  color: rgba(216, 234, 255, 0.5);
  font-size: 12px;
  text-align: center;

  button {
    padding: 0;
    border: 0;
    background: transparent;
    color: #7dd3fc;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }
}

.login-btn {
  width: 100%;
  height: 48px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 42%),
    linear-gradient(135deg, #6d28d9 0%, #4f46e5 52%, #22a7f0 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1.2px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition:
    transform 0.24s ease,
    box-shadow 0.24s ease,
    border-color 0.24s ease;
  box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4);
  text-shadow: 0 1px 10px rgba(15, 23, 42, 0.3);

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      115deg,
      transparent 10%,
      rgba(255, 255, 255, 0.24) 32%,
      transparent 52%
    );
    opacity: 0;
    transform: translateX(-120%);
    transition:
      opacity 0.22s ease,
      transform 0.65s ease;
  }

  &::after {
    content: '';
    position: absolute;
    inset: auto 10% -18px;
    height: 28px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(79, 70, 229, 0.34), transparent 72%);
    filter: blur(16px);
    opacity: 0.78;
    pointer-events: none;
  }

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.22);
    box-shadow: 0 10px 32px rgba(91, 33, 182, 0.48);

    &::before {
      opacity: 1;
      transform: translateX(120%);
    }
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.7;
  }

  .btn-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
  }

  .dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: white;
    animation: bounce 0.9s ease-in-out infinite;

    &:nth-child(2) {
      animation-delay: 0.15s;
    }
    &:nth-child(3) {
      animation-delay: 0.3s;
    }
  }
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0.7);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes starPulseA {
  0% {
    opacity: 0.38;
    transform: scale(1) translateY(0);
  }
  45% {
    opacity: 0.8;
  }
  100% {
    opacity: 0.58;
    transform: scale(1.015) translateY(-4px);
  }
}

@keyframes starPulseB {
  0%,
  100% {
    opacity: 0.28;
    transform: translate3d(0, 0, 0);
  }
  35% {
    opacity: 0.62;
  }
  70% {
    opacity: 0.42;
    transform: translate3d(0, -6px, 0);
  }
}

@keyframes logoHaloPulse {
  0% {
    opacity: 0.42;
    transform: scale(0.96);
  }
  100% {
    opacity: 0.78;
    transform: scale(1.04);
  }
}

@keyframes logoDustOrbit {
  0% {
    transform: rotate(0deg) scale(1);
    opacity: 0.42;
  }
  50% {
    opacity: 0.72;
  }
  100% {
    transform: rotate(360deg) scale(1.02);
    opacity: 0.48;
  }
}

@keyframes logoFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(0, -4px, 0);
  }
}

.login-footer {
  text-align: center;
  margin-top: 30px;
  display: grid;
  gap: 6px;

  p {
    margin: 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.28);
  }

  .powered-by {
    font-size: 10px;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.44);
  }

  .disclaimer {
    max-width: 360px;
    margin: 2px auto 0;
    font-size: 10px;
    line-height: 1.55;
    color: rgba(255, 255, 255, 0.18);
  }
}

.login-page { box-sizing: border-box; }
.login-card h1 { margin: 8px 0 10px; font-size: 23px; color: #edf5ff; }
.edition-label { margin: 0; font-size: 10px; letter-spacing: 0.16em; color: #a5b4fc; }
.account-note, .setup-note { font-size: 12px; line-height: 1.7; color: #aebbd3; }
.account-note { margin-bottom: 24px; }
.setup-note { margin: 0 0 18px; }
.login-card :deep(.el-alert) { margin-bottom: 18px; }
.login-card :deep(.el-alert__title) { overflow-wrap: anywhere; }
.login-btn:focus-visible { outline: 3px solid #a78bfa; outline-offset: 4px; }
.login-footer p { color: #9ba9c3; }
.login-footer .disclaimer { color: #8d9bb5; }
@media (max-width: 480px) {
  .login-page { padding: 28px 20px; }
  .login-header { margin-bottom: 24px; }
  .login-card { padding: 28px 22px 24px; }
  .login-footer { margin-top: 24px; }
}
@media (prefers-reduced-motion: reduce) {
  .login-page::before, .login-page::after, .logo-icon,
  .logo-wrap::before, .logo-wrap::after { animation: none !important; }
  .login-btn, .login-btn::before { transition: none; }
  .login-btn:hover:not(:disabled) { transform: none; }
}
</style>
