<template>
 <div class="rules-editor">
  <el-checkbox :model-value="!!modelValue" :disabled="disabled" @change="toggle">设置回撤加仓条件</el-checkbox>
  <template v-if="modelValue">
   <el-form-item label="锚定价格"><el-input :model-value="modelValue.anchor_price" inputmode="decimal" :disabled="disabled" @update:model-value="update('anchor_price',$event)"/></el-form-item>
   <el-form-item label="底仓占目标股数（%）"><el-input :model-value="modelValue.base_percent" inputmode="decimal" :disabled="disabled" @update:model-value="update('base_percent',$event)"/></el-form-item>
   <fieldset v-for="(rule,index) in modelValue.rules" :key="index" class="rule-row"><legend>回撤条件 {{ index+1 }}</legend>
    <el-form-item :label="`回撤幅度 ${index+1}（%）`"><el-input :model-value="rule.pullback_percent" inputmode="decimal" :disabled="disabled" @update:model-value="changeRule(index,'pullback_percent',$event)"/></el-form-item>
    <el-form-item :label="`加仓占目标股数 ${index+1}（%）`"><el-input :model-value="rule.add_percent" inputmode="decimal" :disabled="disabled" @update:model-value="changeRule(index,'add_percent',$event)"/></el-form-item>
    <el-form-item :label="`条件说明 ${index+1}`"><el-input :model-value="rule.label" maxlength="120" :disabled="disabled" @update:model-value="changeRule(index,'label',$event)"/></el-form-item>
    <el-button :disabled="disabled" @click="remove(index)">删除条件 {{ index+1 }}</el-button>
   </fieldset>
   <el-button :disabled="disabled||modelValue.rules.length>=12" @click="add">添加回撤条件</el-button>
   <p>例如填 5 表示回撤 5%。比例均以目标股数为基准；保存条件不会自动成交。</p>
  </template>
 </div>
</template>
<script setup lang="ts">
import {ElCheckbox} from 'element-plus'
import type {Strategy} from './strategyTypes'
const props=defineProps<{modelValue:Strategy|null;disabled:boolean}>(),emit=defineEmits<{ 'update:modelValue':[Strategy|null] }>()
const rule=()=>({pullback_percent:'5',add_percent:'20',label:'回撤后人工复核'})
function toggle(value:unknown){emit('update:modelValue',value?{anchor_price:'',base_percent:'20',rules:[rule()]}:null)}
function update(key:'anchor_price'|'base_percent',value:string){if(props.modelValue)emit('update:modelValue',{...props.modelValue,[key]:value})}
function changeRule(index:number,key:keyof Strategy['rules'][number],value:string){if(props.modelValue)emit('update:modelValue',{...props.modelValue,rules:props.modelValue.rules.map((r,i)=>i===index?{...r,[key]:value}:r)})}
function remove(index:number){if(props.modelValue)emit('update:modelValue',{...props.modelValue,rules:props.modelValue.rules.filter((_,i)=>i!==index)})}
function add(){if(props.modelValue)emit('update:modelValue',{...props.modelValue,rules:[...props.modelValue.rules,rule()]})}
</script>
<style scoped>
.rules-editor{width:100%;margin:16px 0}.rule-row{border:1px solid var(--el-border-color);border-radius:8px;padding:12px;margin:12px 0;min-width:0}legend{font-size:13px;color:var(--el-text-color-secondary)}p{font-size:12px;color:var(--el-text-color-secondary)}
</style>
