export type SupportedLanguage = 'zh-CN' | 'en-US'

const routeTitleMap: Record<string, Partial<Record<SupportedLanguage, string>>> = {
  'Cockpit': { 'en-US': 'Cockpit' },
  'Today': { 'en-US': 'Today' },
  'Portfolio': { 'en-US': 'Portfolio' },
  'Research': { 'en-US': 'Research' },
  'Plan': { 'en-US': 'Plan' },
  'Academy': { 'en-US': 'Academy' },
  'Evolve': { 'en-US': 'Evolve' },
  '行动收件箱': { 'en-US': 'Action Inbox' },
  '健康趋势': { 'en-US': 'Health Trend' },
  '驾驶舱': { 'en-US': 'Cockpit' },
  'AI 智能工作台': { 'en-US': 'AI Intelligence Workspace' },
  '持仓总览': { 'en-US': 'Portfolio' },
  '交易流水': { 'en-US': 'Trades' },
  '账户管理': { 'en-US': 'Accounts' },
  '健康诊断': { 'en-US': 'Diagnosis' },
  '提醒中心': { 'en-US': 'Reminders' },
  '投资日记': { 'en-US': 'Journal' },
  '学院': { 'en-US': 'Academy' },
  '交易前检查': { 'en-US': 'Pre-trade Check' },
  '单股分析': { 'en-US': 'Single Analysis' },
  '个股研究': { 'en-US': 'Stock Research' },
  '分析历史': { 'en-US': 'Analysis History' },
  '研究档案': { 'en-US': 'Research Library' },
  '批量分析': { 'en-US': 'Batch Analysis' },
  '批量研究': { 'en-US': 'Batch Research' },
  '机会筛选': { 'en-US': 'Opportunity Screener' },
  '股票筛选': { 'en-US': 'Screening' },
  '设置': { 'en-US': 'Settings' },
  '通用设置': { 'en-US': 'General Settings' },
  '配置管理': { 'en-US': 'Config' },
  '缓存管理': { 'en-US': 'Cache' },
  '定时任务': { 'en-US': 'Scheduler' },
  '股票详情': { 'en-US': 'Stock Detail' },
  '登录': { 'en-US': 'Login' },
  '数据库管理': { 'en-US': 'Database' },
  '操作日志': { 'en-US': 'Operation Logs' },
  '系统日志': { 'en-US': 'System Logs' },
  '多数据源同步': { 'en-US': 'Data Sync' },
  '使用统计': { 'en-US': 'Usage' },
  '页面不存在': { 'en-US': 'Page Not Found' },
}

export function translateRouteTitle(title: string, language: SupportedLanguage): string {
  if (language === 'zh-CN') return title
  return routeTitleMap[title]?.[language] || title
}
