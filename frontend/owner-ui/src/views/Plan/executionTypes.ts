import type {Trade} from '@/api/owner'
export type Execution={id:string;revision:number;plan_id:string;plan_revision:number;step_index:number;step_text:string;trade:Trade&{account_name:string;currency:string};note:string;archived:boolean;trade_changed:boolean;amount:string}
