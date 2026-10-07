<template><div class="settings-page"><section class="settings-hero"><div class="settings-hero-copy"><div class="settings-kicker">Awesome Stock Control Center</div><h1 class="settings-title">个人连接设置</h1><p class="settings-subtitle">连接你自己的模型和行情服务，不配置也能使用手工业务。</p></div></section><div class="settings-layout"><aside class="settings-sidebar"><button class="settings-nav-item" @click="router.push('/settings/appearance')">外观</button><button class="settings-nav-item is-active">数据与 AI 连接</button><button class="settings-nav-item" @click="router.push('/settings/account')">账户与备份管理</button><button class="settings-nav-item" @click="router.push('/settings/transfer')">导入与导出</button><div class="settings-side-note"><div class="settings-side-note-title">费用与数据</div><p>云端使用你自己的 API Key，费用由你的服务商账号承担。Community 不提供统一密钥、不代付。</p><p>密钥只保留在服务进程内，退出、改密或重启后清除，不进入备份与导出。</p></div></aside><div class="settings-main"><AppDataState v-if="error" tone="error" :title="statusUnavailable?'连接状态读取失败':'连接操作未完成'" :description="error"/><section class="settings-panel model-panel"><div class="panel-head"><div><div class="panel-title">模型服务</div><p class="panel-subtitle">{{ statusLabel('ai') }}</p></div><el-button :disabled="busy||statusLoading" @click="load">刷新状态</el-button></div><details class="configuration-guide"><summary>模型配置与使用步骤</summary><ol><li>云端服务先获取自己的 API Key：<a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener noreferrer">DeepSeek 控制台</a> / <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer">OpenAI 控制台</a>。按账号权限填写模型 ID，费用由自己的账号承担。</li><li>本机模型请按 <a href="https://docs.ollama.com/quickstart" target="_blank" rel="noopener noreferrer">Ollama 安装说明</a>安装、启动并下载本地模型；用 ollama ls 查看完整模型名，Key 留空。连接本机 11434 端口。</li><li>点击「保存模型连接」，再在下方「测试连接」核对测试文字并确认发送。看到「连接测试成功」及模型回复才代表一次调用成功。保存本身不发请求，Key 输入框清空是正常的。</li><li>打开顶部 Ask Awesome，在自由输入框提问；需要材料时主动载入，预览后确认发送。模型回复需自行核对，每次云端请求使用自己的额度。</li><li>退出登录、改密、关闭连接或服务重启后，需重新配置。模型与行情互不代替；不配置也能用手工业务。</li></ol></details><el-form label-position="top"><el-form-item label="模型服务"><el-select v-model="provider" :disabled="busy" aria-label="模型服务"><el-option label="OpenAI 云端" value="openai"/><el-option label="DeepSeek 云端" value="deepseek"/><el-option :label="status?.ollama_location||'本机 Ollama'" value="ollama"/></el-select></el-form-item><p>{{ provider==='ollama'?'请自行安装并启动 Ollama、下载模型后填写模型名。使用自己的设备资源，无需云端 API Key。':'请填写自己的模型 API 账号凭据。登录本应用的账号不是模型名，ChatGPT 订阅不是 API Key。' }}</p><el-form-item label="模型 ID（不是服务名称或邮箱）"><el-input v-model="model" autocomplete="off" :disabled="busy" placeholder="填写服务商模型 ID 或已安装的本地模型名"/></el-form-item><p v-if="provider==='deepseek'" class="model-presets">常用模型：<el-button text :disabled="busy" @click="model='deepseek-flash'">deepseek-flash</el-button><el-button text :disabled="busy" @click="model='deepseek-v4-pro'">deepseek-v4-pro</el-button><a href="https://api-docs.deepseek.com/quick_start/pricing/" target="_blank" rel="noopener noreferrer">查看模型说明</a></p><el-form-item v-if="provider!=='ollama'" label="你自己的模型服务 API Key"><el-input v-model="aiKey" type="password" autocomplete="new-password" :disabled="busy" :placeholder="status?.ai.enabled?'已保存在当前进程；更换配置时重新填写 Key':'粘贴你自己的 API Key'"/></el-form-item></el-form><div class="panel-actions model-actions"><el-button type="primary" :loading="working" :disabled="busy" @click="configure('ai')">保存模型连接</el-button><el-button :disabled="busy||!status?.ai.enabled" @click="disable('ai')">关闭模型连接</el-button></div><div v-if="aiNotice" class="connection-feedback" role="status">{{ aiNotice }}</div><el-alert v-if="error&&errorContext==='ai'" type="error" :title="error" :closable="false" show-icon/><p class="model-help">保存后 Key 输入框会清空，凭据仍在当前进程中。保存不发送模型请求；下一步点击「测试连接」。</p><ConnectionTest :enabled="!!status?.ai.enabled" :configuration-matches="configurationMatches" :external-busy="working||statusLoading" :provider="provider" :model="model" :tested="!!status?.ai.tested" @busy="testing=$event" @success="testSucceeded"/></section>
<section class="settings-panel market-panel"><div class="panel-head"><div><div class="panel-title">行情服务</div><p class="panel-subtitle">{{ statusLabel('data') }}</p></div></div><p>可手工录入价格或导入 CSV 成交，无需连接行情服务。自动查询需使用你自己的行情 API；本次首发暂不提供 Yahoo 免 Key 接口。</p><div class="panel-actions"><el-button @click="router.push('/portfolio')">前往持仓录入价格</el-button><el-button @click="router.push('/settings/transfer')">导入 CSV</el-button></div><p>持仓页打开「管理持仓 → 记录价格快照」，可录入自己核对的价格与来源。</p><details class="configuration-guide"><summary>行情配置与保存步骤</summary><ol><li>不配 API：到「持仓 → 管理持仓 → 记录价格快照」录入已核对的价格、时间与来源。CSV 只导入成交，不导入行情或日线。</li><li>自动查询：美股/A股在 <a href="https://www.alphavantage.co/support/#api-key" target="_blank" rel="noopener noreferrer">Alpha Vantage 申请自己的 Key</a>；港股在 <a href="https://eodhd.com/register" target="_blank" rel="noopener noreferrer">EODHD 注册并获取 Token</a>。核对自己的市场权限与额度，项目不提供共享密钥、不代付。</li><li>填入对应凭据并启用连接，选择市场后输入代码：美国如 AAPL，A股如 600104，港股如 00700。启用不自动查询。</li><li>主动查询后核对价格/日线、币种、日期与来源，再点击「确认保存」。查询预览尚未写入账本；日级价格不是实时价。港股每次查询包含两次供应商请求。</li><li>权限或额度不足会显示错误，不自动重试或换源。服务重启后重新配置；已保存来源保留。</li></ol></details><div><p>Alpha Vantage · 美国市场 / 沪深 A 股 · 日级价格。使用你自己的行情账号与额度。</p><el-form label-position="top"><el-form-item label="你自己的 Alpha Vantage API Key"><el-input v-model="dataKey" type="password" autocomplete="new-password" :disabled="busy"/></el-form-item></el-form><div class="panel-actions"><el-button :disabled="busy" @click="configure('data')">启用行情连接</el-button><el-button :disabled="busy" @click="disable('data')">关闭行情连接</el-button></div></div><el-form label-position="top"><div><el-divider/><h3>港股日线连接</h3><p>{{ statusLabel('data_hk') }}</p><p>使用你自己的 EODHD Token 和额度；与 Alpha Vantage 分开保存于本次进程内存。每次主动查询包含标的核对与日线读取两次请求，无权限即停止，不自动换源。</p><el-form-item label="你自己的 EODHD API Token"><el-input v-model="hkKey" type="password" autocomplete="new-password" :disabled="busy"/></el-form-item><el-button :disabled="busy" @click="configure('data_hk')">启用港股连接</el-button><el-button :disabled="busy" @click="disable('data_hk')">关闭港股连接</el-button></div><el-divider/><el-form-item label="行情市场"><el-select v-model="market" :disabled="busy" aria-label="行情市场"><el-option label="美国市场 · USD" value="US"/><el-option label="沪深 A 股 · CNY" value="CN"/><el-option label="港股 · HKD · EODHD" value="HK"/></el-select></el-form-item><el-form-item :label="market==='US'?'美国市场标的代码':market==='CN'?'沪深 A 股代码':'港股代码'"><el-input v-model="symbol" :disabled="busy" maxlength="24"/></el-form-item></el-form><el-alert v-if="error&&errorContext!=='ai'" type="error" :title="error" :closable="false" show-icon/><p v-if="market==='CN'">输入六位代码，如 600104、000002；请求时按已支持号段映射供应商交易所代码，来源保留映射。仅人民币 A 股，不含 B 股、基金或港股；不要把现有持仓代码自动改名。公司与新闻来源当前仅支持美国市场。</p><p v-if="market==='HK'">输入四或五位港股代码，如 0700 或 00700；保存时使用五位代码。只接受供应商核对为香港上市且HKD计价的股票或基金。报价为最新日线收盘值，不是实时价；价格未复权，成交量按拆股调整。</p><el-button :disabled="busy"  :loading="requesting==='quote'" @click="fetchQuote">主动查询日级价格</el-button><div v-if="quote" class="surface-card"><h3>{{ quote.symbol }} · {{ quote.currency }} {{ quote.price }}</h3><p>{{ quote.as_of }} · {{ quote.source }}</p><p>供应商昨收：{{ quote.previous_close??'未提供' }} {{ quote.currency }}；不推测缺失值。</p><p>非实时，尚未保存。确认标的及币种后再写入价格快照。</p><el-button :disabled="busy" @click="saveQuote">确认保存价格快照</el-button></div><el-divider/><el-form label-position="top"><el-form-item label="日线历史范围"><el-select v-model="historyMode" :disabled="busy" aria-label="日线历史范围"><el-option label="最近100根" value="compact"/><el-option label="长历史（保留最近260根）" value="full"/></el-select></el-form-item></el-form><el-button :disabled="busy"  :loading="requesting==='history'" @click="fetchHistory">主动查询最近日线</el-button><p v-if="market==='HK'">港股最近100根查询过去200个自然日；260根查询过去550个自然日，按账号覆盖返回，不补造缺失交易日。两次请求都使用自己的额度。</p><p v-else>长历史从供应商完整响应保留最近260根；使用自己的账号权限和额度，若无权限将报错，不自动回退或重试。均为未复权日线，拆股、分红可能造成跳变；不足周期的指标保持待补。</p><div v-if="historyPreview" class="surface-card"><h3>{{ historyPreview.packet.symbol }} · {{ historyPreview.packet.candles.length }} 根日线</h3><p>供应商代码：{{ historyPreview.packet.provider_symbol||historyPreview.packet.symbol }}</p><p>供应商返回 {{ historyPreview.packet.received_points??historyPreview.packet.candles.length }} 根；当前保留 {{ historyPreview.packet.candles.length }} 根。</p><p>{{ historyPreview.packet.from }} — {{ historyPreview.packet.as_of }} · {{ historyPreview.packet.currency }} · {{ historyPreview.packet.price_basis==='supplier_ohlcv_no_adjclose'?'供应商 OHLCV（未读取 adjclose）':'未复权' }}</p><p v-if="historyPreview.packet.volume_basis==='split_adjusted'">成交量按供应商拆股调整口径；不使用 adjusted_close 替换原始价格。</p><details v-if="historyPreview.packet.listing_evidence"><summary>核对供应商标的身份</summary><pre>{{ historyPreview.packet.listing_evidence }}</pre></details><p>{{ historyPreview.packet.source }} · 尚未保存，预览5分钟有效。保存后作为独立来源快照，不修改账户或价格快照。</p><details><summary>核对日线内容</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{{ historyPreview.packet.candles }}</pre></details><el-button :disabled="busy" @click="saveHistory">确认保存日线快照</el-button></div><div><el-divider/><el-button :disabled="busy||market!=='US'" @click="fetchCompany">主动查询公司资料</el-button><p>查询公司介绍、行业及供应商估值/财务指标，不自动标记为人工核验。</p><div v-if="companyPreview"><CompanyEvidence :source="companyPreview.packet"/><p>尚未保存，预览5分钟有效。</p><el-button :disabled="busy" @click="saveCompany">确认保存公司资料</el-button></div><el-divider/><el-button :disabled="busy||market!=='US'" @click="fetchNews">主动查询相关新闻</el-button><p>使用你自己的行情额度。最多20条来源索引，不自动读取新闻全文或图片。</p><div v-if="newsPreview"><NewsEvidence :source="newsPreview.packet"/><p>尚未保存，预览5分钟有效。</p><el-button :disabled="busy" @click="saveNews">确认保存新闻来源</el-button></div></div></section></div></div></div></template>
<script setup lang="ts">
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {useRouter,onBeforeRouteLeave} from 'vue-router'
import {ElMessage,ElMessageBox} from 'element-plus'
import {request} from '@/api/owner'
import {operationCache} from '@/api/business'
import NewsEvidence from '@/components/Research/NewsEvidence.vue'
import type {NewsSource} from '@/api/news'
import CompanyEvidence from '@/components/Research/CompanyEvidence.vue'
import type {CompanySource} from '@/api/company'
import ConnectionTest from '@/components/Settings/ConnectionTest.vue'
import AppDataState from '@/components/Global/AppDataState.vue'
type Kind='ai'|'data'|'data_hk'
type Status={data_public?:{enabled:boolean;tested:boolean};data_hk:{enabled:boolean;provider:string|null;model:string|null;tested:boolean};ai:{enabled:boolean;provider:string|null;model:string|null;tested:boolean};data:{enabled:boolean;provider:string|null;model:string|null;tested:boolean};ollama_location:string}
type HistoryPreview={token:string;packet:{symbol:string;provider_symbol?:string;listing_evidence?:unknown;volume_basis?:string;price_basis?:string;currency:string;from:string;as_of:string;source:string;received_points?:number;retained_points?:number;candles:unknown[]}}
const newsPreview=ref<{token:string;packet:NewsSource}|null>(null);let newsId=''
const companyPreview=ref<{token:string;packet:CompanySource}|null>(null);let companyId=''
const historyMode=ref<'compact'|'full'>('compact')
watch(historyMode,()=>{historyPreview.value=null;historyId='';operations.clear()})
const market=ref('US')
const historyPreview=ref<HistoryPreview|null>(null);let historyId=''
type Quote={symbol:string;currency:string;price:string;previous_close?:string|null;as_of:string;source:string}
const testing=ref(false),aiNotice=ref(''),errorContext=ref('status'),requesting=ref('');let hydrated=false
const router=useRouter(),status=ref<Status|null>(null),statusLoading=ref(false),statusUnavailable=ref(false),error=ref(''),working=ref(false),provider=ref('deepseek'),model=ref('deepseek-flash'),aiKey=ref(''),dataKey=ref(''),hkKey=ref(''),symbol=ref(''),quote=ref<Quote|null>(null),operations=operationCache();let quoteId='',baseline='',statusLoadVersion=0
const busy=computed(()=>working.value||testing.value),dirty=computed(()=>!!aiKey.value||!!dataKey.value||!!hkKey.value||!!quote.value||!!historyPreview.value||!!companyPreview.value||!!newsPreview.value||JSON.stringify([provider.value,model.value])!==baseline)
const configurationMatches=computed(()=>!!status.value?.ai.enabled&&status.value.ai.provider===provider.value&&status.value.ai.model===model.value.trim()&&!aiKey.value)
const statusLabel=(kind:Kind)=>{const c=status.value?.[kind];return c?`${c.enabled?c.provider+' / '+(c.model||'日级价格'):'关闭'} · ${c.tested?'本进程调用成功':'尚未验证真实调用'}`:statusUnavailable.value?'状态不可用，请刷新':'正在读取连接状态'}
async function load():Promise<boolean>{const version=++statusLoadVersion;status.value=null;statusLoading.value=true;statusUnavailable.value=false;error.value='';try{const fresh=await request<Status>('/api/v1/owner/connections');if(version!==statusLoadVersion)return false;status.value=fresh;if(!hydrated){hydrated=true;if(fresh.ai.enabled){provider.value=fresh.ai.provider||'deepseek';model.value=fresh.ai.model||''}baseline=JSON.stringify([provider.value,model.value])}return true}catch(e){if(version===statusLoadVersion){status.value=null;statusUnavailable.value=true;error.value=`连接状态读取失败，请刷新状态。${e instanceof Error?e.message:''}`}return false}finally{if(version===statusLoadVersion)statusLoading.value=false}}
watch(market,()=>{symbol.value='';quote.value=null;historyPreview.value=null;companyPreview.value=null;newsPreview.value=null;operations.clear()});watch(provider,()=>{aiKey.value='';model.value=provider.value==='deepseek'?'deepseek-flash':'';aiNotice.value=''}, {flush:'sync'});watch(symbol,()=>{historyPreview.value=null;historyId='';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';quote.value=null;quoteId='';operations.clear()});watch([model,aiKey],()=>{if(!working.value)aiNotice.value=''}, {flush:'sync'})
async function testSucceeded(){if(await load())aiNotice.value='模型已完成一次真实调用验证。关闭连接、退出登录或重启后需要重新配置。'}
async function configure(kind:Kind){if(busy.value)return;errorContext.value=kind;error.value='';const local=kind==='ai'&&provider.value==='ollama';if(kind==='ai'&&(!model.value.trim()||model.value.includes('@')||(provider.value==='deepseek'&&/^deepseek$/i.test(model.value.trim())))){error.value=provider.value==='deepseek'?'请选择或填写实际模型 ID，例如 deepseek-flash；DeepSeek 是服务名称。':'请填写服务商模型 ID 或已安装的本地模型名，不是账号或邮箱。';return}if(!local&&!(kind==='ai'?aiKey.value:kind==='data'?dataKey.value:hkKey.value).trim()){error.value='请填写你自己的服务商 API Key。';return}working.value=true;try{historyPreview.value=null;historyId='';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';await request('/api/v1/owner/connections','POST',{kind,provider:kind==='ai'?provider.value:kind==='data'?'alphavantage':'eodhd',model:kind==='ai'?model.value.trim():'',key:local?'':kind==='ai'?aiKey.value:kind==='data'?dataKey.value:hkKey.value,enabled:true});baseline=JSON.stringify([provider.value,model.value]);if(kind!=='ai'){quote.value=null;quoteId='';operations.clear()}if(await load()){if(kind==='ai')aiNotice.value='连接配置已保存。Key 输入框已清空，下一步点击下方「测试连接」。';ElMessage.success('连接已配置，尚未发起测试请求')}else ElMessage.warning('配置请求已提交，但状态读取失败，请刷新确认')}catch(e){error.value=e instanceof Error?e.message:'配置失败'}finally{if(kind==='ai')aiKey.value='';else if(kind==='data')dataKey.value='';else hkKey.value='';working.value=false}}
async function disable(kind:Kind){if(busy.value)return;errorContext.value=kind;working.value=true;error.value='';try{historyPreview.value=null;historyId='';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';await request('/api/v1/owner/connections','POST',{kind,provider:'',model:'',key:'',enabled:false});if(kind==='ai'){aiKey.value='';model.value='';baseline=JSON.stringify([provider.value,model.value])}else{if(kind==='data')dataKey.value='';else hkKey.value='';quote.value=null;quoteId=''}if(await load()){if(kind==='ai')aiNotice.value='模型连接已关闭，内存凭据已清除。';ElMessage.success('连接已关闭，内存凭据已清除')}else ElMessage.warning('关闭请求已提交，但状态读取失败，请刷新确认')}catch(e){error.value=e instanceof Error?e.message:'关闭失败'}finally{working.value=false}}
async function fetchQuote(){if(busy.value)return;errorContext.value='market';quote.value=null;quoteId='';error.value='';if(!symbol.value.trim()){error.value=market.value==='US'?'请填写美国市场标的代码。':market.value==='CN'?'请填写受支持的六位沪深 A 股代码。':'请填写四或五位港股代码。';return}working.value=true;requesting.value='quote';try{quote.value=await request<Quote>('/api/v1/owner/quote-fetch','POST',{symbol:symbol.value.trim(),market:market.value},false);quoteId=crypto.randomUUID();operations.clear();await load()}catch(e){error.value=e instanceof Error?e.message:'查询失败，不会自动重试'}finally{requesting.value='';working.value=false}}
async function saveQuote(){if(busy.value||!quote.value)return;working.value=true;error.value='';try{await request('/api/v1/owner/business','POST',operations.body('quote',{id:quoteId,revision:0,kind:'quote',data:{symbol:quote.value.symbol,currency:quote.value.currency,price:quote.value.price,previous_close:quote.value.previous_close??null,as_of:quote.value.as_of,source:quote.value.source}}));quote.value=null;quoteId='';ElMessage.success('价格快照已保存')}catch(e){error.value=e instanceof Error?e.message:'保存失败'}finally{working.value=false}}
async function fetchHistory(){if(busy.value)return;errorContext.value='market';historyPreview.value=null;historyId='';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';error.value='';if(!symbol.value.trim()){error.value=market.value==='US'?'请填写美国市场标的代码。':market.value==='CN'?'请填写受支持的六位沪深 A 股代码。':'请填写四或五位港股代码。';return}working.value=true;requesting.value='history';try{historyPreview.value=await request<HistoryPreview>('/api/v1/owner/market-history-fetch','POST',{symbol:symbol.value.trim(),market:market.value,outputsize:historyMode.value},false);historyId=crypto.randomUUID();operations.clear();await load()}catch(e){error.value=e instanceof Error?e.message:'日线查询失败，不会自动重试'}finally{requesting.value='';working.value=false}}
async function saveHistory(){if(busy.value||!historyPreview.value)return;working.value=true;error.value='';try{await request('/api/v1/owner/market-history','POST',operations.body('market-history',{id:historyId,token:historyPreview.value.token}));historyPreview.value=null;historyId='';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';ElMessage.success('日线来源快照已保存')}catch(e){error.value=e instanceof Error?e.message:'保存失败，预览保留'}finally{working.value=false}}
async function fetchNews(){if(busy.value)return;errorContext.value='market';newsPreview.value=null;newsId='';error.value='';if(!symbol.value.trim()){error.value=market.value==='US'?'请填写美国市场标的代码。':market.value==='CN'?'请填写受支持的六位沪深 A 股代码。':'请填写四或五位港股代码。';return}working.value=true;requesting.value='news';try{newsPreview.value=await request('/api/v1/owner/news-fetch','POST',{symbol:symbol.value.trim()},false);newsId=crypto.randomUUID();operations.clear();await load()}catch(e){error.value=e instanceof Error?e.message:'新闻查询失败，不会自动重试'}finally{requesting.value='';working.value=false}}
async function saveNews(){if(busy.value||!newsPreview.value)return;working.value=true;error.value='';try{await request('/api/v1/owner/news-snapshots','POST',operations.body('news',{id:newsId,token:newsPreview.value.token}));newsPreview.value=null;newsId='';ElMessage.success('新闻来源快照已保存')}catch(e){error.value=e instanceof Error?e.message:'保存失败，预览保留'}finally{working.value=false}}
async function fetchCompany(){if(busy.value)return;errorContext.value='market';companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';error.value='';if(!symbol.value.trim()){error.value=market.value==='US'?'请填写美国市场标的代码。':market.value==='CN'?'请填写受支持的六位沪深 A 股代码。':'请填写四或五位港股代码。';return}working.value=true;requesting.value='company';try{companyPreview.value=await request('/api/v1/owner/company-fetch','POST',{symbol:symbol.value.trim()},false);companyId=crypto.randomUUID();operations.clear();await load()}catch(e){error.value=e instanceof Error?e.message:'公司查询失败，不会自动重试'}finally{requesting.value='';working.value=false}}
async function saveCompany(){if(busy.value||!companyPreview.value)return;working.value=true;error.value='';try{await request('/api/v1/owner/company-snapshots','POST',operations.body('company',{id:companyId,token:companyPreview.value.token}));companyPreview.value=null;companyId='';newsPreview.value=null;newsId='';ElMessage.success('公司资料来源快照已保存')}catch(e){error.value=e instanceof Error?e.message:'保存失败，预览保留'}finally{working.value=false}}
onBeforeRouteLeave(async()=>{if(busy.value)return false;if(!dirty.value)return true;try{await ElMessageBox.confirm('离开会丢弃未保存的配置、测试内容或价格预览。已启用的连接仍保留在当前服务进程。','离开连接设置',{confirmButtonText:'离开',cancelButtonText:'继续编辑'});return true}catch{return false}})
const beforeUnload=(e:BeforeUnloadEvent)=>{if(dirty.value||busy.value){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',beforeUnload);onBeforeUnmount(()=>{aiKey.value='';dataKey.value='';hkKey.value='';window.removeEventListener('beforeunload',beforeUnload)});baseline=JSON.stringify([provider.value,model.value]);load()
</script>
<style scoped>
.configuration-guide {
  margin: 0 0 18px;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.configuration-guide summary { cursor: pointer; font-weight: 600; color: var(--el-text-color-primary); }
.configuration-guide summary:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 4px; }
.configuration-guide ol { margin: 12px 0 0; padding-left: 20px; }
.configuration-guide li + li { margin-top: 8px; }
.configuration-guide a { color: var(--el-color-primary); text-decoration: underline; }

.settings-page {
  padding: 28px 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.settings-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 16px;
  padding: 24px 26px;
  border-radius: 24px;
  border: 1px solid rgba(91, 153, 255, 0.14);
  background:
    radial-gradient(circle at top right, rgba(72, 196, 255, 0.16), transparent 32%),
    linear-gradient(135deg, rgba(10, 27, 54, 0.96), rgba(14, 44, 86, 0.92));
  box-shadow: 0 20px 54px rgba(5, 18, 43, 0.24);
}

.settings-kicker {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #8fd3ff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.settings-title {
  margin: 16px 0 10px;
  font-size: 34px;
  line-height: 1.08;
  color: #f3fbff;
}

.settings-subtitle {
  margin: 0;
  max-width: 720px;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(216, 232, 255, 0.84);
}

.settings-hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.hero-stat {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(7, 20, 42, 0.42);
  border: 1px solid rgba(109, 178, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-stat-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(151, 197, 240, 0.75);
}

.hero-stat b {
  font-size: 20px;
  color: #f5fbff;
}

.hero-stat small {
  color: rgba(185, 211, 242, 0.72);
  font-size: 12px;
}

.settings-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
}

.settings-sidebar,
.settings-panel {
  border-radius: 22px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color-overlay);
  box-shadow: 0 16px 44px rgba(17, 32, 62, 0.08);
}

.settings-sidebar {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-self: start;
  position: sticky;
  top: 28px;
}

.settings-nav-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 16px;
  background: rgba(14, 26, 46, 0.03);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-nav-item:hover {
  border-color: rgba(84, 167, 255, 0.16);
  background: rgba(84, 167, 255, 0.06);
}

.settings-nav-item.is-active {
  border-color: rgba(84, 167, 255, 0.22);
  background: linear-gradient(135deg, rgba(84, 167, 255, 0.12), rgba(33, 108, 231, 0.08));
  color: #0f56cf;
}

.settings-side-note {
  margin-top: 8px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(84, 167, 255, 0.05);
  color: var(--el-text-color-regular);
}

.settings-side-note-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.settings-side-note p {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
}

.settings-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-panel {
  padding: 22px 24px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.panel-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.beta-panel-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-grid {
  display: grid;
  gap: 16px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.surface-card,
.toggle-card,
.security-box,
.data-ownership-box {
  border-radius: 18px;
  border: 1px solid var(--el-border-color-lighter);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.04), rgba(84, 167, 255, 0.01));
}

.surface-card {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}

.surface-card-title,
.toggle-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.surface-card-copy,
.toggle-copy {
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.data-ownership-box {
  margin-top: 14px;
  padding: 18px;
}

.data-ownership-head,
.data-ownership-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.data-ownership-scope {
  flex: 0 0 auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.data-ownership-actions {
  justify-content: flex-end;
  margin-top: 16px;
}

.delete-confirmation {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.delete-confirmation label {
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.delete-confirmation code {
  display: block;
  overflow-wrap: anywhere;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
  color: var(--el-color-danger);
  font-variant-numeric: tabular-nums;
}

.radio-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.toggle-list {
  display: grid;
  gap: 14px;
}

.beta-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.beta-summary-card {
  position: relative;
  overflow: hidden;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(84, 167, 255, 0.14);
  background:
    radial-gradient(circle at top right, rgba(72, 196, 255, 0.14), transparent 36%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.08), rgba(84, 167, 255, 0.018));
}

.beta-summary-card span {
  display: block;
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
}

.beta-summary-card b {
  color: var(--el-text-color-primary);
  font-size: 28px;
  line-height: 1;
}

.beta-section-block {
  margin-top: 16px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid var(--el-border-color-lighter);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(248, 251, 255, 0.92)),
    radial-gradient(circle at top right, rgba(84, 167, 255, 0.08), transparent 42%);
}

.beta-section-title {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 800;
}

.beta-table {
  --el-table-header-bg-color: rgba(84, 167, 255, 0.055);
  --el-table-row-hover-bg-color: rgba(84, 167, 255, 0.055);
}

.beta-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.invite-code-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.toggle-card,
.security-box {
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.data-health {
  margin-bottom: 18px;
  padding: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, rgba(49, 207, 220, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.07), rgba(84, 167, 255, 0.012));
}

.data-health-head,
.data-source-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.data-health-title {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 800;
}

.data-health-copy {
  margin-top: 5px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.data-health-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.data-health-metric {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: var(--el-fill-color-blank);
}

.data-health-metric span,
.data-source-row span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.data-health-metric b {
  display: block;
  margin: 5px 0 8px;
  color: var(--el-text-color-primary);
  font-size: 22px;
}

.data-source-list,
.data-health-anomalies {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.data-source-row {
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.data-source-row strong {
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.data-source-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.data-health-anomaly {
  padding: 9px 12px;
  border-radius: 10px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  background: rgba(230, 162, 60, 0.09);
}

.data-health-anomaly.is-critical {
  color: var(--el-color-danger);
  background: rgba(245, 108, 108, 0.09);
}

.ai-settings {
  display: grid;
  gap: 18px;
}

.ai-fallback-alert {
  border-radius: 14px;
  border-color: rgba(84, 167, 255, 0.18);
  background:
    radial-gradient(circle at top left, rgba(80, 211, 255, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.075), rgba(84, 167, 255, 0.022));
}

.ai-fallback-alert :deep(.el-alert__title) {
  color: var(--el-text-color-primary);
}

.ai-fallback-alert :deep(.el-alert__description) {
  color: var(--el-text-color-secondary);
}

.ai-fallback-alert :deep(.el-alert__icon) {
  color: #61d7ff;
}

.ai-mode-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.ai-mode-grid :deep(.el-radio) {
  width: 100%;
  height: auto;
  min-height: 84px;
  margin: 0;
  padding: 15px 16px;
  align-items: flex-start;
  border-radius: 16px;
}

.ai-mode-grid :deep(.el-radio__input) {
  margin-top: 3px;
}

.ai-mode-grid :deep(.el-radio__label) {
  min-width: 0;
  padding-left: 10px;
  white-space: normal;
}

.ai-mode-copy {
  display: grid;
  gap: 5px;
}

.ai-mode-copy b {
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.ai-mode-copy small,
.ai-mode-panel small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.ai-mode-panel {
  padding: 16px 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 16px;
  background:
    radial-gradient(circle at top right, rgba(49, 207, 220, 0.1), transparent 36%),
    linear-gradient(135deg, rgba(84, 167, 255, 0.07), rgba(84, 167, 255, 0.015));
}

.ai-mode-panel > div {
  display: grid;
  gap: 5px;
}

.ai-mode-panel b {
  color: var(--el-text-color-primary);
  font-size: 17px;
}

.ai-optional-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 14px;
}

.ai-optional-grid.is-guardrail-only {
  grid-template-columns: 1fr;
}

.ai-local-card,
.ai-guardrail-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.055), rgba(84, 167, 255, 0.012));
}

.ai-local-card {
  display: grid;
  gap: 9px;
}

.ai-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ai-local-card b {
  color: var(--el-text-color-primary);
  font-size: 17px;
}

.ai-local-card small,
.ai-guardrail-card li {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.ai-local-meta {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px 10px;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  align-items: center;
}

.ai-local-meta span {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 700;
}

.ai-local-meta code {
  min-width: 0;
  overflow-wrap: anywhere;
  padding: 5px 8px;
  border-radius: 9px;
  color: var(--el-color-primary);
  background: rgba(84, 167, 255, 0.08);
  font-size: 12px;
}

.ai-guardrail-card ul {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
  padding-left: 18px;
}

.ai-detail-label {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ai-provider-form {
  padding: 18px;
  border: 1px solid rgba(84, 167, 255, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at top right, rgba(80, 211, 255, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(84, 167, 255, 0.055), rgba(84, 167, 255, 0.012));
}

.ai-credential-note,
.ai-saved-row,
.ai-last-test {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.ai-credential-note {
  margin-top: -2px;
  line-height: 1.6;
}

.ai-saved-row {
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.ai-last-test {
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(84, 167, 255, 0.05);
}

.ai-last-test b.is-success {
  color: var(--el-color-success);
}

.ai-last-test b.is-failed {
  color: var(--el-color-danger);
}

.ai-actions {
  gap: 10px;
}

.ops-card {
  text-align: left;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--el-border-color-lighter);
  background: linear-gradient(180deg, rgba(84, 167, 255, 0.045), rgba(84, 167, 255, 0.008));
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.ops-card:hover {
  transform: translateY(-2px);
  border-color: rgba(84, 167, 255, 0.2);
  box-shadow: 0 14px 34px rgba(31, 73, 151, 0.1);
}

.ops-card-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.ops-card-copy {
  margin-top: 8px;
  min-height: 42px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--el-text-color-secondary);
}

.ops-card-link {
  display: inline-block;
  margin-top: 12px;
  font-size: 13px;
  font-weight: 700;
  color: #2f7dff;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

@media (max-width: 1240px) {
	  .settings-hero,
	  .settings-layout,
	  .two-columns,
	  .ai-mode-grid,
	  .ai-optional-grid,
	  .ops-grid,
	  .data-health-metrics,
	  .beta-summary-grid {
    grid-template-columns: 1fr;
  }

  .settings-sidebar {
    position: static;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 18px 16px 28px;
  }

  .settings-title {
    font-size: 28px;
  }

  .settings-hero-stats {
    grid-template-columns: 1fr;
  }

  .toggle-card,
  .security-box,
  .data-ownership-head,
  .data-ownership-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .data-ownership-actions .el-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>

<style scoped>.settings-panel p{line-height:1.7;overflow-wrap:anywhere}.settings-panel .el-select{width:100%}.panel-actions{flex-wrap:wrap}.settings-nav-item{width:100%}.surface-card{margin-top:18px}</style>

<style scoped>
.model-actions{justify-content:flex-start;gap:10px}.model-actions .el-button{margin-left:0}.model-presets{display:flex;flex-wrap:wrap;align-items:center;gap:4px}.model-presets a{color:var(--el-color-primary);font-size:13px;margin-left:8px}.connection-feedback{padding:12px 16px;margin-top:16px;border:1px solid var(--el-color-success-light-5);border-radius:12px;color:var(--el-color-success);line-height:1.6;font-size:14px}.model-help{color:var(--el-text-color-secondary);font-size:13px}
</style>
