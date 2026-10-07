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
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-messages-evidence-'));console.log('Messages evidence: '+output);
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
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type())&&!/422|503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('portfolio-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const api=async(path,method='GET',body)=>page.evaluate(async({path,method,body})=>{const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='));const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'awesome-owner'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d},{path,method,body});

 const today=new Date().toISOString().slice(0,10);
 for(const title of ['Review first','Review tomorrow','Review ignored'])await api('/api/v1/owner/documents','POST',{id:crypto.randomUUID(),operation_id:crypto.randomUUID(),revision:0,kind:'decision',title,symbol:'TEST',content:'Synthetic judgment',support:'Synthetic support',counter_case:'Synthetic counter',invalidation:'Synthetic condition',risk_limit:'Synthetic limit',review_on:today,research_ref:null});
 await page.reload();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const bell=page.getByRole('button',{name:'打开消息中心',exact:true}),panel=page.getByRole('region',{name:'消息中心',exact:true});
 assert.ok((await page.title()).includes('Awesome'));assert.ok(page.url().includes('/portfolio/accounts'));await bell.click();await panel.getByText('复核：Review first',{exact:true}).waitFor();
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:1000});await page.waitForTimeout(200);const box=await panel.boundingBox();assert.ok(box&&box.x>=0&&box.x+box.width<=width);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:path.join(output,`messages-${width}.png`),animations:'disabled'})}
 const row=title=>panel.locator('.notif-item').filter({hasText:title});
 await row('Review first').getByRole('button',{name:'完成',exact:true}).click();await row('Review first').waitFor({state:'hidden'});
 await row('Review tomorrow').getByRole('button',{name:'明天',exact:true}).click();await row('Review tomorrow').waitFor({state:'hidden'});
 await row('Review ignored').getByRole('button',{name:'忽略',exact:true}).click();const prompt=page.getByRole('dialog',{name:'忽略提醒',exact:true});await prompt.getByRole('button',{name:'忽略',exact:true}).click();await prompt.getByText('请填写忽略原因',{exact:true}).waitFor();await prompt.locator('input').fill('Synthetic reason');await prompt.getByRole('button',{name:'忽略',exact:true}).click();await prompt.waitFor({state:'hidden'});await row('Review ignored').waitFor({state:'hidden'});
 if(!(await panel.isVisible()))await bell.click();await panel.getByText('稍后提醒',{exact:true}).click();await row('Review tomorrow').waitFor();const actions=(await api('/api/v1/owner/business')).actions;assert.equal(actions.find(a=>a.title==='复核：Review first').status,'resolved');assert.equal(actions.find(a=>a.title==='复核：Review ignored').feedback.reason,'Synthetic reason');assert.equal(actions.find(a=>a.title==='复核：Review tomorrow').status,'snoozed');
 await panel.getByRole('button',{name:'行动收件箱',exact:true}).click();await page.getByRole('dialog',{name:'行动收件箱',exact:true}).waitFor();await page.locator('.el-drawer__close-btn').click();await bell.click();await row('Review tomorrow').getByRole('button',{name:'复核：Review tomorrow',exact:true}).click();await page.waitForURL('**/decisions?id=*');assert.deepEqual(errors,[]);fs.writeFileSync(resultPath,JSON.stringify({passed:true,widths:[1440,390,320],quick_resolve:true,utc_snooze:true,ignore_reason_required:true,source_route:true,inbox:true,errors,real_provider:false}));console.log('Messages browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
