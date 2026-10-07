// Default shipped Vue runtime; all records and downloads are isolated synthetic fixtures.
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-china-market-'));console.log('China market evidence: '+output);
const {chromium}=createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE || path.join(root,'package.json'))('playwright');
const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-vue-browser-')));
fs.chmodSync(dir,0o700);
fs.mkdirSync(path.join(root,'qa'),{recursive:true});
const port=await new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const p=socket.address().port;socket.close(()=>resolve(p));});});
const base=`http://127.0.0.1:${port}`;
const resultPath=path.join(output,'result.json');
const server=spawn(process.env.OWNER_PYTHON || 'python3',['tests/owner/serve_market_fixture.py','--port',String(port),'--data-dir',path.join(dir,'data')],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,serverErrors='';server.stderr.on('data',d=>serverErrors+=d);
try {
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(serverErrors || 'server exited');try{if((await fetch(base+'/api/v1/owner/status')).ok)break}catch{}await delay(100)}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/422|503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('portfolio-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const api=async(path,method='GET',body)=>page.evaluate(async({path,method,body})=>{const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='));const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'awesome-owner'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d},{path,method,body});

 await page.goto(base+'/settings/connections');await page.locator('.el-select').filter({has:page.getByRole('combobox',{name:'行情来源',exact:true})}).locator('.el-select__wrapper').click();await page.getByRole('option',{name:'自有 API · Alpha Vantage / EODHD',exact:true}).click();await page.getByLabel('你自己的 Alpha Vantage API Key',{exact:true}).fill('synthetic-china-key');await page.getByRole('button',{name:'启用行情连接',exact:true}).click();await page.locator('.el-select').filter({has:page.getByRole('combobox',{name:'行情市场',exact:true})}).locator('.el-select__wrapper').click();await page.getByRole('option',{name:'沪深 A 股 · CNY',exact:true}).click();await page.getByLabel('沪深 A 股代码',{exact:true}).fill('600104');assert.equal(await page.getByRole('button',{name:'主动查询公司资料',exact:true}).isDisabled(),true);assert.equal(await page.getByRole('button',{name:'主动查询相关新闻',exact:true}).isDisabled(),true);
 await page.getByRole('button',{name:'主动查询日级价格',exact:true}).click();await page.getByRole('heading',{name:'600104 · CNY 20',exact:true}).waitFor();await page.getByRole('button',{name:'确认保存价格快照',exact:true}).click();await page.getByText('价格快照已保存',{exact:true}).waitFor();await delay(1100);await page.getByRole('button',{name:'主动查询最近日线',exact:true}).click();await page.getByRole('heading',{name:'600104 · 90 根日线',exact:true}).waitFor();assert.equal((await api('/api/v1/owner/market-history')).snapshots.length,0);await page.getByRole('button',{name:'确认保存日线快照',exact:true}).click();await page.getByText('日线来源快照已保存',{exact:true}).waitFor();const saved=(await api('/api/v1/owner/market-history')).snapshots[0];assert.equal(saved.currency,'CNY');assert.equal(saved.price_basis,'raw_unadjusted');assert.equal(saved.date_basis,'Asia/Shanghai');
 await page.goto(base+'/research');await page.getByLabel('标的代码',{exact:true}).fill('600104');await page.getByRole('button',{name:'载入本地研究材料',exact:true}).click();const technical=page.locator('main .technical-evidence');await technical.getByText('趋势：上行排列 · RSI14：100',{exact:true}).waitFor();assert.ok((await technical.innerText()).includes('CNY'));assert.ok(!(await technical.innerText()).includes('USD'));
 await page.getByRole('button',{name:'预览报告 · 查看历史',exact:true}).click();const report=page.getByRole('dialog',{name:'固定研究报告',exact:true});await report.getByRole('button',{name:'第一步：预览当前报告',exact:true}).click();await report.locator('.technical-evidence').getByText('趋势：上行排列 · RSI14：100',{exact:true}).waitFor();await report.getByRole('button',{name:'第二步：确认保存这份报告',exact:true}).click();await report.getByText('已保存固定报告',{exact:true}).waitFor();const fixed=(await api('/api/v1/owner/research-reports')).reports[0];assert.equal(fixed.packet.market_technical.source.id,saved.id);assert.equal(fixed.packet.market_technical.source.currency,'CNY');await report.getByRole('button',{name:'关闭固定报告',exact:true}).click();await report.waitFor({state:'hidden'});
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await technical.scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:path.join(output,`china-market-${width}.png`),animations:'disabled'})}
 assert.deepEqual(errors,[]);assert.equal(JSON.parse(fs.readFileSync(path.join(dir,'calls.json'))).length,2);fs.writeFileSync(resultPath,JSON.stringify({passed:true,widths:[1440,390,320],currency:'CNY',price_basis:'raw_unadjusted',confirmed_quote_and_history:true,fixed_research:true,unsupported_company_news_disabled:true,provider_calls:2,errors,real_provider:false}));console.log('China market browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
