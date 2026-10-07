<template>
  <div class="academy-page page-container">
    <section class="academy-hero">
      <div>
        <p class="eyebrow">{{ copy.eyebrow }}</p>
        <h1>{{ copy.title }}</h1>
        <p class="hero-desc">{{ copy.subtitle }}</p>
      </div>
      <div class="hero-visual" aria-hidden="true">
        <span>{{ copy.visualStepOne }}</span>
        <i />
        <span>{{ copy.visualStepTwo }}</span>
        <i />
        <span>{{ copy.visualStepThree }}</span>
      </div>
    </section>

    <section class="document-layout" aria-label="Academy learning documents">
      <aside class="doc-index" aria-label="Learning document index">
        <div class="index-tools"><p class="index-kicker">{{ copy.indexTitle }}</p><button type="button" :aria-expanded="showSearch" @click="toggleSearch">{{ showSearch ? '收起搜索' : '查找文章' }}</button></div>
        <div v-if="showSearch" class="academy-search"><el-input v-model="search" clearable aria-label="搜索学习文档" placeholder="搜索概念、误区或检查清单"/><span role="status">{{ docs.length }} / {{ allDocs.length }} 篇文档</span></div>
        <p v-if="!docs.length" class="empty-search">没有匹配的文档，请调整关键词。</p>
        <nav>
          <a v-for="doc in docs" :key="doc.id" :href="`#${doc.id}`" class="doc-link">
            <span>{{ doc.number }}</span>
            <strong>{{ doc.navTitle }}</strong>
            <small>{{ doc.navHint }}</small>
          </a>
        </nav>
      </aside>

      <div class="doc-stack">
        <article v-for="doc in docs" :id="doc.id" :key="doc.id" class="learning-doc">
          <header class="doc-header">
            <span class="doc-number">{{ doc.number }}</span>
            <div>
              <p class="eyebrow">{{ doc.category }}</p>
              <h2>{{ doc.title }}</h2>
              <p>{{ doc.summary }}</p>
            </div>
          </header>

          <div class="doc-body">
            <section v-if="doc.diagram" class="doc-block diagram-block">
              <h3>{{ labels.diagram }}</h3>
              <div class="diagram-stage" :class="`diagram-${doc.diagram}`">
                <template v-if="doc.diagram === 'sequence'">
                  <span v-for="step in diagramLabels.sequence" :key="step">{{ step }}</span>
                </template>
                <template v-else-if="doc.diagram === 'candle'">
                  <div class="wick wick-top" />
                  <div class="candle-body" />
                  <div class="wick wick-bottom" />
                  <small>{{ diagramLabels.candle }}</small>
                </template>
                <template v-else-if="doc.diagram === 'trend'">
                  <svg viewBox="0 0 320 120" role="img" aria-label="Trend diagram">
                    <polyline points="20,92 78,72 128,82 188,46 236,56 300,24" />
                    <circle v-for="point in trendPoints" :key="point" :cx="point.split(',')[0]" :cy="point.split(',')[1]" r="5" />
                  </svg>
                </template>
                <template v-else-if="doc.diagram === 'volume'">
                  <span v-for="bar in volumeBars" :key="bar" :style="{ height: `${bar}%` }" />
                </template>
                <template v-else-if="doc.diagram === 'ma'">
                  <svg viewBox="0 0 320 120" role="img" aria-label="Moving average diagram">
                    <path class="price-line" d="M16 88 C58 58, 88 74, 128 48 S214 62, 304 22" />
                    <path class="avg-line" d="M16 92 C70 82, 118 72, 168 58 S248 46, 304 34" />
                  </svg>
                </template>
                <template v-else-if="doc.diagram === 'oscillator'">
                  <div class="osc-line high">70</div>
                  <svg viewBox="0 0 320 120" role="img" aria-label="RSI diagram">
                    <path d="M18 88 C54 96, 74 28, 112 40 S166 96, 204 78 260 28, 302 44" />
                  </svg>
                  <div class="osc-line low">30</div>
                </template>
                <template v-else-if="doc.diagram === 'macd'">
                  <span v-for="bar in macdBars" :key="bar.value" :class="{ negative: bar.value < 0 }" :style="{ height: `${Math.abs(bar.value)}px` }" />
                </template>
                <template v-else-if="doc.diagram === 'bollinger'">
                  <svg viewBox="0 0 320 120" role="img" aria-label="Bollinger Bands diagram">
                    <path class="band-line" d="M18 36 C84 18, 112 50, 164 32 S248 34, 304 16" />
                    <path class="avg-line" d="M18 64 C84 50, 124 68, 168 54 S250 58, 304 42" />
                    <path class="band-line" d="M18 92 C84 82, 112 98, 164 86 S248 90, 304 74" />
                  </svg>
                </template>
                <template v-else-if="doc.diagram === 'option-payoff'">
                  <svg viewBox="0 0 320 140" role="img" aria-label="Option payoff diagram">
                    <line x1="24" y1="92" x2="300" y2="92" />
                    <line x1="92" y1="18" x2="92" y2="124" />
                    <polyline points="24,112 132,112 286,28" />
                    <text x="160" y="137" text-anchor="middle" fill="currentColor" font-size="10">{{ diagramLabels.payoff }}</text>
                  </svg>
                </template>
                <template v-else-if="doc.diagram === 'covered-call'">
                  <div class="payoff-card stock">{{ diagramLabels.stock }}</div>
                  <span class="plus">+</span>
                  <div class="payoff-card premium">{{ diagramLabels.premium }}</div>
                  <span class="equals">=</span>
                  <div class="payoff-card cap">{{ diagramLabels.cap }}</div>
                </template>
                <template v-else-if="doc.diagram === 'greeks'">
                  <span v-for="greek in diagramLabels.greeks" :key="greek" class="greek-pill">{{ greek }}</span>
                </template>
                <template v-else>
                  <span v-for="step in diagramLabels.confirmation" :key="step">{{ step }}</span>
                </template>
              </div>
            </section>

            <section class="doc-block doc-definition">
              <h3>{{ labels.definition }}</h3>
              <p>{{ doc.definition }}</p>
            </section>

            <section class="doc-block">
              <h3>{{ labels.howToRead }}</h3>
              <ul>
                <li v-for="item in doc.howToRead" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="doc-block">
              <h3>{{ labels.marketMeaning }}</h3>
              <p>{{ doc.marketMeaning }}</p>
            </section>

            <section class="doc-block two-column">
              <div>
                <h3>{{ labels.strengths }}</h3>
                <ul>
                  <li v-for="item in doc.strengths" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div>
                <h3>{{ labels.limits }}</h3>
                <ul>
                  <li v-for="item in doc.limits" :key="item">{{ item }}</li>
                </ul>
              </div>
            </section>

            <section class="doc-block trap-block">
              <h3>{{ labels.traps }}</h3>
              <ul>
                <li v-for="item in doc.traps" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="doc-block checklist-block">
              <h3>{{ labels.checklist }}</h3>
              <ol>
                <li v-for="item in doc.checklist" :key="item">{{ item }}</li>
              </ol>
            </section>

            <section class="doc-block practice-block">
              <h3>{{ labels.practice }}</h3>
              <ol>
                <li v-for="item in doc.practice" :key="item">{{ item }}</li>
              </ol>
            </section>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/app'

defineOptions({ name: 'AcademyHome' })

interface LearningDoc {
  id: string
  number: string
  category: string
  navTitle: string
  navHint: string
  diagram?: 'sequence' | 'candle' | 'trend' | 'volume' | 'ma' | 'oscillator' | 'macd' | 'bollinger' | 'confirmation' | 'option-payoff' | 'covered-call' | 'greeks'
  title: string
  summary: string
  definition: string
  howToRead: string[]
  marketMeaning: string
  strengths: string[]
  limits: string[]
  traps: string[]
  checklist: string[]
  practice: string[]
}

const appStore = useAppStore()
const isEnglish = computed(() => appStore.language === 'en-US')

const copy = computed(() => isEnglish.value ? {
  eyebrow: 'ACADEMY / TECHNICAL DOCUMENTS',
  title: 'Technical analysis learning documents',
  subtitle: 'A quiet document library for learning indicators. Each note explains what the indicator is, how to read it, what it can and cannot prove, and how to turn it into a checklist.',
  visualStepOne: 'Concept',
  visualStepTwo: 'Diagram',
  visualStepThree: 'Checklist',
  indexTitle: 'Document index',
} : {
  eyebrow: '学院 / 技术分析文档',
  title: '投资知识学习文档',
  subtitle: '这里不做课程商城，也不做知识看板。学院第一版就是一篇篇能读懂的学习文档：技术指标讲清楚，期权基础讲明白，最后都落到检查清单。',
  visualStepOne: '概念',
  visualStepTwo: '示意图',
  visualStepThree: '检查清单',
  indexTitle: '文档目录',
})

const labels = computed(() => isEnglish.value ? {
  definition: 'What it is',
  howToRead: 'How to read it',
  marketMeaning: 'Market meaning',
  strengths: 'Useful for',
  limits: 'Limits',
  traps: 'Common mistakes',
  checklist: 'Use checklist',
  practice: 'Practice questions',
  diagram: 'Diagram',
} : {
  definition: '是什么',
  howToRead: '怎么看',
  marketMeaning: '市场含义',
  strengths: '优点',
  limits: '缺点',
  traps: '常见误区',
  checklist: '使用清单',
  practice: '练习问题',
  diagram: '示意图',
})

const trendPoints = ['20,92', '78,72', '128,82', '188,46', '236,56', '300,24']
const volumeBars = [36, 48, 34, 68, 44, 86, 62, 74]
const macdBars = [
  { value: -42 },
  { value: -34 },
  { value: -28 },
  { value: -18 },
  { value: 10 },
  { value: 24 },
  { value: 34 },
]

const diagramLabels = computed(() => isEnglish.value ? {
  sequence: ['Trend', 'Location', 'Price', 'Volume', 'Momentum', 'Plan'],
  candle: 'Open · Close · High · Low',
  payoff: 'Break-even after premium',
  stock: 'Hold shares',
  premium: 'Collect premium',
  cap: 'Upside capped',
  greeks: ['Delta', 'Gamma', 'Theta', 'Vega', 'IV'],
  confirmation: ['No new low', 'Volume', 'Momentum', 'MA reclaim'],
} : {
  sequence: ['趋势', '位置', '价格', '成交量', '动能', '计划'],
  candle: '开盘 · 收盘 · 最高 · 最低',
  payoff: '权利金后的盈亏平衡',
  stock: '持有正股',
  premium: '收取权利金',
  cap: '上方收益封顶',
  greeks: ['Delta', 'Gamma', 'Theta', 'Vega', '隐含波动率'],
  confirmation: ['不创新低', '成交确认', '动能修复', '站回均线'],
})

const chineseDocs: LearningDoc[] = [
  {
    id: 'principles',
    number: '00',
    category: '学习总原则',
    navTitle: '总原则',
    navHint: '先顺序，后指标',
    diagram: 'sequence',
    title: '先建立读图顺序，再看单个指标',
    summary: '技术分析的价值不是预测下一根 K 线，而是把市场行为翻译成概率、节奏和风险。',
    definition: '技术分析是一套观察价格、成交量、趋势和动能的方法。它更适合回答“什么时候动、用多大仓位、错了怎么办”，不应该替代基本面判断，也不能保证某只股票一定涨跌。',
    howToRead: ['先确定周期：日线、周线、小时线代表的决策级别完全不同。', '先看趋势和位置，再看 K 线、成交量和指标。', '先判断风险和失效条件，最后才讨论是否交易。', '把下跌停止、买盘出现、趋势反转分成三层，不要把第一层当第三层。'],
    marketMeaning: '单个指标只能提供一个角度。真正有意义的是多项证据是否指向同一个结论，例如趋势改善、成交量配合、动能修复和价格重新站回关键均线。',
    strengths: ['能让交易计划更具体，减少凭感觉买卖。', '能帮助识别风险位置、节奏变化和确认条件。', '适合和 Awesome Stock 的 Plan、Research、Evolve 模块连接。'],
    limits: ['指标大多基于历史价格和成交量，天然滞后。', '财报、政策、地缘政治、行业供需会让技术形态失效。', '震荡市里信号容易反复打脸。'],
    traps: ['看到超卖就抄底，看到金叉就追涨。', '先买入，再回头找指标为自己辩护。', '用短周期信号否定长期趋势。'],
    checklist: ['我看的是什么周期？这个周期对应短线、波段还是长期持有？', '趋势是上升、下降还是横盘？当前位置靠近支撑还是压力？', '价格、成交量、均线、RSI/MACD、布林带是否互相确认？', '如果判断错了，失效点在哪里？仓位是否能承受继续下跌？'],
    practice: ['请用一句话描述你当前最关注持仓的趋势状态。', '找一张图，按“周期、趋势、位置、K线、成交量、均线、动能、布林带、计划”的顺序读一遍。', '写下一个你最容易犯的技术面误区，并把它转成 Evolve 规则候选。'],
  },
  {
    id: 'candlestick',
    number: '01',
    category: '价格行为',
    navTitle: 'K线',
    navHint: '多空争夺战报',
    diagram: 'candle',
    title: 'K线：一个周期内多空争夺的战报',
    summary: 'K 线把开盘、收盘、最高、最低压缩成一张图，重点不是背形态，而是看位置和确认。',
    definition: 'K 线由实体和上下影线组成。实体表示开盘到收盘的结果，影线表示盘中试探过但没有完全守住的价格。',
    howToRead: ['先看实体方向和长度：长阳代表买方主动，长阴代表卖方主动。', '再看上下影线：长上影说明上涨后被卖回，长下影说明下跌后被买回。', '最后看位置：同样的十字星、锤头线、吞没形态，在高位和低位含义可能完全相反。', '组合形态要结合成交量和趋势判断，不能只看名字。'],
    marketMeaning: 'K 线反映的是当期情绪和关键价位争夺。它可以提示犹豫、恐慌、承接或反攻，但单根 K 线很难证明趋势已经反转。',
    strengths: ['直观、信息密度高。', '适合观察情绪突变、支撑压力争夺和短期节奏。', '能给后续成交量和均线确认提供观察点。'],
    limits: ['噪声很大，尤其在短周期。', '单根 K 线无法区分短暂反弹和真正反转。', '没有位置和成交量配合时，形态可信度明显下降。'],
    traps: ['把每一种形态背成固定答案。', '看到锤头线就立即买入。', '忽略这根 K 线处在上升、下降还是横盘趋势里。'],
    checklist: ['这根 K 线出现在高位、低位、趋势中段还是关键支撑压力附近？', '实体和影线谁更重要？收盘靠近高点还是低点？', '成交量是否支持这根 K 线表达的方向？', '次日或随后几天是否出现确认？'],
    practice: ['连续下跌后出现长下影小实体，能否直接判断见底？为什么？', '高位十字星和低位十字星的观察重点有什么不同？', '看涨吞没如果没有放量，可信度会怎样变化？'],
  },
  {
    id: 'trend',
    number: '02',
    category: '趋势结构',
    navTitle: '趋势',
    navHint: '先看河流方向',
    diagram: 'trend',
    title: '趋势：先判断河流方向，再决定怎么划船',
    summary: '趋势判断比抄最低点重要。最低点事后才知道，趋势改善通常会留下多个可识别信号。',
    definition: '趋势是价格在一段时间内的主要运动方向，通常分为上升、下降和横盘。',
    howToRead: ['上升趋势看高点抬高、低点也抬高。', '下降趋势看高点降低、低点也降低。', '横盘看价格是否反复被相近的上沿和下沿限制。', '用与你决策周期一致的图看趋势，不要用很短周期否定长期结构。'],
    marketMeaning: '趋势代表市场中持续占优势的一方。上升趋势里的回调更像买方休息，下降趋势里的反弹常常只是卖方喘息。',
    strengths: ['能过滤大量噪声。', '帮助确定交易方向和仓位强弱。', '能减少在下降趋势里越跌越买的冲动。'],
    limits: ['趋势确认通常有滞后。', '震荡市里容易假突破和假跌破。', '趋势线画法有主观性。'],
    traps: ['执着于买在最低点。', '把一次急反弹当成趋势反转。', '因为估值低就忽略下降趋势还没结束。'],
    checklist: ['最近两个高点和两个低点是抬高、降低还是混乱？', '当前价格处于趋势的早段、中段还是末段？', '如果是下降趋势，我等待的反转证据是什么？', '如果是横盘，靠近区间上沿还是下沿？'],
    practice: ['股价创出新高后又跌破前一个重要低点，原上升趋势是否仍完整？', '为什么下降趋势里的低估值不一定安全？', '横盘区间中部为什么容易做出低质量交易？'],
  },
  {
    id: 'volume',
    number: '03',
    category: '成交确认',
    navTitle: '成交量',
    navHint: '参与度与分歧',
    diagram: 'volume',
    title: '成交量：价格告诉你方向，成交量告诉你有多少人认真',
    summary: '成交量不等于买入量，它衡量参与度和分歧。真正重要的是价格方向、量能变化和位置的组合。',
    definition: '成交量是一段时间内成交的股票数量。每一笔成交都有买方和卖方，所以放量不是天然看涨。',
    howToRead: ['把当日成交量与过去 20 日平均量比较。', '观察放量上涨、放量下跌、缩量上涨、缩量下跌分别出现在什么位置。', '突破压力位时，成交量显著高于均量更有说服力。', '急跌放量后，要看随后 1 到 3 天是否不再创新低、收盘重心是否抬高。'],
    marketMeaning: '放量代表参与度和分歧扩大，缩量代表观望或抛压减轻。放量止跌只有在后续不再创新低时才更可信。',
    strengths: ['能验证突破是否得到资金配合。', '能观察恐慌释放和承接是否出现。', '能帮助识别弱反弹和有效反转的区别。'],
    limits: ['财报日、指数再平衡、期权到期会制造异常量。', '放量可能是买盘，也可能是出货或恐慌卖盘。', '低流动性标的的成交量噪声更大。'],
    traps: ['认为放量一定上涨。', '认为缩量下跌一定安全。', '看到一根放量 K 线就认定主力进场。'],
    checklist: ['成交量相对 20 日均量是放大还是缩小？', '价格是上涨、下跌、突破、跌破还是止跌？', '放量发生在支撑、压力、趋势中段还是恐慌下跌后？', '后续 1 到 3 天是否确认，而不是只看当天？'],
    practice: ['放量大跌但收在全天最低附近，算放量止跌吗？', '突破新高但成交量低于 20 日均量，应该如何理解？', '连续缩量下跌和缩量横盘，哪个更接近卖压衰竭？为什么？'],
  },
  {
    id: 'moving-average',
    number: '04',
    category: '平均成本',
    navTitle: '均线',
    navHint: '不同周期成本线',
    diagram: 'ma',
    title: '均线：不同时间尺度的市场平均成本',
    summary: '均线最重要的不是金叉死叉，而是方向、价格相对位置和多条均线的排列。',
    definition: '移动平均线把过去若干天的收盘价取平均并连成线。MA5 偏短线，MA10 偏短中线，MA20 约代表一个交易月，MA60 约代表一个季度。',
    howToRead: ['先看均线方向：向上、走平还是向下。', '再看价格在均线上方还是下方。', '最后看排列：MA5、MA10、MA20、MA60 是多头排列还是空头排列。', '把支撑压力理解成区域，不要精确到一分钱。'],
    marketMeaning: '价格长期站在上升均线上方，说明平均持仓者逐步盈利；跌破并压在下降均线下方，反弹容易遇到解套卖压。',
    strengths: ['简单、直观，适合识别趋势和节奏。', '能帮助判断支撑、压力和回踩质量。', '适合做仓位分批和失效条件的参考。'],
    limits: ['本质是历史平均，天然滞后。', '震荡市中金叉死叉频繁失效。', '不同标的和周期需要不同参数理解。'],
    traps: ['金叉必涨、死叉必跌。', '股价站上一天 MA20 就认定趋势反转。', '忽略均线斜率，只看价格是否穿越。'],
    checklist: ['短中长期均线分别向上、走平还是向下？', '价格在 MA5/MA10/MA20/MA60 的哪一侧？', '当前是多头排列、空头排列还是缠绕震荡？', '如果回踩均线，成交量是否缩小、价格是否守住？'],
    practice: ['股价站上 MA20，但 MA20 仍明显向下，这算趋势反转吗？', '多头排列中回踩 MA20 且缩量，通常如何理解？', '为什么震荡市里金叉和死叉容易反复失效？'],
  },
  {
    id: 'rsi',
    number: '05',
    category: '动能指标',
    navTitle: 'RSI',
    navHint: '上涨与下跌力气',
    diagram: 'oscillator',
    title: 'RSI：上涨力气和下跌力气的拔河比分',
    summary: 'RSI 低说明近期下跌力度很强，不等于马上要涨。重点是止跌、背离和重新站回关键区域。',
    definition: 'RSI 通常取 14 个周期，比较这段时间平均上涨幅度与平均下跌幅度，并换算成 0 到 100。',
    howToRead: ['一般把 70 以上称为超买，30 以下称为超卖。', '比数值本身更重要的是 RSI 是否止跌、是否形成更高低点。', '价格创新低但 RSI 不创新低，可能出现底背离，但仍需要价格和成交量确认。', '强趋势中 RSI 可以长时间停留在超买或超卖区。'],
    marketMeaning: 'RSI 反映近期上涨和下跌的力度差。超卖表示卖压很强、下跌很急；它提示可能接近过度，但不证明买盘已经占优。',
    strengths: ['反应快，适合观察动能极端。', '适合发现背离和卖压减弱线索。', '能帮助避免在极端动能阶段一次性重仓。'],
    limits: ['强趋势中会长期钝化。', '逆势信号容易过早出现。', '只看 RSI 不看趋势，容易接飞刀。'],
    traps: ['RSI 到 30 立刻抄底。', 'RSI 到 70 立刻卖出或做空。', '看到背离就忽略价格仍在创新低。'],
    checklist: ['RSI 当前处于超买、正常还是超卖区域？', 'RSI 是继续走弱，还是从极低区域回升？', '价格是否不再创新低？RSI 是否形成更高低点？', 'K 线、成交量、均线是否也支持动能修复？'],
    practice: ['RSI 从 18 回到 28，但股价仍创新低，能算见底吗？', '强势股 RSI 连续两周在 70 以上，说明什么？', '价格创新低但 RSI 没有创新低，这叫什么？还需要什么确认？'],
  },
  {
    id: 'macd',
    number: '06',
    category: '趋势动能',
    navTitle: 'MACD',
    navHint: '速度与惯性',
    diagram: 'macd',
    title: 'MACD：趋势速度与惯性的仪表盘',
    summary: 'MACD 适合观察趋势与动能，但滞后明显。绿柱缩短只是下跌惯性减弱，不等于反转完成。',
    definition: 'MACD 由 DIF、DEA 和柱状图组成。DIF 反映短期与长期指数均线差，DEA 是 DIF 的平滑线，柱子反映二者距离。',
    howToRead: ['看 DIF 和 DEA 的位置、方向与交叉。', '看柱子在零轴上方还是下方。', '红柱变长表示上行动能增强，红柱变短表示上行动能减弱。', '绿柱变长表示下行动能增强，绿柱变短表示下跌惯性减弱。'],
    marketMeaning: 'MACD 把趋势速度和动能变化放在一起看。零轴下的低位金叉通常仍弱于零轴上的金叉，必须结合价格是否重新站回关键均线。',
    strengths: ['能同时观察趋势和动能。', '适合中短期趋势确认。', '能帮助区分“下跌放缓”和“真正反转”。'],
    limits: ['滞后明显，常在价格已反弹一段后才金叉。', '震荡市交叉频繁，假信号多。', '柱子变短不代表方向已经改变。'],
    traps: ['绿柱变短就等于买点。', '零轴下金叉等同于强势反转。', '忽略价格是否仍创新低、均线是否仍下行。'],
    checklist: ['DIF 和 DEA 在零轴上方还是下方？', '两条线是向上、走平还是向下？', '柱子是变长还是变短，连续性如何？', '价格是否配合站回 MA5/MA10/MA20？'],
    practice: ['绿柱连续三天变短，但股价每天仍创新低，应该如何理解？', '零轴下金叉和零轴上金叉，哪个通常更强？', '为什么 MACD 经常在股价已经反弹后才金叉？'],
  },
  {
    id: 'bollinger',
    number: '07',
    category: '波动通道',
    navTitle: '布林带',
    navHint: '趋势与波动率',
    diagram: 'bollinger',
    title: '布林带：随波动自动变宽变窄的弹性通道',
    summary: '布林带不是简单的高抛低吸工具。贴上轨可能是强势延续，贴下轨可能是弱势加速。',
    definition: '布林带通常以 MA20 为中轨，上下轨约为中轨加减两倍标准差。波动变大时通道变宽，波动变小时通道变窄。',
    howToRead: ['看价格相对上轨、中轨、下轨的位置。', '看通道是收口还是开口。', '看中轨方向，判断趋势背景。', '贴轨运行时要结合成交量和趋势，不能机械反向交易。'],
    marketMeaning: '收口说明波动率压缩，像弹簧被压住，但方向未知；开口说明波动释放，可能意味着趋势或剧烈波动正在展开。',
    strengths: ['能把趋势和波动率放在一张图里。', '适合观察突破前压缩和趋势加速。', '能帮助判断价格是否过度偏离中轨。'],
    limits: ['强趋势中价格会长期贴轨。', '不同市场和周期参数效果不同。', '单独使用容易过早逆势交易。'],
    traps: ['碰下轨就买、碰上轨就卖。', '把收口当成一定向上突破。', '忽略中轨方向和成交量。'],
    checklist: ['价格在上轨、中轨、下轨的哪一侧？', '通道是在收口、走平还是快速开口？', '中轨 MA20 的方向是什么？', '如果跌破下轨，是否重新收回并获得后续确认？'],
    practice: ['连续贴下轨下跌，为什么不能只因碰下轨而买入？', '布林带收口后放量突破上轨，下一步应观察什么？', '股价重新站回中轨，但中轨仍向下，意味着什么？'],
  },
  {
    id: 'mu-case',
    number: '08',
    category: '综合案例',
    navTitle: 'MU 案例',
    navHint: '超卖不等于见底',
    diagram: 'confirmation',
    title: 'MU 综合判断：极度超卖的下降趋势，不等于确认见底',
    summary: '这个案例的核心不是判断 MU 一定怎样走，而是训练“有承接”和“趋势改善”之间的区别。',
    definition: '综合判断是把 K 线、趋势、成交量、均线、RSI、MACD 和布林带按固定顺序放在一起看，避免被单个指标牵着走。',
    howToRead: ['K 线：急跌后的低位拉回只说明有承接，尚不能单独定义反转。', '趋势：短中期高低点持续降低时，下降趋势优先于“跌了很多”的直觉。', '成交量：巨量可能同时包含恐慌卖盘和抄底买盘，需要随后不创新低确认。', '动能：RSI 超卖、MACD 绿柱缩短都只是卖压或下跌速度变化，不是完整买点。'],
    marketMeaning: '一个更稳健的见底判断，至少要看到价格不再创新低、反转 K 线或看涨组合、成交量配合、RSI 修复、MACD 改善和价格重新站回关键均线中的多项证据。',
    strengths: ['把多个指标放进同一张检查表，减少单点误判。', '适合训练仓位纪律和等待确认。', '能直接转成 Plan 的分批建仓条件。'],
    limits: ['案例数据有时间点限制，不能当实时交易依据。', '综合判断仍然不是确定性预测。', '极端财报或行业事件会改变技术结构。'],
    traps: ['因为 RSI 超卖就认为已经见底。', '把恐慌巨量直接当成净买入。', '等到一个指标改善后立刻一次性重仓。'],
    checklist: ['连续 2 到 3 天不再创新低，关键低点被守住。', '出现明确反转 K 线或看涨组合，收盘接近当日高位。', '上涨日放量，回调日缩量。', 'RSI 回到 30 上方并形成更高低点。', 'MACD 绿柱连续缩短，随后出现低位金叉。', '价格先站回 MA5/MA10，再挑战 MA20 或布林中轨。'],
    practice: ['MU 的 RSI 已经超卖，为什么仍不能直接加仓？', '如果第二天上涨但成交量明显缩小，你会把它视为强反转吗？', '写出你自己的见底确认清单，至少包含价格、成交量和一个动能指标。'],
  },
  {
    id: 'options-basics',
    number: '09',
    category: '期权基础',
    navTitle: '期权入门',
    navHint: '权利、义务与权利金',
    diagram: 'option-payoff',
    title: '期权入门：先理解权利、义务和权利金',
    summary: '期权不是“更刺激的股票”，而是一份带到期日、行权价和权利金的合约。新手先学风险边界，再学策略。',
    definition: '期权是一种合约。买方支付权利金，获得在到期日前后按约定价格买入或卖出标的的权利；卖方收取权利金，同时承担被行权的义务。',
    howToRead: ['先看标的、到期日、行权价和合约方向。', '再看权利金、盈亏平衡点和最大风险。', '区分买方风险有限但胜率未必高，卖方胜率可能高但尾部风险更大。', '任何期权策略都要先问：如果方向、时间和波动率都错了会怎样？'],
    marketMeaning: '期权把方向、时间和波动率放进同一笔交易。你不只是判断股票涨跌，还在判断涨跌幅度、发生时间以及市场预期波动是否合理。',
    strengths: ['可以用较小资金表达观点。', '能构造保护、增强收益或分批建仓工具。', '能把风险边界写得更明确。'],
    limits: ['有到期日，时间会持续消耗价值。', '报价受波动率影响，方向判断对了也可能亏钱。', '卖方策略可能暴露较大的尾部风险。'],
    traps: ['把买 Call 当成低成本买股票。', '只看权利金便宜，不看隐含波动率和到期时间。', '卖 Put 或卖 Call 前没有想清楚被行权后的仓位结果。'],
    checklist: ['我买/卖的是 Call 还是 Put？', '到期日和行权价是否匹配我的判断周期？', '最大亏损、最大收益和盈亏平衡点分别是什么？', '如果被行权，我是否愿意持有或卖出对应正股？'],
    practice: ['为什么期权方向判断正确也可能亏钱？', '买方和卖方的风险结构最大区别是什么？', '你会用期权表达长期投资逻辑，还是短期事件判断？为什么？'],
  },
  {
    id: 'call-put',
    number: '10',
    category: '期权基础',
    navTitle: 'Call / Put',
    navHint: '看涨与看跌',
    diagram: 'option-payoff',
    title: 'Call / Put：看涨、看跌和盈亏平衡',
    summary: 'Call 和 Put 的名字不难，难的是把方向、行权价、权利金和到期日放在一起看。',
    definition: 'Call 是买入标的的权利，Put 是卖出标的的权利。买 Call 通常表达看涨，买 Put 通常表达看跌或保护；卖 Call / Put 则是在收取权利金的同时承担相反义务。',
    howToRead: ['买 Call：标的价格需要上涨并超过行权价加权利金，才真正开始盈利。', '买 Put：标的价格需要下跌并低于行权价减权利金，才真正开始盈利。', '卖 Call：收权利金，但如果标的大涨，上方风险或机会成本会扩大。', '卖 Put：收权利金，但如果标的大跌，可能以行权价接下正股。'],
    marketMeaning: '期权盈亏不是只看“涨了还是跌了”，而是看标的价格是否越过盈亏平衡点，并且是否在到期前足够快地越过。',
    strengths: ['能清楚表达上涨、下跌、保护或接货意愿。', '适合把观点变成结构化风险。', '可以和正股仓位组合使用。'],
    limits: ['买方需要方向、幅度和时间三者都较配合。', '卖方可能在极端行情中承受不对称风险。', '流动性差的期权买卖价差可能很大。'],
    traps: ['只因为看涨就买很虚值的 Call。', '忽略权利金导致盈亏平衡点过高或过低。', '把卖 Put 收权利金误以为没有下跌风险。'],
    checklist: ['盈亏平衡点是多少？', '距离到期还有多久？', '标的需要涨/跌多少才值得？', '如果到期时刚好没到盈亏平衡，我是否接受权利金损失？'],
    practice: ['为什么“股票涨了”不一定代表买 Call 赚钱？', '卖 Put 和直接挂低价买股票有什么相似和不同？', '什么情况下你宁可买正股，而不是买 Call？'],
  },
  {
    id: 'covered-call',
    number: '11',
    category: '期权策略',
    navTitle: '备兑看涨',
    navHint: '持股收租但封顶',
    diagram: 'covered-call',
    title: 'Covered Call：持有正股时收取权利金',
    summary: '备兑看涨适合“愿意继续持有，但也愿意在某个价格卖出”的场景。它不是无风险收租。',
    definition: 'Covered Call 是在持有正股的同时卖出对应数量的 Call。你收取权利金，但如果股价超过行权价，正股可能被按行权价卖出。',
    howToRead: ['先确认你真的愿意在行权价卖出正股。', '权利金可以缓冲小幅下跌，但不能保护大跌。', '如果股价大涨，你的上方收益会被行权价限制。', '它更像“给持仓设置一个带租金的卖出价”。'],
    marketMeaning: 'Covered Call 适合震荡或温和上涨预期，不适合你强烈看好、完全不想卖出的核心仓位。',
    strengths: ['能在持股期间增加权利金收入。', '能帮助提前写清楚卖出价格。', '比裸卖 Call 风险更可控。'],
    limits: ['大涨时收益被封顶。', '大跌时权利金只能提供很小缓冲。', '可能因行权、税务或机会成本带来复杂影响。'],
    traps: ['对最想长期持有的股票随便卖 Call。', '只看权利金高，不看是否愿意被行权。', '在财报前高波动时期卖出后，忽视跳空风险。'],
    checklist: ['这只股票如果到行权价被卖出，我是否真的接受？', '权利金相对潜在上行机会是否值得？', '到期日是否避开我不想承担的事件窗口？', '如果股价下跌，我的正股仓位计划是什么？'],
    practice: ['Covered Call 为什么不是无风险收益？', '强烈看好一只股票时，为什么备兑看涨可能不适合？', '你会在哪类持仓上考虑 Covered Call？'],
  },
  {
    id: 'greeks-risk',
    number: '12',
    category: '期权风险',
    navTitle: 'Greeks',
    navHint: '时间与波动率',
    diagram: 'greeks',
    title: 'Greeks：用几个风险字母看懂期权价格变化',
    summary: 'Greeks 不是炫技指标，它们帮助你理解期权为什么涨跌：方向、速度、时间和波动率各自贡献了什么。',
    definition: 'Greeks 是期权风险敏感度。Delta 看标的价格变化影响，Gamma 看 Delta 变化速度，Theta 看时间损耗，Vega 看隐含波动率影响。',
    howToRead: ['Delta 越高，期权越像正股。', 'Gamma 越高，价格接近行权价时波动越敏感。', 'Theta 通常对买方不友好，到期越近时间损耗越快。', 'Vega 提醒你：隐含波动率下降时，方向判断正确也可能亏。'],
    marketMeaning: '期权价格由方向、时间和波动率共同决定。财报、重大事件和市场恐慌会推高隐含波动率，事件落地后可能出现波动率回落。',
    strengths: ['能拆解期权盈亏来源。', '帮助避免只看方向的错误。', '适合做期权仓位和到期日选择。'],
    limits: ['Greeks 会随价格、时间和波动率动态变化。', '模型估算不等于真实成交结果。', '极端行情中敏感度会快速失真。'],
    traps: ['只看 Delta，不看 Theta 和 Vega。', '财报前买高 IV 期权，却没考虑事件后 IV 回落。', '把 Greeks 当成确定性保护，而不是风险近似。'],
    checklist: ['这笔期权主要赚方向、时间还是波动率的钱？', 'Theta 每天大约消耗多少？', '隐含波动率处在高位还是低位？', '如果 IV 下跌、时间流逝、价格横盘，我是否仍能接受？'],
    practice: ['为什么财报后股票上涨，Call 也可能不涨甚至亏损？', 'Theta 对买方和卖方分别意味着什么？', '你会如何向新手解释 Delta？'],
  },
]

const englishDocs: LearningDoc[] = chineseDocs.map((doc) => ({
  ...doc,
  category: doc.category === '综合案例' ? 'Case study' : 'Technical document',
  navHint: doc.id === 'mu-case' ? 'Oversold is not bottom' : 'Indicator note',
  title: doc.id === 'principles' ? 'Build a reading sequence before reading indicators' : doc.title,
  summary: doc.id === 'principles'
    ? 'Technical analysis turns market behavior into probability, rhythm, and risk. It does not predict the next candle.'
    : doc.summary,
  definition: doc.id === 'principles'
    ? 'Technical analysis observes price, volume, trend, and momentum. It is better for timing, sizing, and invalidation than for proving a long-term thesis.'
    : doc.definition,
}))

const search = ref('')
const showSearch = ref(false)
function toggleSearch() { showSearch.value = !showSearch.value; if (!showSearch.value) search.value = '' }
const allDocs = computed(() => isEnglish.value ? englishDocs : chineseDocs)
const docs = computed(() => { const query=search.value.trim().toLocaleLowerCase();return allDocs.value.filter(doc=>!query||[doc.title,doc.navTitle,doc.summary,doc.definition,doc.marketMeaning,...doc.howToRead,...doc.strengths,...doc.limits,...doc.traps,...doc.checklist,...doc.practice].join(' ').toLocaleLowerCase().includes(query)) })
</script>

<style scoped lang="scss">
.academy-page {
  min-height: 100%;
  padding: 48px clamp(24px, 5vw, 80px) 72px;
  color: rgba(226, 239, 255, 0.92);
}

.academy-hero,
.learning-doc,
.doc-index {
  border: 1px solid rgba(78, 177, 255, 0.18);
  background:
    linear-gradient(135deg, rgba(9, 27, 50, 0.92), rgba(13, 23, 47, 0.82)),
    rgba(11, 24, 44, 0.86);
  box-shadow: 0 24px 80px rgba(0, 8, 25, 0.32);
  backdrop-filter: blur(18px);
}

.academy-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 28px;
  align-items: end;
  margin-bottom: 28px;
  padding: clamp(26px, 4vw, 44px);
  border-radius: 28px;
}

.eyebrow,
.index-kicker {
  margin: 0 0 10px;
  color: #5ddcff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 14px;
  font-size: clamp(34px, 4.2vw, 56px);
  line-height: 1.05;
  letter-spacing: -0.04em;
}

.hero-desc {
  max-width: 860px;
  margin-bottom: 0;
  color: rgba(184, 203, 226, 0.84);
  font-size: 16px;
  line-height: 1.9;
}

.hero-visual {
  display: grid;
  grid-template-columns: 1fr 32px 1fr 32px 1fr;
  gap: 10px;
  align-items: center;
  padding: 22px;
  border: 1px solid rgba(93, 220, 255, 0.18);
  border-radius: 22px;
  background: radial-gradient(circle at 50% 0%, rgba(93, 220, 255, 0.22), rgba(39, 119, 220, 0.08) 62%);
}

.hero-visual span {
  display: inline-flex;
  min-height: 58px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(130, 176, 224, 0.18);
  border-radius: 18px;
  background: rgba(6, 23, 45, 0.58);
  color: rgba(226, 239, 255, 0.9);
  font-weight: 800;
}

.hero-visual i {
  height: 1px;
  background: linear-gradient(90deg, rgba(93, 220, 255, 0), rgba(93, 220, 255, 0.7), rgba(93, 220, 255, 0));
}

.document-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.doc-index {
  position: sticky;
  top: 24px;
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding: 20px;
  border-radius: 24px;
}

.doc-index nav {
  display: grid;
  gap: 10px;
}

.doc-link {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 4px 12px;
  padding: 14px;
  border: 1px solid rgba(130, 176, 224, 0.12);
  border-radius: 16px;
  color: inherit;
  text-decoration: none;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.doc-link:hover,
.doc-link:focus-visible {
  border-color: rgba(93, 220, 255, 0.46);
  background: rgba(93, 220, 255, 0.08);
  outline: none;
  transform: translateX(3px);
}

.doc-link span {
  grid-row: span 2;
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(93, 220, 255, 0.1);
  color: #5ddcff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 800;
}

.doc-link strong {
  font-size: 15px;
}

.doc-link small {
  color: rgba(184, 203, 226, 0.68);
  line-height: 1.5;
}

.doc-stack {
  display: grid;
  gap: 24px;
}

.learning-doc {
  scroll-margin-top: 24px;
  padding: clamp(24px, 3.5vw, 40px);
  border-radius: 28px;
}

.doc-header {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 18px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(130, 176, 224, 0.14);
}

.doc-number {
  display: inline-flex;
  width: 54px;
  height: 54px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(93, 220, 255, 0.22);
  border-radius: 18px;
  background: rgba(93, 220, 255, 0.1);
  color: #5ddcff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 900;
}

.doc-header h2 {
  margin-bottom: 12px;
  font-size: clamp(25px, 2.6vw, 36px);
  line-height: 1.18;
}

.doc-header p:last-child {
  max-width: 880px;
  margin-bottom: 0;
  color: rgba(184, 203, 226, 0.8);
  line-height: 1.85;
}

.doc-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  padding-top: 24px;
}

.doc-block {
  min-width: 0;
  padding: 20px;
  border: 1px solid rgba(130, 176, 224, 0.12);
  border-radius: 20px;
  background: rgba(5, 18, 35, 0.42);
}

.doc-definition,
.checklist-block,
.practice-block {
  grid-column: 1 / -1;
}

.doc-block h3 {
  margin-bottom: 12px;
  color: rgba(236, 246, 255, 0.94);
  font-size: 16px;
}

.doc-block p,
.doc-block li {
  color: rgba(184, 203, 226, 0.82);
  line-height: 1.82;
}

.doc-block p {
  margin-bottom: 0;
}

.doc-block ul,
.doc-block ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}

.two-column {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.trap-block {
  border-color: rgba(255, 105, 130, 0.18);
  background: rgba(92, 25, 47, 0.18);
}

.checklist-block {
  border-color: rgba(65, 216, 174, 0.2);
  background: rgba(28, 112, 93, 0.14);
}

.practice-block {
  border-color: rgba(255, 191, 92, 0.18);
  background: rgba(117, 78, 21, 0.13);
}

.diagram-block {
  grid-column: 1 / -1;
  overflow: hidden;
  border-color: rgba(93, 220, 255, 0.2);
  background:
    radial-gradient(circle at 18% 10%, rgba(93, 220, 255, 0.2), transparent 34%),
    rgba(5, 18, 35, 0.42);
}

.diagram-stage {
  position: relative;
  display: flex;
  min-height: 150px;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 22px;
  border: 1px solid rgba(130, 176, 224, 0.12);
  border-radius: 18px;
  background: rgba(2, 10, 24, 0.36);
}

.diagram-stage svg {
  width: min(100%, 520px);
  height: 150px;
  overflow: visible;
}

.diagram-stage polyline,
.diagram-stage path {
  fill: none;
  stroke: #5ddcff;
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.diagram-stage circle {
  fill: #0f203a;
  stroke: #6ee7ff;
  stroke-width: 3;
}

.diagram-sequence span,
.diagram-confirmation span {
  display: inline-flex;
  min-width: 76px;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(93, 220, 255, 0.24);
  border-radius: 999px;
  background: rgba(93, 220, 255, 0.09);
  color: rgba(226, 239, 255, 0.9);
  font-weight: 800;
}

.diagram-candle {
  flex-direction: column;
  gap: 0;
}

.wick {
  width: 4px;
  height: 34px;
  border-radius: 999px;
  background: rgba(226, 239, 255, 0.72);
}

.candle-body {
  width: 52px;
  height: 74px;
  border: 2px solid rgba(255, 105, 130, 0.7);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 105, 130, 0.28), rgba(255, 105, 130, 0.08));
}

.diagram-candle small,
.diagram-option-payoff small {
  margin-top: 12px;
  color: rgba(184, 203, 226, 0.72);
}

.diagram-volume {
  align-items: flex-end;
}

.diagram-volume span,
.diagram-macd span {
  width: 28px;
  border-radius: 9px 9px 4px 4px;
  background: linear-gradient(180deg, #5ddcff, rgba(93, 220, 255, 0.24));
}

.diagram-macd {
  align-items: center;
}

.diagram-macd span {
  transform-origin: bottom;
}

.diagram-macd span.negative {
  align-self: flex-end;
  background: linear-gradient(180deg, rgba(255, 105, 130, 0.34), #ff6b86);
}

.price-line {
  stroke: #41d8ae;
}

.avg-line {
  stroke: #ffbf5c;
  stroke-width: 4;
}

.band-line {
  stroke: rgba(93, 220, 255, 0.58);
  stroke-width: 3;
  stroke-dasharray: 8 8;
}

.diagram-oscillator {
  flex-direction: column;
  gap: 4px;
}

.diagram-oscillator svg {
  height: 92px;
}

.osc-line {
  width: min(100%, 520px);
  border-top: 1px dashed rgba(184, 203, 226, 0.34);
  color: rgba(184, 203, 226, 0.64);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.diagram-option-payoff line {
  stroke: rgba(184, 203, 226, 0.35);
  stroke-width: 2;
}

.diagram-covered-call,
.diagram-greeks {
  flex-wrap: wrap;
}

.payoff-card,
.greek-pill {
  display: inline-flex;
  min-height: 52px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(93, 220, 255, 0.22);
  border-radius: 16px;
  background: rgba(93, 220, 255, 0.1);
  color: rgba(226, 239, 255, 0.92);
  font-weight: 800;
}

.payoff-card {
  min-width: 112px;
  padding: 0 16px;
}

.payoff-card.premium {
  border-color: rgba(65, 216, 174, 0.24);
  background: rgba(65, 216, 174, 0.12);
}

.payoff-card.cap {
  border-color: rgba(255, 191, 92, 0.26);
  background: rgba(255, 191, 92, 0.12);
}

.plus,
.equals {
  color: rgba(184, 203, 226, 0.7);
  font-size: 22px;
  font-weight: 900;
}

.greek-pill {
  min-width: 92px;
  padding: 0 16px;
}

@media (max-width: 1180px) {
  .academy-hero,
  .document-layout {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    grid-template-columns: 1fr;
  }

  .hero-visual i {
    display: none;
  }

  .doc-index {
    position: static;
    max-height: none;
  }

  .doc-index nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .academy-page {
    padding: 24px 14px 92px;
  }

  .academy-hero,
  .learning-doc,
  .doc-index {
    border-radius: 22px;
  }

  .doc-index nav,
  .doc-body,
  .two-column {
    grid-template-columns: 1fr;
  }

  .diagram-stage {
    min-height: 120px;
    flex-wrap: wrap;
    padding: 16px;
  }

  .doc-header {
    grid-template-columns: 1fr;
  }

  .doc-number {
    width: 48px;
    height: 48px;
  }
}
</style>

<style scoped>.index-tools{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}.index-tools .index-kicker{margin:0}.index-tools button{padding:3px 7px;border:1px solid rgba(93,220,255,.3);border-radius:8px;background:transparent;color:#80dfff;font-size:11px;white-space:nowrap;cursor:pointer}.index-tools button:hover,.index-tools button:focus-visible{border-color:#5ddcff;outline:2px solid #5ddcff;outline-offset:2px}.academy-search{display:grid;gap:8px;margin:0 0 12px}.academy-search span{color:#a5bad3;font-size:12px}.learning-doc{scroll-margin-top:90px}.doc-link:focus-visible{outline:2px solid #5fbfff;outline-offset:3px}.learning-doc p,.learning-doc li,.doc-link strong{overflow-wrap:anywhere}.diagram-stage svg{max-width:100%}.empty-search{padding:12px;border:1px solid #24405f;border-radius:12px;font-size:12px}</style>
