<template>
  <section class="ask-conversation">
    <div class="chat-toolbar"><span>{{ turns.length ? '本次对话' : '直接提问，或继续讨论材料' }}</span><div><el-button v-if="route.path!=='/settings/connections'" :disabled="blocked" @click="settings">模型连接设置</el-button><el-button v-if="turns.length" :disabled="blocked" @click="newConversation">新对话</el-button></div></div>
    <div ref="thread" class="chat-thread" aria-live="polite" aria-label="Ask Awesome 对话记录">
      <div v-if="!turns.length" class="chat-welcome"><img src="/logo.svg" alt=""/><h2>想讨论什么？</h2><p>在下方输入你的问题。可以聊投资概念，也可以主动载入本页材料后一起核对。</p></div>
      <article v-for="turn in turns" :key="turn.id" class="chat-turn">
        <section class="chat-question"><small>你</small><p>{{ turn.question }}</p></section>
        <section class="chat-answer" :class="{'is-error':turn.error}"><small>Ask Awesome · {{ turn.answer ? 'AI 草稿，待核验' : turn.error ? '未完成' : '正在回答…' }}</small><p>{{ turn.answer || turn.error || '正在等待模型返回完整答案。' }}</p><template v-if="turn.answer"><div class="chat-meta">{{ turn.provider }} / {{ turn.model }}</div><details><summary>本次发送依据</summary><pre>{{ JSON.stringify(turn.payload,null,2) }}</pre></details><el-button @click="copy(turn.answer)">复制回答</el-button></template></section>
      </article>
    </div>
    <div class="chat-composer">
      <p v-if="error" role="alert" class="chat-error">{{ error }}</p>
      <details class="chat-material"><summary>{{ context ? '已附材料 · 可查看和编辑' : '添加材料（可选）' }}</summary><el-input v-model="context" aria-label="对话附加材料" type="textarea" :rows="3" maxlength="20000" :disabled="blocked" placeholder="粘贴需要核对的材料；不填也能直接提问。"/></details>
      <el-input ref="input" v-model="message" aria-label="给 Ask Awesome 的消息" placeholder="输入你的问题，或继续追问…" type="textarea" :rows="3" maxlength="4000" :disabled="blocked" @keydown.ctrl.enter.prevent="prepare" @keydown.meta.enter.prevent="prepare"/>
      <div class="chat-send"><small>对话仅留在当前页面；发送前可核对材料与历史。</small><el-button type="primary" :loading="busy" :disabled="blocked||!message.trim()" @click="prepare">发送</el-button></div>
    </div>
    <el-dialog :model-value="!!preview" title="确认发送对话" width="min(640px,calc(100vw - 32px))" :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy" @close="cancel">
      <template v-if="preview"><p>{{ preview.provider }} / {{ preview.model }} · {{ preview.sends_to_cloud ? '发送到你配置的云端服务，可能产生费用' : '请求你配置的本地模型' }}</p><p>本次问题、附加材料和先前对话如下。取消不会调用模型。</p><h3>你的消息</h3><pre class="chat-preview">{{ preview.payload.question }}</pre><details v-if="previewHistory.length"><summary>附带此前 {{ previewHistory.length }} 组问答 · 查看全文</summary><div v-for="(turn,index) in previewHistory" :key="index"><b>你</b><pre class="chat-preview">{{ turn.question }}</pre><b>Ask Awesome</b><pre class="chat-preview">{{ turn.answer }}</pre></div></details><details v-if="previewMaterial"><summary>附加材料 · 查看全文</summary><pre class="chat-preview">{{ previewMaterial }}</pre></details><p v-else>没有附加页面材料。</p></template>
      <template #footer><el-button :disabled="busy" @click="cancel">返回修改</el-button><el-button type="primary" :loading="busy" @click="send">确认发送</el-button></template>
    </el-dialog>
  </section>
</template>
<script setup lang="ts">
import {ref,watch,computed,nextTick} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
type Payload={task:string;question:string;context:string}
type Preview={token:string;payload:Payload;provider:string;model:string;sends_to_cloud:boolean}
type Turn={id:string;question:string;answer:string;error:string;provider:string;model:string;payload:Payload}
const props=defineProps<{sourceContext:string;externalBusy?:boolean}>()
const emit=defineEmits<{state:[value:{busy:boolean;preview:boolean;result:boolean;failed:boolean;dirty:boolean}];connectionSettings:[]}>()
const route=useRoute(),router=useRouter(),message=ref(''),context=ref(props.sourceContext),turns=ref<Turn[]>([]),preview=ref<Preview|null>(null),busy=ref(false),error=ref(''),thread=ref<HTMLElement|null>(null),input=ref<{focus:()=>void}|null>(null)
const previewHistory=ref<{question:string;answer:string}[]>([]),previewMaterial=ref('')
const blocked=computed(()=>busy.value||!!props.externalBusy||!!preview.value)
watch(()=>props.sourceContext,value=>{if(!busy.value&&!preview.value)context.value=value})
watch([message,context],()=>{preview.value=null;error.value=''})
const state=computed(()=>({busy:busy.value||!!preview.value,preview:!!preview.value,result:!!turns.value.length,failed:!!error.value,dirty:!!message.value||!!context.value||!!turns.value.length}))
watch(state,value=>emit('state',value),{immediate:true})
async function bottom(){await nextTick();thread.value?.scrollTo({top:thread.value.scrollHeight})}
function cancel(){if(!busy.value)preview.value=null}
async function prepare(){
 if(blocked.value||!message.value.trim())return
 error.value=''
 if(turns.value.length>=10){error.value='本次对话已达到10次发送。请复制需要保留的回答后开始新对话。';return}
 const history=turns.value.filter(turn=>!!turn.answer).map(turn=>({question:turn.question,answer:turn.answer}))
 const selectedContext=history.length?JSON.stringify({conversation:history,material:context.value},null,2):context.value
 const payload={task:'explain',question:message.value,context:selectedContext}
 if(selectedContext.length>20000||new TextEncoder().encode(JSON.stringify(payload)).length>60000){error.value='对话历史与材料超过本次长度限制。请缩短材料，或复制回答后开始新对话；不会自动截断。';return}
 previewHistory.value=history;previewMaterial.value=context.value;busy.value=true
 try{preview.value=await request('/api/v1/owner/ai-preview','POST',payload)}catch(e){error.value=e instanceof Error?e.message:'无法准备本次发送，请检查模型连接。'}finally{busy.value=false}
}
async function send(){
 if(busy.value||props.externalBusy||!preview.value)return
 const selected=preview.value,turn:Turn={id:crypto.randomUUID(),question:selected.payload.question,answer:'',error:'',provider:selected.provider,model:selected.model,payload:selected.payload}
 turns.value.push(turn);busy.value=true;await bottom()
 try{const result=await request<{draft:string;provider:string;model:string}>('/api/v1/owner/ai-generate','POST',{token:selected.token,confirm:true},false);Object.assign(turns.value[turns.value.length-1],{answer:result.draft,provider:result.provider,model:result.model});message.value=''}catch(e){const text=(e instanceof Error?e.message:'请求失败')+' 没有自动重试；重新发送需再次确认。';turns.value[turns.value.length-1].error=text;error.value=text}finally{preview.value=null;busy.value=false;await bottom();input.value?.focus()}
}
async function copy(value:string){try{await navigator.clipboard.writeText(value);ElMessage.success('回答已复制，请核对来源')}catch{ElMessage.error('无法复制，可直接选择回答文字')}}
async function newConversation(){if(blocked.value)return;try{await ElMessageBox.confirm('清除当前对话和未发送的问题？附加材料保留，请先复制需要保留的回答。','新对话',{confirmButtonText:'开始新对话',cancelButtonText:'保留对话'})}catch{return}turns.value=[];message.value='';error.value='';input.value?.focus()}
async function settings(){if(blocked.value)return;try{if(!await router.push('/settings/connections'))emit('connectionSettings')}catch{error.value='无法打开连接设置，请刷新后重试。'}}
async function confirmMaterialChange(){if(busy.value||preview.value)return false;if(!context.value||context.value===props.sourceContext)return true;try{await ElMessageBox.confirm('替换你编辑的附加材料？问题和对话记录会保留。','替换助手材料',{confirmButtonText:'替换',cancelButtonText:'保留原内容'});return true}catch{return false}}
defineExpose({confirmMaterialChange,setQuestion:(value:string)=>{if(!blocked.value){message.value=value;input.value?.focus()}},focus:()=>input.value?.focus()})
</script>
<style scoped>
.ask-conversation{display:flex;flex-direction:column;flex:1;min-height:0;min-width:0}.chat-toolbar{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 18px;color:#88a9c5;font-size:11px;border-bottom:1px solid #59b4e21a}.chat-toolbar>div{display:flex;gap:6px}.chat-toolbar .el-button{margin:0;height:28px;padding:0 9px;font-size:11px}.chat-thread{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:18px;scrollbar-width:thin}.chat-welcome{display:grid;justify-items:center;align-content:center;text-align:center;min-height:160px;padding:20px 8px}.chat-welcome img{width:42px;height:42px}.chat-welcome h2{font-size:19px;margin:16px 0 8px;color:#e6f4ff}.chat-welcome p{font-size:12px;color:#8ca8c2;line-height:1.8;max-width:320px;margin:0}.chat-turn{display:flex;flex-direction:column;gap:12px;margin-bottom:22px}.chat-question{align-self:flex-end;max-width:92%;padding:12px 14px;background:#317fc329;border:1px solid #52beee33;border-radius:14px 14px 4px 14px}.chat-answer{padding:14px;border:1px solid #52beee22;border-radius:14px;background:#0e2339}.chat-answer.is-error{border-color:#f07c9340}.chat-turn small{font-size:10px;color:#7cbddc}.chat-turn p{white-space:pre-wrap;overflow-wrap:anywhere;color:#d5e6f5;font-size:13px;line-height:1.8;margin:7px 0}.chat-meta{font-size:10px;color:#7b9cb9}.chat-answer summary{cursor:pointer;font-size:11px;color:#9cc1dc;margin:12px 0}.chat-answer pre,.chat-preview{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;font-size:12px;line-height:1.7;max-height:35vh;overflow:auto}.chat-answer .el-button{height:28px;font-size:11px}.chat-composer{flex-shrink:0;padding:12px 16px 16px;border-top:1px solid #52beee22;background:#09192b;box-shadow:0 -10px 32px #030d1933}.chat-composer :deep(.el-textarea__inner){color:#e3f2ff;font-size:13px;line-height:1.6;padding:11px 12px;resize:none;border-radius:12px}.chat-material{margin-bottom:10px;color:#90aec8;font-size:11px}.chat-material summary{cursor:pointer}.chat-material[open]{max-height:24vh;overflow:auto}.chat-material :deep(.el-textarea){margin-top:8px}.chat-send{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px}.chat-send small{font-size:10px;color:#7995ae;line-height:1.5;max-width:280px}.chat-send .el-button{flex-shrink:0;height:36px;min-width:70px}.chat-error{font-size:12px;line-height:1.6;color:#ffb9c3;margin:0 0 10px;max-height:15vh;overflow:auto}.chat-preview{background:#09192b;padding:14px;border-radius:12px}
@media(max-height:650px){.chat-composer{padding:8px 12px}.chat-composer :deep(.el-textarea__inner){min-height:48px!important;max-height:70px}.chat-send small{display:none}.chat-material{margin-bottom:5px}.chat-send{margin-top:6px}}
</style>
