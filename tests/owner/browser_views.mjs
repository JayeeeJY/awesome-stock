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
 await page.goto(base+'/ledger');await page.locator('#auth').waitFor({state:'visible'});assert.match(await page.locator('#auth-title').textContent(),/创建本地账号/);
 await page.locator('#username').fill('synthetic-owner');await page.locator('#password').fill(password);await page.locator('#confirm-password').fill(password);await page.locator('#auth-submit').click();await message(page,'已登录本地账本');assert.deepEqual((await ledger(page)).accounts,[]);
 await page.locator('#account-name').fill('虚构 USD 测试账户');await page.locator('#opening-cash').fill('1000');await page.locator('#account-form button').click();await message(page,'账户已建立');
 await saveTrade(page,'buy','10','10','2026-01-01T12:00');let a=(await ledger(page)).accounts[0];assert.equal(a.cash,'899');assert.equal(a.holdings[0].quantity,'10');
 await saveTrade(page,'sell','4','15','2026-01-02T12:00');a=(await ledger(page)).accounts[0];assert.equal(a.cash,'958');assert.equal(a.holdings[0].open_cost,'60.6');
 await page.locator('#trades tr').last().getByRole('button',{name:'更正'}).click();await page.locator('#quantity').fill('2');await page.locator('#save-trade').click();await page.waitForFunction(()=>document.querySelector('#trades tr:last-child td:nth-child(8)').textContent==='2');a=(await ledger(page)).accounts[0];assert.equal(a.cash,'928');assert.equal(a.holdings[0].realized_pnl,'8.8');
 await page.locator('#account-name').fill('<img src=x onerror=alert(1)> 虚构 CNY');await page.locator('#currency').selectOption('CNY');await page.locator('#opening-cash').fill('2000');await page.locator('#account-form button').click();await message(page,'账户已建立');assert.equal(await page.locator('#accounts img').count(),0);assert.equal((await ledger(page)).cross_currency_total,null);
 await page.locator('#backup').click();await message(page,'本地备份已完成');const backupName=fs.readdirSync(path.join(data,'backups'))[0];const expected=await ledger(page);
 await workspaceNav(page,'cockpit');await page.locator('#cockpit-panel').waitFor({state:'visible'});assert.match(await page.locator('#overview').textContent(),/资金账户2/);assert.match(await page.locator('#data-gaps').textContent(),/缺少行情/);assert.equal(await page.locator('#recent-trades tbody tr').count(),2);assert.equal(await page.title(),'Cockpit · 账本概览 · Awesome Stock');await page.screenshot({path:path.join(qa,'cockpit-desktop.png'),fullPage:true});
 await workspaceNav(page,'portfolio');await page.locator('#portfolio-panel').waitFor({state:'visible'});assert.match(await page.locator('#currency-balances').textContent(),/928/);assert.equal(await page.locator('#positions tbody tr').count(),1);const cny=(await ledger(page)).accounts.find(a=>a.currency==='CNY');await page.locator('#portfolio-account').selectOption(cny.id);assert.match(await page.locator('#positions').textContent(),/没有未平仓/);await page.locator('#portfolio-account').selectOption('');await page.screenshot({path:path.join(qa,'portfolio-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:path.join(qa,'portfolio-mobile.png'),fullPage:true});
 await stop();await start(data);await page.reload();await login(page);assert.deepEqual(await ledger(page),expected);await page.locator('#portfolio-panel').waitFor({state:'visible'});assert.equal(await page.locator('#positions tbody tr').count(),1);await workspaceNav(page,'ledger');await page.locator('#ledger-panel').waitFor({state:'visible'});
 await workspaceNav(page,'settings');await page.locator('#settings-panel').waitFor({state:'visible'});
 await page.locator('summary').filter({hasText:'修改本地口令'}).click();await page.locator('#old-password').fill(password);await page.locator('#new-password').fill(newPassword);await page.locator('#repeat-password').fill(newPassword);await page.locator('#password-form button').click();await message(page,'口令已修改');await login(page,newPassword);await workspaceNav(page,'ledger');await page.locator('#ledger-panel').waitFor({state:'visible'});
 page.once('dialog',d=>d.accept());await page.locator('#trades tr').last().getByRole('button',{name:'删除'}).click();await message(page,'交易已删除');assert.equal((await ledger(page)).accounts.find(a=>a.currency==='USD').cash,'899');
 await workspaceNav(page,'portfolio');await page.locator('#portfolio-panel').waitFor({state:'visible'});assert.match(await page.locator('#currency-balances').textContent(),/899/);assert.match(await page.locator('#positions').textContent(),/10/);
 await stop();const restored=path.join(temp,'restored');const run=spawnSync(python,['start_owner.py','--restore-from',path.join(data,'backups',backupName),'--data-dir',restored],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});assert.equal(run.status,0,run.stderr);
 await start(restored);await page.reload();await login(page,password);assert.deepEqual(await ledger(page),expected);
 await page.locator('#logout').click();await message(page,'已退出');await page.locator('#auth').waitFor({state:'visible'});
 assert.deepEqual(problems,[]);const summary={browser:'Chromium via Playwright',checks:['first-run owner setup','empty ledger','account creation','buy and sell recalculation','versioned correction','currency separation','safe text rendering','online backup','desktop and 390px mobile','process restart','same credential login','password change and relogin','trade delete','restore to new directory','backup-time credential and ledger restored','logout','Cockpit facts and gaps','Portfolio currency totals','account filter','direct route restart','delete reflected in views'],consoleErrors:problems.length,mobileOverflow:false,passed:true};fs.writeFileSync(path.join(qa,'views-browser-result.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
}finally{await browser?.close();await stop();fs.rmSync(temp,{recursive:true,force:true});}
