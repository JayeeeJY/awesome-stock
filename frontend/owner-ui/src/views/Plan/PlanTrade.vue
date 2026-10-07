<template>
 <el-button v-if="!plan.archived" :loading="opening" @click="open">录入实际成交</el-button>
 <el-dialog v-model="dialog" title="录入实际成交并关联计划" width="min(620px,calc(100vw - 24px))" :close-on-click-modal="false" :before-close="close" :show-close="!busy" :close-on-press-escape="!busy">
  <el-alert title="仅记录你已经完成的成交，不会向券商下单。请勿重复录入账本中已有的成交。" type="info" :closable="false"/>
  <el-alert v-if="error" :title="error" type="error" :closable="false"/>
  <el-form label-position="top">
   <el-form-item label="成交账户"><el-select v-model="form.account_id" :disabled="busy||!!plan.target"><el-option v-for="a in accounts" :key="a.id" :value="a.id" :label="a.name+' · '+a.currency"/></el-select></el-form-item>
   <p>标的 {{ plan.symbol }} · 计划版本 v{{ planRevision }}</p>
   <el-form-item label="执行步骤"><el-select v-model="form.step_index" :disabled="busy"><el-option v-for="(text,index) in plan.steps" :key="index" :value="index" :label="`${index+1}. ${text}`"/></el-select></el-form-item>
   <el-form-item label="买卖方向"><el-select v-model="form.side" :disabled="busy||plan.plan_type!=='rebalance'"><el-option value="buy" label="买入"/><el-option value="sell" label="卖出"/></el-select></el-form-item>
   <el-form-item v-for="f in fields" :key="f.key" :label="f.label"><el-input v-model="form[f.key]" :type="f.key==='executed_at'?'datetime-local':f.key==='note'?'textarea':'text'" :disabled="busy"/></el-form-item>
  </el-form>
  <template #footer><el-button :disabled="busy" @click="close">取消</el-button><el-button type="primary" :loading="busy" @click="save">核对并录入成交</el-button></template>
 </el-dialog>
</template>
<script setup lang="ts">
import {ref,reactive,computed,onBeforeUnmount} from 'vue'
import {onBeforeRouteLeave} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
const props=defineProps<{plan:{id:string;revision:number;symbol:string;steps:string[];plan_type:string;archived:boolean;target?:{account_id:string}|null}}>(),emit=defineEmits<{changed:[]}>()
const dialog=ref(false),busy=ref(false),opening=ref(false),error=ref(''),accounts=ref<{id:string;name:string;currency:string}[]>([]),planRevision=ref(0),ops=operationCache()
const blank=()=>({account_id:'',step_index:0,side:'buy',quantity:'',price:'',fee:'0',executed_at:'',note:''}),form=reactive(blank())
const fields:{key:'quantity'|'price'|'fee'|'executed_at'|'note';label:string}[]=[{key:'quantity',label:'实际成交股数'},{key:'price',label:'实际成交价格'},{key:'fee',label:'成交费用'},{key:'executed_at',label:'实际成交时间（本地时间）'},{key:'note',label:'执行说明'}]
let baseline='',id='',tradeId='',alive=true
const dirty=computed(()=>dialog.value&&JSON.stringify(form)!==baseline)
async function open(){if(opening.value)return;opening.value=true;try{const w=await request<{accounts:typeof accounts.value}>('/api/v1/owner/plans');if(!alive)return;accounts.value=w.accounts;Object.assign(form,blank(),{account_id:props.plan.target?.account_id||'',side:props.plan.plan_type==='reduce'?'sell':'buy'});planRevision.value=props.plan.revision;id=crypto.randomUUID();tradeId=crypto.randomUUID();baseline=JSON.stringify(form);ops.clear();error.value='';dialog.value=true}catch(e){ElMessage.error(e instanceof Error?e.message:'读取账户失败')}finally{opening.value=false}}
async function canLeave(){if(busy.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('放弃未保存的实际成交？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'});return true}catch{return false}}
async function close(){if(await canLeave())dialog.value=false}
async function save(){if(busy.value)return;error.value='';const account=accounts.value.find(a=>a.id===form.account_id),when=new Date(form.executed_at);if(!account||!form.quantity.trim()||!form.price.trim()||!form.note.trim()||!form.executed_at||!Number.isFinite(when.getTime())){error.value='请填写账户、实际成交股数、价格、时间和执行说明。';return}
 busy.value=true;try{try{await ElMessageBox.confirm(`${account.name}（${account.currency}） · ${props.plan.symbol}\n${form.side==='buy'?'买入':'卖出'} ${form.quantity} 股 @ ${form.price}\n费用 ${form.fee} · ${when.toLocaleString()}\n确认这笔成交已实际发生，并写入账本及计划记录？`,'确认实际成交',{confirmButtonText:'确认录入并关联',cancelButtonText:'返回核对',closeOnClickModal:false})}catch{return}
 await request('/api/v1/owner/plan-trades','POST',ops.body('record',{id,trade_id:tradeId,plan_id:props.plan.id,plan_revision:planRevision.value,...form,quantity:form.quantity.trim(),price:form.price.trim(),fee:form.fee.trim(),note:form.note.trim(),executed_at:when.toISOString(),confirmed:true}));dialog.value=false;emit('changed');ElMessage.success('实际成交和计划记录已保存')
 }catch(e){error.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{busy.value=false}}
onBeforeRouteLeave(canLeave);const unload=(e:BeforeUnloadEvent)=>{if(dirty.value||busy.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>{alive=false;window.removeEventListener('beforeunload',unload)})
</script>
