// Display arithmetic only. Authoritative cash/cost/valuation remains on the Owner server.
// BigInt avoids precision loss when aggregating same-currency decimal strings.
function parts(value: string): [bigint, number] {
  // Decimal differences from the server can be represented as 0E-8.
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d{1,3}))?$/.exec(value)
  if (!match) throw new Error('Invalid decimal')
  const exponent = Number(match[4] || 0)
  if (Math.abs(exponent) > 100) throw new Error('Invalid decimal exponent')
  const fraction = match[3] || ''
  let n = BigInt(match[2] + fraction) * (match[1] ? -1n : 1n)
  const scale = fraction.length - exponent
  if (scale < 0) n *= 10n ** BigInt(-scale)
  return [n, Math.max(0, scale)]
}
function render(integer: bigint, scale: number) {
  const sign = integer < 0n ? '-' : '', digits = (integer < 0n ? -integer : integer).toString().padStart(scale + 1, '0')
  if (!scale) return sign + digits
  const result = sign + digits.slice(0,-scale) + '.' + digits.slice(-scale)
  return result.replace(/\.?0+$/, '') || '0'
}
export function sum(values: string[]) {
  const parsed = values.map(parts), scale = Math.max(0,...parsed.map(p=>p[1]))
  return render(parsed.reduce((total,[n,s])=>total+n*10n**BigInt(scale-s),0n),scale)
}
export function negate(value: string) { return value.startsWith('-') ? value.slice(1) : '-' + value }
export function compare(a: string, b: string) {
  const [x,s] = parts(a), [y,t] = parts(b), scale = Math.max(s,t)
  const d = x*10n**BigInt(scale-s)-y*10n**BigInt(scale-t)
  return d < 0n ? -1 : d > 0n ? 1 : 0
}
export function divide(a: string, b: string, precision = 8): string | null {
  const [x,s] = parts(a), [y,t] = parts(b)
  if (!y) return null
  return render(x*10n**BigInt(t+precision)/(y*10n**BigInt(s)),precision)
}
export function percent(a: string, b: string): string {
  const ratio = divide(a,b,6)
  if (ratio === null) return '—'
  const [n,s] = parts(ratio)
  return money(render(n*100n,s),2)+'%'
}
export function money(value: string | null | undefined, precision = 2) {
  if (value == null) return '—'
  let [n,s] = parts(value)
  if (s > precision) {
    const factor = 10n**BigInt(s-precision), negative = n < 0n
    n = ((negative ? -n : n) + factor/2n)/factor * (negative ? -1n : 1n); s = precision
  }
  let [integer,fraction=''] = render(n,s).split('.')
  integer = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return integer + (precision ? '.' + fraction.padEnd(precision,'0') : '')
}

export function multiply(a: string, b: string) {
  const [x,s] = parts(a), [y,t] = parts(b)
  return render(x*y,s+t)
}
