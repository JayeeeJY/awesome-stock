import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { ElAlert, ElAvatar, ElBacktop, ElBreadcrumb, ElBreadcrumbItem, ElButton, ElCard, ElCol, ElDialog, ElDropdown, ElDropdownItem, ElDropdownMenu, ElForm, ElFormItem, ElIcon, ElInput, ElMenu, ElMenuItem, ElMessageBox, ElOption, ElPagination, ElPopconfirm, ElRadio, ElRadioGroup, ElRow, ElSelect, ElTable, ElTableColumn, ElTag, ElTooltip, ElLoading } from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/styles/index.scss'
import '@/styles/dark-theme.scss'
import App from './App.vue'
import { useAppStore } from './stores/app'
import Layout from './layouts/BasicLayout.vue'
const Accounts = () => import('./views/Portfolio/Accounts.vue')
const Cockpit = () => import('./views/Dashboard/index.vue')
const Overview = () => import('./views/Portfolio/Overview.vue')
const Cash = () => import('./views/Portfolio/Cash.vue')
const Trades = () => import('./views/Portfolio/Trades.vue')
import Login from './views/Login.vue'
import { useAuthStore } from './stores/auth'
import { useBusinessStore } from './stores/business'
const app = createApp(App), pinia = createPinia()
app.use(pinia)
useAppStore().initAppearance()
const router = createRouter({ history: createWebHistory(), scrollBehavior: (to, _from, saved) => saved || (to.hash ? { el: to.hash, top: 90 } : { left: 0, top: 0 }), routes: [
  { path: '/login', component: Login, meta: {title: '登录'} },
  { path: '/', component: Layout, children: [{path:'settings',redirect:'/settings/account'},{path:'settings/transfer',component:()=>import('./views/Settings/Transfer.vue'),meta:{title:'导入与导出'}},{path:'settings/account',component:()=>import('./views/Settings/Account.vue'),meta:{title:'账户与数据管理'}},{path:'settings/appearance',component:()=>import('./views/Settings/Appearance.vue'),meta:{title:'外观设置'}},{path:'settings/connections',component:()=>import('./views/Settings/Connections.vue'),meta:{title:'个人连接设置'}},{path:'academy',component:()=>import('./views/Academy/index.vue'),meta:{title:'学院'}},{path:'review/rules',component:()=>import('./views/Review/Trends.vue'),meta:{title:'规则与周期趋势'}},{path:'review/diagnosis',component:()=>import('./views/Review/Diagnosis.vue'),meta:{title:'组合诊断'}},{path:'review',component:()=>import('./views/Review/Reviews.vue'),meta:{title:'Evolve'}},{path:'plan',redirect:'/plan/allocation'},{path:'plan/allocation',component:()=>import('./views/Plan/Simulation.vue'),meta:{title:'资产配置'}},{path:'plan/pre-trade',component:()=>import('./views/Plan/Simulation.vue'),meta:{title:'交易前试算'}},{path:'plan/budget',component:()=>import('./views/Plan/Simulation.vue'),meta:{title:'分批预算'}},{path:'plan/build-up',component:()=>import('./views/Plan/Plans.vue'),meta:{title:'投资计划'}},{path:'research',component:()=>import('./views/Research/Workbench.vue'),meta:{title:'Research'}},{path:'research/batch',component:()=>import('./views/Research/Batch.vue'),meta:{title:'批量研究'}},{path:'research/screening',component:()=>import('./views/Research/Screening.vue'),meta:{title:'机会筛选'}},{path:'research/notes',component:()=>import('./views/Research/Documents.vue'),meta:{title:'研究笔记'}},{path:'decisions',component:()=>import('./views/Research/Documents.vue'),meta:{title:'投资判断'}},{path:'cockpit',component:Cockpit,meta:{title:'Cockpit'}},{path: 'portfolio', meta: {title: 'Portfolio'}, children: [{path:'',component:Overview,meta:{title:'Portfolio'}},{path:'cash',component:Cash,meta:{title:'资金流水'}},{path: 'accounts', component: Accounts, meta: {title: '账户管理'}},{path: 'trades', component: Trades, meta: {title: '交易流水'}}]}] },
  { path: '/:pathMatch(.*)*', component: () => import('./views/NotFound.vue'), meta: {title: '页面未找到'} },
] })
router.beforeEach(async to => {
  const auth = useAuthStore()
  if (!auth.checked) {
    try { await auth.check(); auth.bootstrapError = '' }
    catch { auth.bootstrapError = '无法连接本地服务，请确认服务仍在运行后重试。'; return true }
  }
  if (!auth.authenticated && to.path !== '/login') return '/login'
  if (to.path === '/') return '/portfolio/accounts'
})
router.afterEach((to, _from, failure) => { if (!failure) document.title = `${to.meta.title || 'Awesome Stock'} · Awesome Stock` })
let updatePromptOpen = false
router.onError(error => {
  if (!/Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(error.message) || updatePromptOpen) return
  updatePromptOpen = true
  ElMessageBox.confirm('页面资源已经更新，当前标签需要刷新才能继续导航。刷新会丢弃未保存的输入。', '需要刷新页面', {
    confirmButtonText: '刷新页面', cancelButtonText: '暂不刷新', type: 'warning',
  }).then(() => window.location.reload()).catch(() => {}).finally(() => { updatePromptOpen = false })
})
window.addEventListener('owner-session-expired', () => {
  const auth = useAuthStore(); auth.authenticated = false; auth.user = null; useBusinessStore().reset()
  router.push('/login')
})
for (const component of [ElAlert, ElAvatar, ElBacktop, ElBreadcrumb, ElBreadcrumbItem, ElButton, ElCard, ElCol, ElDialog, ElDropdown, ElDropdownItem, ElDropdownMenu, ElForm, ElFormItem, ElIcon, ElInput, ElMenu, ElMenuItem, ElOption, ElPagination, ElPopconfirm, ElRadio, ElRadioGroup, ElRow, ElSelect, ElTable, ElTableColumn, ElTag, ElTooltip]) app.component(component.name!, component)
app.directive('loading', ElLoading.directive)
app.use(router).mount('#app')
