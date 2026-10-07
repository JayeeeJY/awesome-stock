// Isolated synthetic account; configuring Ollama does not make a model request.
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
const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-connection-status-')));fs.chmodSync(dir,0o700);
const port=await new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const p=socket.address().port;socket.close(()=>resolve(p));});});
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.OWNER_PYTHON||'python3',['start_owner.py','--port',String(port),'--data-dir',path.join(dir,'data')],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,serverErrors='';server.stderr.on('data',d=>serverErrors+=d);
try{
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(serverErrors||'server exited');try{if((await fetch(base+'/api/v1/owner/status')).ok)break}catch{}await delay(100)}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:390,height:900}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('connection-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Connection-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Connection-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 await page.goto(base+'/settings/connections');await page.locator('.el-select').filter({has:page.getByRole('combobox',{name:'行情来源',exact:true})}).locator('.el-select__wrapper').click();await page.getByRole('option',{name:'自有 API · Alpha Vantage / EODHD',exact:true}).click();await page.getByText('关闭 · 尚未验证真实调用',{exact:true}).first().waitFor();
 await page.getByRole('combobox',{name:'模型服务'}).press('Enter');await page.getByRole('option',{name:/Ollama/}).click();await page.getByLabel('模型 ID（不是服务名称或邮箱）',{exact:true}).fill('synthetic-local');assert.equal(await page.getByLabel('你自己的模型服务 API Key').count(),0);
 await page.getByRole('button',{name:'保存模型连接',exact:true}).click();await page.getByText('ollama / synthetic-local · 尚未验证真实调用',{exact:true}).waitFor();await page.getByText('连接已配置，尚未发起测试请求',{exact:true}).waitFor({state:'hidden'});
 const fail=route=>route.request().method()==='GET'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'synthetic_read_failure',message:'Synthetic status failure'}})}):route.continue();
 await page.route('**/api/v1/owner/connections',fail);await page.getByRole('button',{name:'刷新状态',exact:true}).click();await page.getByText('连接状态读取失败',{exact:true}).waitFor();await page.getByText('状态不可用，请刷新',{exact:true}).first().waitFor();assert.equal(await page.getByText('状态不可用，请刷新',{exact:true}).count(),3);assert.equal(await page.getByText('ollama / synthetic-local · 尚未验证真实调用',{exact:true}).count(),0);
 await page.getByText('状态不可用，请刷新',{exact:true}).first().scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:root+'/qa/p182-connection-status-failed-390.png',animations:'disabled'});
 await page.unroute('**/api/v1/owner/connections');await page.getByRole('button',{name:'刷新状态',exact:true}).click();await page.getByText('ollama / synthetic-local · 尚未验证真实调用',{exact:true}).waitFor();await page.getByText('连接状态读取失败',{exact:true}).waitFor({state:'hidden'});
 await page.route('**/api/v1/owner/connections',fail);await page.getByRole('button',{name:'关闭模型连接',exact:true}).click();await page.getByText('关闭请求已提交，但状态读取失败，请刷新确认',{exact:true}).waitFor();await page.getByText('状态不可用，请刷新',{exact:true}).first().waitFor();assert.equal(await page.getByText('ollama / synthetic-local · 尚未验证真实调用',{exact:true}).count(),0);
 await page.unroute('**/api/v1/owner/connections');await page.getByRole('button',{name:'刷新状态',exact:true}).click();await page.getByText('关闭 · 尚未验证真实调用',{exact:true}).first().waitFor();await page.getByText('连接状态读取失败',{exact:true}).waitFor({state:'hidden'});await page.getByText('关闭 · 尚未验证真实调用',{exact:true}).first().scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:root+'/qa/p182-connection-status-recovered-390.png',animations:'disabled'});
 assert.deepEqual(errors,[]);fs.writeFileSync(root+'/qa/p182-connection-status-results.json',JSON.stringify({passed:true,checks:['BYO local model configuration without key or provider request','failed status read withdraws stale enabled state','status retry restores current state','disable succeeds but subsequent status failure is reported as unconfirmed','390px no page overflow']},null,2)+'\n');console.log('P182 connection status browser passed');
}finally{if(browser)await browser.close();if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}fs.rmSync(dir,{recursive:true,force:true});}
