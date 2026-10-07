import type {BaseValuation} from '@/api/business'
// Compare the dates used by the server, independently of the browser timezone.
export function valuationIsCurrent(value:Pick<BaseValuation,'evaluated_on'|'evaluated_market_dates'>|null|undefined,now:number):boolean {
  if(!value||!value.evaluated_market_dates||value.evaluated_on!==new Date(now).toISOString().slice(0,10))return false
  const dates=value.evaluated_market_dates
  if(dates.UTC!==value.evaluated_on)return false
  return Object.entries(dates).every(([zone,day])=>{
    if(!['UTC','Asia/Shanghai','Asia/Hong_Kong'].includes(zone))return false
    const parts=new Intl.DateTimeFormat('en-US',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now))
    const part=(name:string)=>parts.find(p=>p.type===name)?.value
    return day===`${part('year')}-${part('month')}-${part('day')}`
  })
}
