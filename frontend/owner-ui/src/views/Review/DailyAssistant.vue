<template>
<el-dialog append-to-body :model-value="true" title="AI 日报汇总 · 可选" width="min(760px,96vw)" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="!busy" :before-close="close">
<p>使用你在设置中配置的模型。云端调用由你的服务账户计费；预览不会发送，定时日报不会调用模型。原始日报保持不变。</p>
<el-alert v-if="error" :title="error" type="error" :closable="false"/>
<el-form label-position="top"><el-form-item label="日报汇总问题"><el-input v-model="question" type="textarea" :disabled="busy" maxlength="4000"/></el-form-item><el-form-item label="日报待发送材料"><el-input v-model="context" type="textarea" :rows="8" :disabled="busy" maxlength="20000"/></el-form-item></el-form>
<ContextExcerpt :source="sourceMaterial" :label="'固定日报 '+brief.id" :disabled="busy" :accept="acceptExcerpt" @dirty="value=>{if(value)touched=true}"/>
<el-button :disabled="busy" @click="prepare">预览日报发送内容</el-button>
<section v-if="preview"><h3>确认本次发送</h3><p>{{ preview.provider }} / {{ preview.model }} · {{ preview.sends_to_cloud?'发送到你的云端服务':'使用本地 Ollama' }}</p><pre>{{ JSON.stringify(preview.payload,null,2) }}</pre><el-button :disabled="busy" @click="generate">确认发送并汇总日报</el-button></section>
<section v-if="result"><h3>AI 草稿 · 未核验</h3><pre>{{ result.draft }}</pre><el-button :disabled="busy||saved" @click="save">{{ saved?'已保存日报草稿':'保存未核验日报草稿' }}</el-button></section>
<h3>此日报已保存的 AI 草稿</h3><p v-if="!history.length">尚无已保存草稿。</p><article v-for="draft in history" :key="draft.id"><p>{{ draft.provider }} / {{ draft.model }} · {{ draft.generated_at }} · 未核验</p><pre>{{ draft.draft }}</pre><details><summary>查看实际发送材料</summary><pre>{{ JSON.stringify(draft.sent_context,null,2) }}</pre></details></article>
<template #footer><el-button :disabled="busy" @click="close">关闭日报助手</el-button></template>
</el-dialog>
</template>
<script setup lang="ts">
import ContextExcerpt from '@/components/Research/ContextExcerpt.vue'
import {ref,watch,onBeforeUnmount} from 'vue'
import {ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
const props=defineProps<{brief:{id:string;[key:string]:unknown};accountId:string}>(),emit=defineEmits<{close:[]}>()
type Preview={token:string;provider:string;model:string;sends_to_cloud:boolean;payload:unknown}
type Draft={id:string;brief_id:string;draft:string;provider:string;model:string;generated_at:string;sent_context:unknown}
const sourceMaterial=JSON.stringify(props.brief,null,2)
async function acceptExcerpt(value:string){if(context.value!==sourceMaterial){try{await ElMessageBox.confirm('替换已编辑的日报材料？','替换材料',{confirmButtonText:'替换',cancelButtonText:'保留'})}catch{return false}}context.value=value;return true}
const question=ref('请仅依据这份固定日报，分别概括事实、纪律信号、缺失证据与复盘问题；不要提供买卖指令。'),context=ref(sourceMaterial),busy=ref(false),error=ref(''),preview=ref<Preview|null>(null),result=ref<{draft:string}|null>(null),history=ref<Draft[]>([]),saved=ref(false),touched=ref(false),ops=operationCache();let receipt='',id=''
watch([question,context],()=>{preview.value=null;touched.value=true})
async function reload(){const h=await request<{records:Draft[]}>('/api/v1/owner/daily-history','POST',{account_id:props.accountId});history.value=h.records.filter(r=>r.brief_id===props.brief.id&&r.draft)}
async function prepare(){if(busy.value)return;busy.value=true;error.value='';preview.value=null;try{if(context.value.length>20000)throw Error('材料超过20000字，请选取所需内容后再预览。');preview.value=await request('/api/v1/owner/ai-preview','POST',{task:'review',question:question.value,context:context.value});touched.value=true}catch(e){error.value=e instanceof Error?e.message:'预览失败'}finally{busy.value=false}}
async function generate(){if(busy.value||!preview.value)return;if(result.value&&!saved.value){try{await ElMessageBox.confirm('重新生成将替换未保存草稿，并发起一次新的模型请求。','重新汇总',{confirmButtonText:'重新生成',cancelButtonText:'保留草稿'})}catch{return}}busy.value=true;error.value='';const token=preview.value.token;preview.value=null;try{result.value=await request('/api/v1/owner/ai-generate','POST',{token,confirm:true},false);receipt=token;id=crypto.randomUUID();saved.value=false;ops.clear()}catch(e){error.value=(e instanceof Error?e.message:'汇总失败')+'。没有自动重试；再次确认发送可能产生新费用。'}finally{busy.value=false}}
async function save(){if(busy.value||!result.value||saved.value)return;busy.value=true;error.value='';try{await request('/api/v1/owner/daily-ai-draft','POST',ops.body('save',{id,brief_id:props.brief.id,token:receipt}));saved.value=true;touched.value=false;await reload()}catch(e){error.value=e instanceof Error?e.message:'保存失败，可重试保存'}finally{busy.value=false}}
async function close(){if(busy.value)return false;if(touched.value||result.value&&!saved.value){try{await ElMessageBox.confirm('关闭会清除编辑内容、发送预览及未保存草稿。','关闭日报助手',{confirmButtonText:'关闭',cancelButtonText:'继续编辑'})}catch{return false}}emit('close');return true}
const unload=(e:BeforeUnloadEvent)=>{if(busy.value||touched.value||result.value&&!saved.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>window.removeEventListener('beforeunload',unload));reload().catch(e=>error.value=e instanceof Error?e.message:'读取失败');defineExpose({close})
</script>
<style scoped>pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}section,article{margin:20px 0;padding-top:12px;border-top:1px solid var(--el-border-color)}</style>
