import { request, type Account, type Position } from './owner'
export interface Quote { id: string; revision: number; kind: 'quote'; symbol: string; currency: string; price: string; previous_close?:string|null; as_of: string; source: string; updated_at: string; archived: boolean }
export interface ValuedPosition extends Position {day_price_effect:string|null; quote: Quote | null; quote_status: 'missing' | 'stale' | 'current_snapshot'; market_value: string | null; unrealized_pnl: string | null }
export interface ValuedAccount extends Account { positions: ValuedPosition[]; estimated_assets: string | null; valuation_complete: boolean }
export interface BusinessRecord { id: string; revision: number; kind: string; title: string; symbol?: string; updated_at: string; archived: boolean; [key: string]: unknown }
export interface Action {id: string; title: string; symbol: string; source_id: string; source_revision: number; updated_at: string; due_on: string; priority: string; reason: string; next_step: string; href: string; status: string; feedback: BusinessRecord | null; snooze_due: boolean}
export interface BaseValuation {base_currency:string;evaluated_on:string;evaluated_market_dates:Record<string,string>;return_basis:string;accounts:{account_id:string;fx_status:string;fx_evidence:BusinessRecord|null;assets_value_usd:string|null;day_price_effect_usd:string|null;cash_usd:string|null;realized_at_current_fx_usd:string|null;unrealized_at_current_fx_usd:string|null;positions:{symbol:string;market_value_usd:string|null;total_return_at_current_fx_usd:string|null}[]}[]}
export interface CompanyLabel {name:string;source:string;retrieved_at:string;verification:string;id:string;revision:number}
export interface Workspace { base_valuation:BaseValuation; company_sources:Record<string,CompanyLabel>; daily_index: Array<{id:string;account_id:string}>; records: BusinessRecord[]; versions: BusinessRecord[]; accounts: ValuedAccount[]; actions: Action[]; token: string; ledger_fingerprint: string; price_fingerprint: string; baseline: BusinessRecord | null; changes: Array<{account_id: string; account_name: string; currency: string; status: string; cash_change: string|null; cost_change: string|null; quantities: Array<{symbol:string;change:string}>}> }
export const getWorkspace = () => request<Workspace>('/api/v1/owner/business')
export function operationCache() {
  const operations = new Map<string,{fingerprint:string;body:Record<string,unknown>}>()
  return {
    body(key: string, values: Record<string,unknown>) {
      const fingerprint = JSON.stringify(values), old = operations.get(key)
      if (old?.fingerprint === fingerprint) return old.body
      const body = {...values, operation_id: crypto.randomUUID()}
      operations.set(key,{fingerprint,body}); return body
    },
    clear() { operations.clear() },
  }
}
