<template>
  <div class="settings-page">
    <section class="settings-hero">
      <div class="settings-hero-copy">
        <div class="settings-kicker">Awesome Stock Control Center</div>
        <h1 class="settings-title">外观设置</h1>
        <p class="settings-subtitle">沿用自用版的主题与侧栏布局。设置保存在当前浏览器，刷新后继续生效。</p>
      </div>
      <div class="settings-hero-stats">
        <article class="hero-stat"><span>主题外观</span><b>{{ modeLabel }}</b><small>全局界面颜色</small></article>
        <article class="hero-stat"><span>侧栏宽度</span><b>{{ app.sidebarWidth }}px</b><small>桌面布局</small></article>
        <article class="hero-stat"><span>当前配色</span><b>{{ app.theme === 'dark' ? '深色' : '浅色' }}</b><small>跟随系统时自动切换</small></article>
        <article class="hero-stat"><span>隐私模式</span><b>{{ app.privacyMode ? '已开启' : '已关闭' }}</b><small>驾驶舱金额显示</small></article>
      </div>
    </section>
    <div class="settings-layout">
      <aside class="settings-sidebar" aria-label="系统设置导航">
        <button type="button" class="settings-nav-item" @click="router.push('/settings/account')">账户与数据</button>
        <button type="button" class="settings-nav-item is-active" aria-current="page">外观</button>
        <button type="button" class="settings-nav-item" @click="router.push('/settings/connections')">数据与 AI 连接</button>
        <button type="button" class="settings-nav-item" @click="router.push('/settings/transfer')">导入与导出</button>
        <div class="settings-side-note"><strong>界面设置</strong><p>外观只影响当前浏览器，不修改账本、模型连接或其他设备。</p></div>
      </aside>
      <div class="settings-main">
        <section class="settings-panel">
          <div class="panel-title">主题外观</div>
          <p class="panel-subtitle">跟随系统会在系统明暗主题改变时同步切换。</p>
          <el-form label-position="top" @submit.prevent="save">
            <el-form-item label="主题模式">
              <el-radio-group v-model="draftMode" aria-label="主题模式">
                <el-radio value="light">浅色</el-radio>
                <el-radio value="dark">深色</el-radio>
                <el-radio value="auto">跟随系统</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="侧栏宽度">
              <div class="width-control"><el-slider v-model="draftWidth" :min="216" :max="280" :step="4" show-input aria-label="侧栏宽度"/><span>{{ draftWidth }}px</span></div>
            </el-form-item>
            <div class="privacy-card"><div><strong>隐私模式</strong><p>开启后，驾驶舱的金额和持仓数量会隐藏；主动显示金额后才能载入驾驶舱助手材料。</p></div><el-switch v-model="draftPrivacy" aria-label="隐私模式" /></div>
            <div class="panel-actions"><el-button type="primary" native-type="submit" :disabled="!dirty">保存外观设置</el-button><el-button :disabled="!dirty" @click="resetDraft">恢复已保存设置</el-button></div>
          </el-form>
          <p role="status" class="save-status">{{ notice }}</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElSlider, ElSwitch } from 'element-plus'
import { useAppStore } from '@/stores/app'
const router = useRouter(), app = useAppStore()
const draftMode = ref<'light' | 'dark' | 'auto'>(app.themeMode)
const draftWidth = ref(app.sidebarWidth)
const draftPrivacy = ref(app.privacyMode)
const notice = ref('')
const dirty = computed(() => draftMode.value !== app.themeMode || draftWidth.value !== app.sidebarWidth || draftPrivacy.value !== app.privacyMode)
const modeLabel = computed(() => ({light:'浅色',dark:'深色',auto:'跟随系统'})[app.themeMode])
function resetDraft() { draftMode.value = app.themeMode; draftWidth.value = app.sidebarWidth; draftPrivacy.value = app.privacyMode; notice.value = '' }
function save() { app.setThemeMode(draftMode.value); app.setSidebarWidth(draftWidth.value); app.setPrivacyMode(draftPrivacy.value); notice.value = '外观设置已保存。' }
</script>

<style scoped lang="scss">
.settings-page{padding:28px 32px 40px;display:flex;flex-direction:column;gap:22px}
.settings-hero{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:16px;padding:24px 26px;border-radius:24px;border:1px solid rgba(91,153,255,.14);background:radial-gradient(circle at top right,rgba(72,196,255,.16),transparent 32%),linear-gradient(135deg,rgba(10,27,54,.96),rgba(14,44,86,.92));box-shadow:0 20px 54px rgba(5,18,43,.24)}
.settings-kicker{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.08);color:#8fd3ff;font-size:11px;font-weight:700;letter-spacing:.18em;text-transform:uppercase}
.settings-title{margin:16px 0 10px;font-size:34px;line-height:1.08;color:#f3fbff}
.settings-subtitle{margin:0;max-width:720px;font-size:14px;line-height:1.7;color:rgba(216,232,255,.84)}
.settings-hero-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.hero-stat{padding:16px 18px;border-radius:18px;background:rgba(7,20,42,.42);border:1px solid rgba(109,178,255,.12);display:flex;flex-direction:column;gap:6px}
.hero-stat span{font-size:11px;letter-spacing:.12em;color:rgba(151,197,240,.75)}
.hero-stat b{font-size:20px;color:#f5fbff}
.hero-stat small{color:rgba(185,211,242,.72);font-size:12px}
.settings-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:18px}
.settings-sidebar,.settings-panel{border-radius:22px;border:1px solid var(--el-border-color-lighter);background:var(--el-bg-color-overlay);box-shadow:0 16px 44px rgba(17,32,62,.08)}
.settings-sidebar{padding:14px;display:flex;flex-direction:column;gap:10px;align-self:start;position:sticky;top:28px}
.settings-nav-item{width:100%;border:1px solid transparent;border-radius:16px;background:rgba(14,26,46,.03);padding:12px 14px;display:flex;align-items:center;font-size:14px;font-weight:700;color:var(--el-text-color-primary);cursor:pointer;text-align:left}
.settings-nav-item:hover{border-color:rgba(84,167,255,.16);background:rgba(84,167,255,.06)}
.settings-nav-item.is-active{border-color:rgba(84,167,255,.22);background:linear-gradient(135deg,rgba(84,167,255,.12),rgba(33,108,231,.08));color:var(--el-color-primary)}
.settings-side-note{margin-top:8px;padding:14px;border-radius:16px;background:rgba(84,167,255,.05);color:var(--el-text-color-regular)}
.settings-side-note strong{font-size:13px;color:var(--el-text-color-primary)}
.settings-side-note p{margin:6px 0 0;font-size:12px;line-height:1.65}
.settings-main{min-width:0}.settings-panel{padding:22px 24px}.panel-title{font-size:20px;font-weight:800;color:var(--el-text-color-primary)}.panel-subtitle{margin:6px 0 22px;font-size:13px;line-height:1.7;color:var(--el-text-color-secondary)}
.width-control{width:100%;display:flex;align-items:center;gap:12px}.width-control .el-slider{flex:1;min-width:0}.width-control span{min-width:48px;text-align:right;color:var(--el-text-color-secondary);font-variant-numeric:tabular-nums}
.privacy-card{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 18px;margin:4px 0 20px;border:1px solid var(--el-border-color-lighter);border-radius:16px;background:rgba(84,167,255,.05)}.privacy-card strong{font-size:14px;color:var(--el-text-color-primary)}.privacy-card p{margin:5px 0 0;font-size:12px;line-height:1.6;color:var(--el-text-color-secondary)}
.panel-actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:8px}.save-status{min-height:1.5em;margin:18px 0 0;color:var(--el-color-success)}
@media(max-width:900px){.settings-page{padding:14px 12px 26px}.settings-hero,.settings-layout{grid-template-columns:1fr}.settings-sidebar{position:static}.settings-hero-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.settings-title{font-size:27px}.settings-hero{padding:20px 16px}.settings-hero-stats{grid-template-columns:1fr}.settings-panel{padding:18px}.width-control{flex-wrap:wrap}.width-control .el-slider{flex-basis:100%}.privacy-card{align-items:flex-start}}
</style>
