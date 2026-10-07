export type Reference={id:string;revision:number}
export type Decision=Reference&{title:string;symbol:string;content:string;support:string;counter_case:string;invalidation:string;risk_limit:string;review_on:string}
export type Evidence={decision:Decision;research:(Reference&{title:string;content:string})|null;trades:Array<{id:string;revision:number;account_name:string;currency:string;executed_at:string;side:string;quantity:string;price:string;fee:string}>}

export type CoachEvidence=Omit<Evidence,'decision'>&{decision:Decision|null}
