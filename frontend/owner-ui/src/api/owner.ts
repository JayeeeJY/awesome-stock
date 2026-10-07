// The Owner API is the only data source. Never import the self-use API or credentials.
export class OwnerError extends Error {
  constructor(message: string, public status: number, public code: string) { super(message) }
}
let refreshing: Promise<unknown> | undefined
function csrf() {
  const cookie = document.cookie.split('; ').find(value => value.startsWith('__Host-awesome_owner_csrf='))
  return cookie ? decodeURIComponent(cookie.substring(cookie.indexOf('=') + 1)) : ''
}
export async function request<T>(path: string, method = 'GET', body?: unknown, retry = true): Promise<T> {
  if (!/^\/api\/v1\/(owner|auth)\//.test(path)) throw new Error('不支持的请求路径')
  const response = await fetch(path, {
    method, credentials: 'same-origin',
    headers: method === 'GET' ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf(), 'X-Requested-With': 'awesome-owner' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json()
  if (response.status === 401 && retry && !path.includes('/auth/') && !path.endsWith('/password')) {
    try {
      refreshing ??= request('/api/v1/auth/refresh', 'POST', {}, false).finally(() => { refreshing = undefined })
      await refreshing
      return await request<T>(path, method, body, false)
    } catch (error) {
      if (error instanceof OwnerError && error.status === 401) window.dispatchEvent(new Event('owner-session-expired'))
      throw error
    }
  }
  if (!response.ok) throw new OwnerError(data.error?.message || '操作失败，请重试。', response.status, data.error?.code || 'unknown')
  return data
}
export interface Position { symbol: string; quantity: string; open_cost: string; realized_pnl: string }
export interface Account { id: string; broker: string; revision: number; name: string; currency: string; opening_cash: string; cost_method: 'avg' | 'fifo'; cash: string; holdings: Position[]; trades: Trade[] }
export interface Ledger { accounts: Account[]; cost_method: 'per_account'; cross_currency_total: null }
// Retain one operation ID for a failed/uncertain write. Never turn a retry into another account.
export function accountOperation(values: {name: string; currency: string; opening_cash: string; cost_method: 'avg' | 'fifo'; broker: string}) {
  return { ...values, id: crypto.randomUUID(), operation_id: crypto.randomUUID() }
}

export interface Trade { id: string; revision: number; account_id: string; symbol: string; side: string; quantity: string; price: string; fee: string; executed_at: string; event_order: number }
