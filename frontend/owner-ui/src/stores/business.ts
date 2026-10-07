import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getWorkspace, type Workspace } from '@/api/business'
export const useBusinessStore = defineStore('business', () => {
  const workspace=ref<Workspace|null>(null), loading=ref(false), error=ref(''), inboxOpen=ref(false),loadedAt=ref('')
  let pending: Promise<void>|undefined, generation=0
  const pendingActions=computed(()=>workspace.value?.actions.filter(a=>['pending','confirmed'].includes(a.status))||[])
  function load() {
    if(pending)return pending
    const epoch=generation
    loading.value=true;error.value=''
    const task=(async()=>{
      try{const value=await getWorkspace();if(epoch===generation){workspace.value=value;loadedAt.value=new Date().toISOString()}}
      catch(e){if(epoch===generation){workspace.value=null;loadedAt.value='';error.value=e instanceof Error?e.message:'工作区读取失败'}}
      finally{if(epoch===generation){loading.value=false;pending=undefined}}
    })()
    pending=task;return task
  }
  function reset(){generation++;pending=undefined;workspace.value=null;loading.value=false;error.value='';inboxOpen.value=false;loadedAt.value=''}
  return {workspace,loadedAt,loading,error,inboxOpen,pendingActions,load,reset}
})
