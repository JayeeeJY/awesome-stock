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
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-snapshot-trend-'));console.log('Snapshot trend evidence: '+output);
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

 const aid=crypto.randomUUID(),today=new Date().toISOString().slice(0,10);await api('/api/v1/owner/accounts','POST',{id:aid,operation_id:crypto.randomUUID(),name:'Synthetic snapshots',currency:'USD',opening_cash:'1000'});
 const trade=async symbol=>api('/api/v1/owner/trades','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,account_id:aid,symbol,side:'buy',quantity:symbol==='TEST'?'2':'1',price:'10',fee:'0',executed_at:new Date().toISOString()});
 const quote=async(symbol,price)=>api('/api/v1/owner/business','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,kind:'quote',data:{symbol,currency:'USD',price,as_of:today,source:'Synthetic snapshot price'}});
 const input={account_id:aid,policy:{warning_percent:'20',max_percent:'30',shock_percent:'10',custom_rules:[]},holding_context:{}};
 const capture=async()=>{const preview=await api('/api/v1/owner/diagnosis-preview','POST',input);return api('/api/v1/owner/daily-capture','POST',{operation_id:crypto.randomUUID(),input,expected_token:preview.token})};
 await trade('TEST');await quote('TEST','20');const first=await capture();await quote('TEST','25');await capture();await trade('OTHER');await capture();await quote('OTHER','10');await capture();
 const historyBefore=await api('/api/v1/owner/daily-history','POST',{account_id:aid});await page.goto(base+'/review/diagnosis');const chart=page.locator('.snapshot-history');await chart.getByRole('img',{name:'固定快照持仓市值趋势',exact:true}).waitFor();assert.equal(await chart.locator('.snapshot-point').count(),3);assert.equal(await chart.locator('.snapshot-segment').count(),1);await chart.locator('summary').click();assert.match(await chart.innerText(),/40.00 USD/);assert.match(await chart.innerText(),/50.00 USD/);assert.match(await chart.innerText(),/60.00 USD/);assert.match(await chart.innerText(),/估值资料不足/);
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await chart.scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:path.join(output,`snapshot-trend-${width}.png`),animations:'disabled'})}
 await quote('TEST','100');await page.reload();await chart.locator('.snapshot-point').first().waitFor();assert.equal(await chart.locator('.snapshot-segment').count(),1);assert.deepEqual(await api('/api/v1/owner/daily-history','POST',{account_id:aid}),historyBefore);await chart.locator('.snapshot-point').first().focus();await page.keyboard.press('Enter');await page.waitForURL('**/review/diagnosis?id='+first.brief.id);await page.locator('.linked-daily').waitFor();assert.deepEqual(errors,[]);fs.writeFileSync(resultPath,JSON.stringify({passed:true,widths:[1440,390,320],fixed_values:[40,50,null,60],missing_break:true,history_unchanged:true,keyboard_source_link:true,errors,real_provider:false}));console.log('Snapshot trend browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
