<template>
  <section class="fx-panel">
    <el-button @click="open">汇率依据</el-button>
    <el-dialog v-model="visible" title="汇率依据" width="min(560px, 96vw)" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" :before-close="close">
      <p>记录 1 单位原币兑换的美元金额。仅用于估值，不会修改成交或自动请求行情。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" />
      <el-form label-position="top" :disabled="saving || loading">
        <el-form-item label="原币"><el-select :model-value="currency" aria-label="汇率原币" @change="changeCurrency"><el-option v-for="c in ['HKD','CNY','JPY','EUR','GBP']" :key="c" :value="c" :label="c" /></el-select></el-form-item>
        <el-form-item label="每单位原币兑换 USD"><el-input v-model="form.rate" aria-label="兑换美元汇率" inputmode="decimal" /></el-form-item>
        <el-form-item label="汇率日期（UTC）"><el-input v-model="form.as_of" aria-label="汇率日期" type="date" /></el-form-item>
        <el-form-item label="有效至（UTC，含当天）"><el-input v-model="form.expires_on" aria-label="汇率有效至" type="date" /></el-form-item>
        <el-form-item label="来源"><el-input v-model="form.source" aria-label="汇率来源" maxlength="300" placeholder="机构、报价记录或可核对的网址" /></el-form-item>
      </el-form>
      <p v-if="revision">当前版本 {{ revision }}；保存后保留旧版本。</p>
      <details v-if="versions.length"><summary>历史汇率记录</summary><p v-for="v in versions.filter(v=>v.currency===currency)" :key="v.revision">v{{ v.revision }} · {{ v.rate }} USD · {{ v.as_of }} 至 {{ v.expires_on }} · {{ v.source }}</p></details>
      <template #footer><el-button :disabled="saving" @click="close">关闭</el-button><el-button type="primary" :loading="saving" :disabled="loading || !ready" @click="save">保存汇率</el-button></template>
    </el-dialog>
  </section>
</template>
<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { request } from '@/api/owner'
import { operationCache } from '@/api/business'
interface Rate {currency:string;revision:number;rate:string;as_of:string;expires_on:string;source:string}
const emit=defineEmits<{saved:[]}>()
const visible=ref(false),saving=ref(false),loading=ref(false),error=ref(''),ready=ref(false),currency=ref('HKD'),revision=ref(0),rates=ref<Rate[]>([]),versions=ref<Rate[]>([])
const form=reactive({rate:'',as_of:'',expires_on:'',source:''}),ops=operationCache()
let baseline=''
function select(){const r=rates.value.find(r=>r.currency===currency.value);revision.value=r?.revision||0;Object.assign(form,r?{rate:r.rate,as_of:r.as_of,expires_on:r.expires_on,source:r.source}:{rate:'',as_of:new Date().toISOString().slice(0,10),expires_on:new Date().toISOString().slice(0,10),source:''});baseline=JSON.stringify(form);ops.clear()}
async function changeCurrency(value:string){if(JSON.stringify(form)!==baseline){try{await ElMessageBox.confirm('切换币种会丢弃未保存的汇率，是否继续？','切换币种',{confirmButtonText:'切换',cancelButtonText:'继续编辑'})}catch{return}}currency.value=value;select()}
const preventClose=(event:BeforeUnloadEvent)=>{if(saving.value||(visible.value&&JSON.stringify(form)!==baseline)){event.preventDefault();event.returnValue=''}}
onMounted(()=>window.addEventListener('beforeunload',preventClose))
onBeforeUnmount(()=>window.removeEventListener('beforeunload',preventClose))
async function open(){visible.value=true;loading.value=true;ready.value=false;error.value='';try{const data=await request<{rates:Rate[];versions:Rate[]}>('/api/v1/owner/fx-rates');rates.value=data.rates;versions.value=data.versions;select();ready.value=true}catch(e){error.value=String(e)}finally{loading.value=false}}
async function close(){if(saving.value)return false;if(visible.value&&JSON.stringify(form)!==baseline){try{await ElMessageBox.confirm('未保存的汇率将丢失，是否关闭？','放弃编辑',{confirmButtonText:'放弃',cancelButtonText:'继续编辑'})}catch{return false}}visible.value=false;return true}
onBeforeRouteLeave(close)
async function save(){if(saving.value||loading.value||!ready.value)return;error.value='';if(!/^\d{1,12}(?:\.\d{1,8})?$/.test(form.rate)||!/[1-9]/.test(form.rate)||!form.source.trim()||!form.as_of||form.as_of>new Date().toISOString().slice(0,10)||form.expires_on<form.as_of){error.value='请填写正数汇率、来源和有效日期；汇率日期不能晚于今天。';return}saving.value=true;try{await request('/api/v1/owner/fx-rates','POST',ops.body('rate',{currency:currency.value,revision:revision.value,...form,source:form.source.trim()}));baseline=JSON.stringify(form);visible.value=false;emit('saved')}catch(e){error.value=String(e)}finally{saving.value=false}}
</script>
<style scoped>
p{overflow-wrap:anywhere;color:var(--el-text-color-secondary);line-height:1.6}
</style>
