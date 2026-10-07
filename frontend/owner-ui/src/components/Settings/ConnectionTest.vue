<template>
<div class="connection-test">
  <div class="test-heading"><div><h3>测试连接</h3><p>{{ !enabled?'先保存上方模型配置。':!configurationMatches?'配置已修改，请先保存，再测试新的连接。':'只发送下方一句测试文字，不读取持仓或研究材料。' }}</p></div><el-button type="primary" :loading="testing" :disabled="externalBusy||!enabled||!configurationMatches||dialog" @click="prepare">{{ tested?'重新测试连接':'测试连接' }}</el-button></div>
  <div class="test-prompt">{{ question }}</div>
  <el-alert v-if="failure" class="test-feedback" type="error" :closable="false" :title="failure" show-icon/>
  <div v-if="result" class="test-result" role="status"><strong>连接测试成功</strong><span>{{ result.provider }} / {{ result.model }} · {{ result.generated_at }}</span><p>模型回复：{{ result.draft }}</p><small>测试回复仅验证连接，不保存为研究材料。</small></div>
  <el-dialog v-model="dialog" title="确认测试模型连接" width="min(520px, calc(100vw - 32px))" :close-on-click-modal="false" :close-on-press-escape="!testing" :show-close="!testing" :before-close="closeDialog" append-to-body>
    <template v-if="preview"><p>服务：{{ preview.provider }} / {{ preview.model }}</p><p>本次仅发送：</p><blockquote>{{ preview.payload.question }}</blockquote><p>{{ preview.sends_to_cloud?'确认后向你配置的云端模型发送一次请求，费用计入你的服务商账户。':'确认后向你自己运行的 Ollama 发送一次请求，使用本机资源。' }}</p><p>不发送账户、持仓、研究材料或历史记录。</p></template>
    <template #footer><el-button :disabled="testing" @click="cancel">取消</el-button><el-button type="primary" :loading="testing" :disabled="!preview||testing" @click="generate">确认发送测试</el-button></template>
  </el-dialog>
</div>
</template>
<script setup lang="ts">
import {ref,watch,onBeforeUnmount} from 'vue'
import {request} from '@/api/owner'
const props=defineProps<{enabled:boolean;configurationMatches:boolean;externalBusy:boolean;provider:string;model:string;tested:boolean}>()
const emit=defineEmits<{busy:[value:boolean];success:[]}>()
type Preview={token:string;provider:string;model:string;sends_to_cloud:boolean;payload:{question:string}}
type Result={provider:string;model:string;draft:string;generated_at:string}
const question='请只回复：连接成功。',preview=ref<Preview|null>(null),result=ref<Result|null>(null),dialog=ref(false),testing=ref(false),failure=ref('')
function lock(value:boolean){testing.value=value;emit('busy',value)}
function cancel(){if(testing.value)return;preview.value=null;dialog.value=false;emit('busy',false)}
function closeDialog(done:()=>void){if(!testing.value){cancel();done()}}
watch(()=>[props.provider,props.model],()=>{if(!testing.value){result.value=null;failure.value='';cancel()}})
watch(()=>props.configurationMatches,value=>{if(!value&&!testing.value&&!props.externalBusy){result.value=null;failure.value='';cancel()}})
async function prepare(){if(testing.value||props.externalBusy||!props.enabled||!props.configurationMatches)return;failure.value='';result.value=null;lock(true);try{preview.value=await request<Preview>('/api/v1/owner/ai-preview','POST',{question,context:'',task:'connection_test'});dialog.value=true}catch(e){failure.value=e instanceof Error?e.message:'无法准备测试，请检查连接状态。'}finally{testing.value=false;emit('busy',dialog.value)}}
async function generate(){if(testing.value||!preview.value)return;lock(true);const token=preview.value.token;try{result.value=await request<Result>('/api/v1/owner/ai-generate','POST',{token,confirm:true},false);dialog.value=false;emit('success')}catch(e){dialog.value=false;failure.value=(e instanceof Error?e.message:'连接测试失败。')+' 没有自动重试；调整配置后可手动再次测试。'}finally{preview.value=null;lock(false)}}
onBeforeUnmount(()=>emit('busy',false))
</script>
<style scoped>
.connection-test{border-top:1px solid var(--el-border-color-lighter);margin-top:22px;padding-top:20px}.test-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.test-heading h3{font-size:18px;margin:0}.test-heading p{font-size:13px;color:var(--el-text-color-secondary);line-height:1.6;margin:8px 0}.test-prompt{padding:12px 16px;background:var(--el-fill-color-light);border-radius:10px;font-size:14px;margin-top:12px;overflow-wrap:anywhere}.test-feedback,.test-result{margin-top:16px}.test-result{display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid var(--el-color-success-light-5);border-radius:12px;font-size:14px;overflow-wrap:anywhere}.test-result strong{color:var(--el-color-success)}.test-result span,.test-result small{color:var(--el-text-color-secondary);font-size:12px}.test-result p{margin:0;white-space:pre-wrap}.el-dialog p{line-height:1.6;overflow-wrap:anywhere}blockquote{margin:12px 0;padding:12px;border-left:3px solid var(--el-color-primary);background:var(--el-fill-color-light)}@media(max-width:600px){.test-heading{align-items:flex-start;flex-direction:column}.test-heading .el-button{align-self:stretch}}
</style>
