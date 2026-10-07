<template>
  <div class="app-footer">
    <div class="footer-content">
      <div class="copyright">
        <span>Awesome Stock</span>

        <span class="powered-by">Personal AI Decision OS</span>
      </div>
      <div class="disclaimer-text">
        {{ disclaimer }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const disclaimer = computed(() =>
  appStore.language === 'en-US'
    ? 'Awesome Stock is a personal portfolio management and analysis system, not a licensed investment advisory service. Market data, diagnostics, analysis, and reminders are provided only for personal research and review, and do not constitute investment advice or a promise of returns. Markets involve risk.'
    : 'Awesome Stock 是一个个人股票持仓管理分析系统，不具备证券投资咨询资质。系统中的行情、诊断、分析结论和提醒信息仅供个人研究、复盘与决策辅助使用，不构成任何投资建议或收益承诺。市场有风险，投资需谨慎。'
)
</script>

<style lang="scss" scoped>
.app-footer {
  .footer-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 6px;
    color: var(--el-text-color-regular);
    font-size: 14px;
    padding: 12px 16px;
    text-align: center;
  }

  .rights {
    margin-left: 4px;
  }

  .powered-by {
    margin-left: 12px;
    padding-left: 12px;
    border-left: 1px solid var(--el-border-color);
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .disclaimer-text {
    color: var(--el-text-color-secondary);
    font-size: 12px;
    line-height: 1.6;
    max-width: 1100px;
  }
}
</style>
