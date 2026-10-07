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
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const {chromium}=createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE || path.join(root,'package.json'))('playwright');
const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-vue-browser-')));
fs.chmodSync(dir,0o700);
fs.mkdirSync(path.join(root,'qa'),{recursive:true});
const port=await new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const p=socket.address().port;socket.close(()=>resolve(p));});});
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.OWNER_PYTHON || 'python3',['start_owner.py','--port',String(port),'--data-dir',path.join(dir,'data')],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,serverErrors='';server.stderr.on('data',d=>serverErrors+=d);
try {
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(serverErrors || 'server exited');try{if((await fetch(base+'/api/v1/owner/status')).ok)break}catch{}await delay(100)}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/422|503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('portfolio-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const api=async(path,method='GET',body)=>page.evaluate(async({path,method,body})=>{const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='));const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'awesome-owner'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d},{path,method,body});

 const aid=crypto.randomUUID();await api('/api/v1/owner/accounts','POST',{id:aid,name:'Simulation USD',currency:'USD',opening_cash:'1000',operation_id:crypto.randomUUID()});await api('/api/v1/owner/trades','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),account_id:aid,symbol:'TEST',side:'buy',quantity:'2',price:'10',fee:'0',executed_at:new Date().toISOString()});await api('/api/v1/owner/business','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),kind:'quote',data:{symbol:'TEST',currency:'USD',price:'20',as_of:new Date().toISOString().slice(0,10),source:'Synthetic price for simulation'}});

 await page.goto(base+'/plan/pre-trade');await page.getByLabel('标的代码',{exact:true}).fill('TEST');await page.getByLabel('假设成交价格',{exact:true}).fill('20');await page.getByLabel('数量',{exact:true}).fill('1');await page.getByLabel('单笔 / 每批费用',{exact:true}).fill('1');await page.getByLabel('用户仓位上限 %',{exact:true}).fill('100');await page.getByRole('button',{name:'加入当前交易',exact:true}).click();
 await page.getByLabel('标的代码',{exact:true}).fill('NEW');await page.getByLabel('假设成交价格',{exact:true}).fill('10');await page.getByRole('button',{name:'加入当前交易',exact:true}).click();assert.equal(await page.locator('.sequence-row').count(),2);
 await page.getByRole('button',{name:'计算影响',exact:true}).click();await page.locator('.results-section').waitFor();assert.match(await page.locator('.results-section').innerText(),/948.00/);assert.equal(await page.locator('.results-section .el-table__body tbody tr').count(),2);
 await page.getByRole('button',{name:'打开 Ask Awesome 助手',exact:true}).click();const ask=page.getByRole('dialog',{name:'Ask Awesome',exact:true});await openAskMaterials(ask);await ask.getByRole('button',{name:'载入当前页面材料',exact:true}).click();await ask.getByText('核对载入的材料',{exact:true}).waitFor();const material=JSON.parse(await ask.locator('.assistant-scroll > details pre').textContent()).material;assert.equal(material.scope,'current_planning_preview');assert.equal(material.input.type,'pre_trade_batch');assert.equal(material.input.trades.length,2);assert.equal(material.account.id,aid);assert.equal(material.result.type,'pre_trade_batch');assert.ok(!('records' in material));await ask.getByRole('button',{name:'关闭助手',exact:true}).click();
 await page.getByRole('button',{name:'保存固定试算快照',exact:true}).click();await page.getByRole('button',{name:'快照已保存',exact:true}).waitFor();const saved=(await api('/api/v1/owner/business')).records.find(r=>r.kind==='scenario');assert.equal(saved.input.type,'pre_trade_batch');assert.equal(saved.input.trades.length,2);assert.equal((await api('/api/v1/owner/ledger')).accounts[0].trades.length,1);
 await page.locator('.sequence-row').nth(1).getByRole('button',{name:'上移',exact:true}).click();assert.equal(await page.locator('.results-section').count(),0);assert.match(await page.locator('.sequence-row').first().innerText(),/NEW/);
 await page.getByRole('button',{name:'打开 Ask Awesome 助手',exact:true}).click();await openAskMaterials(ask);await ask.getByRole('button',{name:'载入当前页面材料',exact:true}).click();await ask.getByText('请先完成当前试算并关闭历史窗口，再载入材料；输入变化后需要重新计算。',{exact:true}).waitFor();assert.deepEqual(JSON.parse(await ask.locator('.assistant-scroll > details pre').textContent()).material,material);await ask.getByRole('button',{name:'关闭助手',exact:true}).click();
 await page.getByRole('button',{name:'查看固定快照',exact:true}).click();await page.getByRole('button',{name:'在助手中核对这份历史快照',exact:true}).click();await openAskMaterials(ask);await ask.getByRole('button',{name:'载入当前页面材料',exact:true}).click();await page.waitForFunction(()=>{const e=document.querySelector('.assistant-scroll > details pre');return e&&JSON.parse(e.textContent).material.scope==='fixed_simulation_snapshot'});const historical=JSON.parse(await ask.locator('.assistant-scroll > details pre').textContent()).material;assert.equal(historical.snapshot.id,saved.id);assert.equal(historical.snapshot.input.trades[0].symbol,'TEST');assert.deepEqual(historical.snapshot.result,saved.result);await ask.getByRole('button',{name:'关闭助手',exact:true}).click();await page.getByRole('button',{name:'改用当前页面材料',exact:true}).click();
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.locator('.el-message').first().waitFor({state:'hidden'});await page.locator('.sequence-row').first().scrollIntoViewIfNeeded();await page.screenshot({path:root+`/qa/p46-batch-${width}.png`,animations:'disabled'});}
 assert.deepEqual(errors,[]);fs.writeFileSync(root+'/qa/p46-batch-results.json',JSON.stringify({passed:true,checks:['two real UI legs','exact fees and cash','snapshot records sequence','reorder invalidates result','no actual trade created','three viewports']}));console.log('P46 batch browser passed');
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}


async function openAskMaterials(panel){const options=panel.locator('.page-material-options');if(!await options.evaluate(e=>e.open))await options.locator(':scope > summary').click()}
