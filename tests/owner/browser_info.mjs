import {workspaceNav} from './browser_navigation.mjs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import net from 'node:net';
import {spawn,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const req=createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE||path.join(root,'package.json'));
const {chromium}=req('playwright');
const python=(process.env.OWNER_PYTHON||'python3');
const temp=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-owner-browser-')));fs.chmodSync(temp,0o700);
const data=path.join(temp,'data'),qa=path.join(root,'qa');fs.mkdirSync(qa,{recursive:true});
const port=await new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
const base=`http://127.0.0.1:${port}`,password='Synthetic-browser-only-2026',newPassword='Synthetic-browser-new-2026';
let child,browser;
async function start(directory){child=spawn(python,['tests/owner/serve_legacy_fixture.py','--port',String(port),'--data-dir',directory],{cwd:root,stdio:'ignore',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});for(let i=0;i<100;i++){if(child.exitCode!==null)throw Error('server exited');try{if((await fetch(base+'/api/v1/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,50));}throw Error('server did not start');}
async function stop(){if(child&&child.exitCode===null){const p=new Promise(r=>child.once('exit',r));child.kill('SIGTERM');await p;}child=null;}
async function message(page,part){await page.waitForFunction(p=>document.getElementById('message').textContent.includes(p),part);}
async function login(page,pwd=password){await page.locator('#auth').waitFor({state:'visible'});await page.locator('#username').fill('synthetic-owner');await page.locator('#password').fill(pwd);await page.locator('#auth-submit').click();await message(page,'已登录本地账本');}
async function ledger(page){return page.evaluate(async()=>(await fetch('/api/v1/owner/ledger')).json());}
async function saveTrade(page,side,quantity,price,when){await page.locator('#symbol').fill('TEST');await page.locator('#side').selectOption(side);await page.locator('#quantity').fill(quantity);await page.locator('#price').fill(price);await page.locator('#fee').fill('1');await page.locator('#executed-at').fill(when);await page.locator('#save-trade').click();await message(page,'交易已保存');}
try{
 await start(data);browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:960}});const problems=[];page.on('pageerror',e=>problems.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type()))problems.push(m.text());});
 await page.goto(base+'/academy');await page.locator('#auth').waitFor({state:'visible'});assert.equal(await page.locator('#workspace').isVisible(),false);
 await page.locator('#username').fill('synthetic-owner');await page.locator('#password').fill(password);await page.locator('#confirm-password').fill(password);await page.locator('#auth-submit').click();await message(page,'已登录本地账本');
 assert.equal(await page.title(),'Academy · 投资知识 · Awesome Stock');assert.equal(await page.locator('#academy-list button').count(),8);assert.equal(await page.locator('#academy-reading [role="img"]').count(),1);
 const before=await ledger(page);
 await page.locator('#academy-search').fill('RSI');assert.equal(await page.locator('#academy-list button').count(),1);assert.match(await page.locator('#academy-reading h2').textContent(),/RSI/);
 await page.locator('#academy-search').fill('没有匹配的虚构关键词');assert.match(await page.locator('#academy-reading').textContent(),/没有匹配/);
 await page.locator('#academy-search').fill('');await page.locator('#academy-category').selectOption('options');assert.equal(await page.locator('#academy-list button').count(),3);await page.locator('#academy-list button').last().click();assert.match(await page.locator('#academy-reading h2').textContent(),/希腊/);
 await page.locator('#academy-category').selectOption('all');const titles=await page.locator('#academy-list button').allTextContents();for(const title of titles){await page.locator('#academy-list').getByRole('button',{name:title,exact:true}).click();assert.equal(await page.locator('#academy-reading [role="img"]').count(),1);assert.equal(await page.locator('#academy-reading h3').count(),4);}
 await page.locator('#academy-search').fill('RSI');await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(qa,'academy-owner-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(qa,'academy-owner-mobile.png'),fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.locator('#academy-reading').getByRole('link',{name:'我的计划',exact:true}).click();await page.locator('#plans-panel').waitFor({state:'visible'});assert.equal(new URL(page.url()).pathname,'/plans');await page.goBack();await page.locator('#academy-panel').waitFor({state:'visible'});
 await workspaceNav(page,'settings');await page.locator('#settings-panel').waitFor({state:'visible'});assert.equal(await page.title(),'Settings · 本地设置 · Awesome Stock');assert.match(await page.locator('#settings-storage').textContent(),new RegExp(data.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
 assert.equal(await page.locator('#password-form').isVisible(),false);await page.locator('#settings-tab-data').click();await page.locator('#settings-panel summary').filter({hasText:'如何恢复备份'}).click();assert.match(await page.locator('#settings-panel pre').textContent(),/--restore-from/);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.locator('#settings-backup').click();await message(page,'本地备份已完成');assert.match(await page.locator('#settings-backup-result').textContent(),/本次已创建备份/);const backupName=fs.readdirSync(path.join(data,'backups'))[0];assert.deepEqual(await ledger(page),before);
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(qa,'settings-owner-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:960});await page.screenshot({path:path.join(qa,'settings-owner-desktop.png'),fullPage:true});
 await page.locator('#settings-tab-account').click();await page.locator('#settings-panel summary').filter({hasText:'修改本地口令'}).click();await page.locator('#old-password').fill(password);await page.locator('#new-password').fill(newPassword);await page.locator('#repeat-password').fill(newPassword);await page.locator('#password-form button').click();await message(page,'口令已修改');await login(page,newPassword);await page.locator('#settings-panel').waitFor({state:'visible'});
 await stop();await start(data);await page.reload();await login(page,newPassword);await page.locator('#settings-panel').waitFor({state:'visible'});assert.deepEqual(await ledger(page),before);
 await stop();const restored=path.join(temp,'restored');const result=spawnSync(python,['start_owner.py','--restore-from',path.join(data,'backups',backupName),'--data-dir',restored],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});assert.equal(result.status,0,result.stderr);await start(restored);await page.reload();await login(page,password);await page.locator('#settings-panel').waitFor({state:'visible'});assert.ok((await page.locator('#settings-storage').textContent()).includes(restored));assert.deepEqual(await ledger(page),before);
 await page.locator('#logout').click();await message(page,'已退出');assert.equal(await page.locator('#settings-account').textContent(),'');assert.equal(await page.locator('#settings-storage').textContent(),'');assert.equal(await page.locator('#settings-backup-result').textContent(),'');
 assert.deepEqual(problems,[]);const summary={passed:true,consoleErrors:0,mobileOverflow:false,checks:['all eight documents and diagrams','search and empty results','category filter','workspace link and browser back','settings actual custom data directory','backup creation','password change and relogin','direct settings route after restart','restore changes displayed directory and restores backup credential','logout clears private settings'],viewports:['1440x960','390x844'],browser:'Playwright Chromium; Browser plugin not available'};fs.writeFileSync(path.join(qa,'info-browser-result.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
}finally{await browser?.close();await stop();fs.rmSync(temp,{recursive:true,force:true});}
