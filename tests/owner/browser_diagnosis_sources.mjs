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
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-diagnosis-sources-'));console.log('Diagnosis sources evidence: '+output);
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

 const aid=crypto.randomUUID();await api('/api/v1/owner/accounts','POST',{id:aid,operation_id:crypto.randomUUID(),name:'Synthetic sources',currency:'USD',opening_cash:'1000'});await api('/api/v1/owner/trades','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,account_id:aid,symbol:'TEST',side:'buy',quantity:'2',price:'10',fee:'0',executed_at:new Date().toISOString()});await api('/api/v1/owner/business','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,kind:'quote',data:{symbol:'TEST',currency:'USD',price:'20',as_of:new Date().toISOString().slice(0,10),source:'Synthetic quote'}});
 await page.goto(base+'/settings/connections');await page.locator('.el-select').filter({has:page.getByRole('combobox',{name:'行情来源',exact:true})}).locator('.el-select__wrapper').click();await page.getByRole('option',{name:'自有 API · Alpha Vantage / EODHD',exact:true}).click();await page.getByLabel('你自己的 Alpha Vantage API Key',{exact:true}).fill('Synthetic-source-key');await page.getByRole('button',{name:'启用行情连接',exact:true}).click();await page.getByLabel('美国市场标的代码',{exact:true}).fill('TEST');await page.getByRole('button',{name:'主动查询公司资料',exact:true}).click();await page.getByRole('button',{name:'确认保存公司资料',exact:true}).click();await delay(1100);await page.getByRole('button',{name:'主动查询相关新闻',exact:true}).click();await page.getByRole('button',{name:'确认保存新闻来源',exact:true}).click();await page.getByText('新闻来源快照已保存',{exact:true}).waitFor();
 await page.goto(base+'/review/diagnosis');await page.getByRole('button',{name:'核对 TEST 已保存来源',exact:true}).click();await page.locator('.saved-source-proposal').getByText(/Synthetic Company/).waitFor();await page.getByRole('button',{name:'核对后采用 TEST 来源',exact:true}).click();assert.equal(await page.getByLabel('TEST 公司归属',{exact:true}).inputValue(),'Synthetic Company');assert.equal(await page.getByLabel('TEST 公司归属',{exact:true}).isDisabled(),true);await page.getByRole('button',{name:'运行诊断预览',exact:true}).click();await page.getByRole('button',{name:'保存本次诊断',exact:true}).click();const saved=(await api('/api/v1/owner/diagnosis-history','POST',{account_id:aid})).reports[0];assert.equal(saved.report.holding_context.TEST.news,'negative');assert.equal(saved.report.holding_context.TEST.source_evidence.verification,'supplier_unverified');
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await page.getByRole('button',{name:'核对 TEST 已保存来源',exact:true}).scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:path.join(output,`diagnosis-sources-${width}.png`),animations:'disabled'})}
 await page.getByRole('button',{name:'改为手工观察',exact:true}).click();assert.equal(await page.getByLabel('TEST 公司归属',{exact:true}).isDisabled(),false);assert.equal(await page.getByLabel('TEST 资料来源',{exact:true}).inputValue(),'');assert.deepEqual(errors,[]);assert.equal(JSON.parse(fs.readFileSync(path.join(dir,'calls.json'))).length,2);fs.writeFileSync(resultPath,JSON.stringify({passed:true,widths:[1440,390,320],explicit_adoption:true,unverified_preserved:true,fixed_source_versions:true,manual_clears_binding:true,provider_calls:2,errors,real_provider:false}));console.log('Diagnosis sources browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
