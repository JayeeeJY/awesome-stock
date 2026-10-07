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
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'||m.type()==='warning'&&/Failed to resolve component/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('portfolio-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const api=async(path,method='GET',body)=>page.evaluate(async({path,method,body})=>{const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='));const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'awesome-owner'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d},{path,method,body});

 const aid=crypto.randomUUID();await api('/api/v1/owner/accounts','POST',{id:aid,name:'Simulation USD',currency:'USD',opening_cash:'1000',operation_id:crypto.randomUUID()});await api('/api/v1/owner/trades','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),account_id:aid,symbol:'TEST',side:'buy',quantity:'2',price:'10',fee:'0',executed_at:new Date().toISOString()});await api('/api/v1/owner/business','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),kind:'quote',data:{symbol:'TEST',currency:'USD',price:'20',as_of:new Date().toISOString().slice(0,10),source:'Synthetic price for simulation'}});


 const decision=await api('/api/v1/owner/documents','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),kind:'decision',title:'Execution basis',symbol:'TEST',content:'Synthetic evidence',support:'Synthetic support',counter_case:'Synthetic contrary',invalidation:'Synthetic stop',risk_limit:'Synthetic limit',review_on:new Date().toISOString().slice(0,10),research_ref:null});await api('/api/v1/owner/plans','POST',{id:crypto.randomUUID(),revision:0,operation_id:crypto.randomUUID(),title:'Execution plan',decision_ref:{id:decision.id,revision:1},plan_type:'build_up',trigger:'Manual review',steps:['First purchase'],risk_limit:'Budget',stop_condition:'Evidence changed',review_on:new Date().toISOString().slice(0,10),status:'ready'});

 await page.goto(base+'/plan/build-up');await page.getByRole('button',{name:'录入实际成交',exact:true}).click();const dialog=page.getByRole('dialog',{name:'录入实际成交并关联计划',exact:true});
 await dialog.getByLabel('成交账户',{exact:true}).press('Enter');await page.getByRole('option').filter({hasText:'Simulation USD'}).click();await dialog.getByLabel('实际成交股数',{exact:true}).fill('1');await dialog.getByLabel('实际成交价格',{exact:true}).fill('10');await dialog.getByLabel('成交费用',{exact:true}).fill('1');await dialog.getByLabel('实际成交时间（本地时间）',{exact:true}).fill(new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16));await dialog.getByLabel('执行说明',{exact:true}).fill('Confirmed synthetic fill');
 await dialog.getByRole('button',{name:'核对并录入成交',exact:true}).click();await page.getByRole('button',{name:'返回核对',exact:true}).click();assert.equal((await api('/api/v1/owner/ledger')).accounts[0].trades.length,1);assert.equal(await dialog.getByLabel('实际成交股数',{exact:true}).inputValue(),'1');
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await dialog.getByRole('button',{name:'核对并录入成交',exact:true}).scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:root+`/qa/plan-trade-${width}.png`,animations:'disabled'});}
 await dialog.getByRole('button',{name:'核对并录入成交',exact:true}).click();await page.getByRole('button',{name:'确认录入并关联',exact:true}).click();await dialog.waitFor({state:'hidden'});await page.getByText('Confirmed synthetic fill',{exact:true}).waitFor();const ledger=await api('/api/v1/owner/ledger');assert.equal(ledger.accounts[0].trades.length,2);assert.equal(ledger.accounts[0].cash,'969');const w=await api('/api/v1/owner/plans');assert.equal(w.executions.length,1);assert.equal(w.executions[0].trade.quantity,'1');assert.deepEqual(errors,[]);fs.writeFileSync(root+'/qa/plan-trade-results.json',JSON.stringify({passed:true,checks:['cancel confirmation leaves ledger unchanged','inputs preserved','explicit fill and association','cash includes fee','three viewports']}));console.log('Plan trade browser passed');
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
