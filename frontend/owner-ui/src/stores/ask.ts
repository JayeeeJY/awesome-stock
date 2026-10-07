import {defineStore} from 'pinia'
export const useAskStore=defineStore('ask',{state:()=>({visible:false,pinned:false}),actions:{togglePinned(){this.pinned=!this.pinned},open(){this.visible=true},close(){this.visible=false}}})
