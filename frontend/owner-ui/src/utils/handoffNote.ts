type Snapshot = {
  candidate?: Record<string, unknown>
  evidence?: Array<Record<string, unknown>>
  notice?: string
}

const metricNames: Record<string, string> = {
  revenue_growth: '营收增长 %',
  gross_margin: '毛利率 %',
  net_debt_ebitda: '净债务 / EBITDA',
  pe: '市盈率 P/E',
  pb: '市净率 P/B',
  other: '其他',
}
const directionNames: Record<string, string> = {
  strengthens: '支持判断',
  weakens: '削弱判断',
  neutral: '未标记 / 中性',
}
const value = (item: Record<string, unknown>, key: string) => String(item[key] ?? '缺失')

// Older handoffs stored the whole snapshot as JSON in the note body. Keep those
// immutable bytes in storage, but display their fields as readable text.
export function readableHandoffNote(id: string, content: string): string {
  if (!id.startsWith('handoff-') || !content.trimStart().startsWith('{')) return content
  let snapshot: Snapshot
  try {
    snapshot = JSON.parse(content) as Snapshot
  } catch {
    return content
  }
  const candidate = snapshot.candidate
  if (!candidate || typeof candidate !== 'object' || !Array.isArray(snapshot.evidence)) return content
  const evidence = snapshot.evidence
  const lines = [
    '候选交接快照 · 仅供继续研究，不是投资建议',
    `标的：${value(candidate, 'symbol')} · ${value(candidate, 'title')}`,
    `市场：${value(candidate, 'market')}`,
    `观察逻辑：${value(candidate, 'thesis')}`,
    `复核日期：${value(candidate, 'review_on')}`,
    `候选记录：${value(candidate, 'id')} · v${value(candidate, 'revision')}`,
    '',
    `证据快照（${evidence.length} 条；缺失、过期或未核验材料不视为有效证据）`,
  ]
  if (!evidence.length) lines.push('尚无已保存证据，请先补充来源与复核日期。')
  evidence.forEach((item, index) => {
    if (!item || typeof item !== 'object') return
    lines.push(
      `${index + 1}. ${value(item, 'title')} · ${metricNames[value(item, 'metric')] ?? value(item, 'metric')}：${value(item, 'value')}`,
      `   核验：${item.verification === 'verified' ? '人工已核验' : '未核验'} · 方向：${directionNames[value(item, 'direction')] ?? directionNames.neutral}`,
      `   来源：${value(item, 'source')} · 观察：${value(item, 'as_of')} · 截止：${value(item, 'expires_on')}`,
      `   证据记录：${value(item, 'id')} · v${value(item, 'revision')}`,
    )
  })
  lines.push('', snapshot.notice || '固定交接快照；后续更正不会改写此版本。')
  return lines.join('\n')
}
