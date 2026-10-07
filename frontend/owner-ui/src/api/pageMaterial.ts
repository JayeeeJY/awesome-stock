// Ephemeral page-owned readers. No credentials, persistence, or model requests.
type Reader=(selection?:string)=>unknown
const readers=new Map<string,Reader>()
export function registerPageMaterial(path:string,reader:Reader){
  readers.set(path,reader)
  return ()=>{if(readers.get(path)===reader)readers.delete(path)}
}
export function readPageMaterial(path:string,selection?:string):{material:unknown}|undefined{
  const reader=readers.get(path)
  return reader?{material:reader(selection)}:undefined
}
