<template><section class="news-evidence" aria-label="新闻来源"><h3>新闻来源 · {{ source.symbol }}</h3><p>{{ source.source }} · 获取于 {{ source.retrieved_at }}</p><p>供应商资料 · 未人工核验</p><p>{{ source.notice }}</p><p v-if="!source.articles.length">本次查询没有返回匹配新闻，不代表没有相关新闻。</p><article v-for="article in source.articles" :key="article.id"><h4>{{ article.title }}</h4><p>{{ article.publisher }} · {{ article.published_at }}</p><p>{{ article.summary }}</p><p>供应商情绪标签：{{ article.sentiment?.label??'未提供' }} · 原始分数：{{ article.sentiment?.score??'未提供' }} · 未人工核验</p><a :href="article.url" target="_blank" rel="noopener noreferrer">主动打开新闻原文（外部网站）</a></article><p v-if="source.id">来源版本 {{ source.id }} · v{{ source.revision }}</p></section></template>
<script setup lang="ts">
import type {NewsSource} from '@/api/news'
defineProps<{source:NewsSource}>()
</script>
<style scoped>.news-evidence{padding:16px;border:1px solid var(--el-border-color);border-radius:12px;margin:12px 0;overflow-wrap:anywhere}.news-evidence p{line-height:1.6;white-space:pre-wrap}.news-evidence article{border-top:1px solid var(--el-border-color);padding:12px 0}.news-evidence a{color:var(--el-color-primary)}</style>
