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
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-news-evidence-'));console.log('News evidence: '+output);
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

 await page.goto(base+'/settings/connections');await page.getByLabel('你自己的 Alpha Vantage API Key',{exact:true}).fill('synthetic-browser-key');await page.getByRole('button',{name:'启用行情连接',exact:true}).click();await page.getByLabel('美国市场标的代码',{exact:true}).fill('TEST');await page.getByRole('button',{name:'主动查询相关新闻',exact:true}).click();const panel=page.locator('main .news-evidence');await panel.getByText('Synthetic company event',{exact:true}).waitFor();assert.equal((await api('/api/v1/owner/news-source','POST',{symbol:'TEST'})).snapshot,null);assert.equal(await page.evaluate(()=>window.newsExecuted),undefined);await page.getByRole('button',{name:'确认保存新闻来源',exact:true}).click();await page.getByText('新闻来源快照已保存',{exact:true}).waitFor();const saved=(await api('/api/v1/owner/news-source','POST',{symbol:'TEST'})).snapshot;assert.equal(saved.verification,'supplier_unverified');
 const aid=crypto.randomUUID();await api('/api/v1/owner/accounts','POST',{id:aid,operation_id:crypto.randomUUID(),name:'Synthetic news position',currency:'USD',opening_cash:'1000'});await api('/api/v1/owner/trades','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,account_id:aid,symbol:'TEST',side:'buy',quantity:'1',price:'10',fee:'0',executed_at:new Date().toISOString()});await api('/api/v1/owner/business','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,kind:'quote',data:{symbol:'TEST',currency:'USD',price:'10',as_of:new Date().toISOString().slice(0,10),source:'Synthetic price'}});
 await page.goto(base+'/research');await page.getByLabel('标的代码',{exact:true}).fill('TEST');await page.getByRole('button',{name:'载入本地研究材料',exact:true}).click();await panel.getByText('Synthetic company event',{exact:true}).waitFor();await panel.getByText('供应商情绪标签：Somewhat-Bearish · 原始分数：-0.2 · 未人工核验',{exact:true}).waitFor();await page.locator('main .position-evidence').getByText('供应商将近期新闻标为负面 · 未人工核验',{exact:true}).waitFor();await page.locator('main .memory-evidence').getByText('Synthetic company event',{exact:true}).waitFor();assert.equal(await panel.locator('a').getAttribute('rel'),'noopener noreferrer');assert.equal(await page.evaluate(()=>window.newsExecuted),undefined);
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await panel.scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:path.join(output,`news-${width}.png`),animations:'disabled'})}
 await page.getByRole('button',{name:'预览报告 · 查看历史',exact:true}).click();const report=page.getByRole('dialog',{name:'固定研究报告',exact:true});await report.getByRole('button',{name:'第一步：预览当前报告',exact:true}).click();await report.locator('.news-evidence').getByText('Synthetic company event',{exact:true}).waitFor();await report.getByRole('button',{name:'第二步：确认保存这份报告',exact:true}).click();await report.getByText('已保存固定报告',{exact:true}).waitFor();assert.equal((await api('/api/v1/owner/research-reports')).reports[0].packet.news_source.id,saved.id);assert.ok((await api('/api/v1/owner/research-reports')).reports[0].packet.position_intelligence.context_signals.some(s=>s.code==='negative_news'));assert.deepEqual(errors,[]);assert.equal(JSON.parse(fs.readFileSync(path.join(dir,'calls.json'))).length,1);fs.writeFileSync(resultPath,JSON.stringify({passed:true,provider_calls:1,preview_writes:0,fixed_source:true,news_memory:true,supplier_sentiment:true,negative_news_signal:true,widths:[1440,390,320],errors,real_provider:false}));console.log('News browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
