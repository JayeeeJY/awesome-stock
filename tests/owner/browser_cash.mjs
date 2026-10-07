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
 await start(data);browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:960}});const problems=[];let expectedFailure=false,expectedRejections=0;
 page.on('pageerror',e=>problems.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type())){if(expectedFailure&&m.text().includes('422'))expectedRejections++;else problems.push(m.text());}});
 await page.goto(base+'/ledger');await page.locator('#auth').waitFor({state:'visible'});await page.locator('#username').fill('synthetic-owner');await page.locator('#password').fill(password);await page.locator('#confirm-password').fill(password);await page.locator('#auth-submit').click();await message(page,'已登录本地账本');
 await page.locator('#account-name').fill('虚构资金账户');await page.locator('#opening-cash').fill('0');await page.locator('#account-form button').click();await message(page,'账户已建立');
 await workspaceNav(page,'cash');await page.locator('#cash-panel').waitFor({state:'visible'});assert.equal(await page.title(),'Portfolio · 入金与出金 · Awesome Stock');
 await page.locator('#cash-amount').fill('1000');await page.locator('#cash-when').fill('2026-01-01T12:00');await page.locator('#cash-note').fill('虚构入金 <img src=x onerror=alert(1)>');await page.locator('#save-cash').click();await message(page,'资金流水已保存');assert.equal((await ledger(page)).accounts[0].cash,'1000');assert.equal(await page.locator('#cash-list img').count(),0);
 await workspaceNav(page,'ledger');await page.locator('#ledger-panel').waitFor({state:'visible'});await saveTrade(page,'buy','10','10','2026-01-02T12:00');const holding=(await ledger(page)).accounts[0].holdings;
 await workspaceNav(page,'cash');await page.locator('#cash-panel').waitFor({state:'visible'});await page.locator('#cash-direction').selectOption('withdrawal');await page.locator('#cash-amount').fill('100');await page.locator('#cash-when').fill('2026-01-03T12:00');await page.locator('#save-cash').click();await message(page,'资金流水已保存');await page.waitForFunction(()=>document.querySelectorAll('#cash-list tbody tr').length===2);assert.equal((await ledger(page)).accounts[0].cash,'799');
 await page.locator('#cash-list tbody tr').last().getByRole('button',{name:'更正'}).click();assert.equal(await page.locator('#cash-account').isDisabled(),true);await page.locator('#cash-amount').fill('150');await page.locator('#save-cash').click();await page.waitForFunction(()=>document.querySelector('#cash-list tbody tr:last-child td:nth-child(6)').textContent.startsWith('2 /'));assert.equal((await ledger(page)).accounts[0].cash,'749');assert.deepEqual((await ledger(page)).accounts[0].holdings,holding);
 await page.locator('#cash-list tbody tr').first().getByRole('button',{name:'更正'}).click();await page.locator('#cash-amount').fill('50');expectedFailure=true;await page.locator('#save-cash').click();await message(page,'现金不足');await page.waitForFunction(()=>!document.getElementById('save-cash').disabled);expectedFailure=false;assert.equal(await page.locator('#cash-amount').inputValue(),'50');assert.equal((await ledger(page)).accounts[0].cash,'749');
 page.once('dialog',d=>d.accept());await page.locator('#new-cash').click();
 await page.locator('#cash-panel summary').click();assert.match(await page.locator('#cash-history').textContent(),/v2/);assert.equal(await page.locator('#cash-history img').count(),0);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(qa,'cash-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:path.join(qa,'cash-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:960});
 const expected=await ledger(page);await page.locator('#backup').click();await message(page,'本地备份已完成');const backupName=fs.readdirSync(path.join(data,'backups'))[0];
 await workspaceNav(page,'settings');await page.locator('#settings-panel').waitFor({state:'visible'});const downloaded=page.waitForEvent('download');await page.locator('#settings-tab-data').click();await page.locator('#business-export').click();const dl=await downloaded;const out=JSON.parse(fs.readFileSync(await dl.path(),'utf8'));assert.equal(out.format_version,2);assert.equal(out.cash_flow_versions.length,3);assert.deepEqual(out.accounts,expected.accounts);
 await workspaceNav(page,'portfolio');await page.locator('#portfolio-panel').waitFor({state:'visible'});assert.match(await page.locator('#currency-balances').textContent(),/749/);
 await stop();await start(data);await page.goto(base+'/cash');await login(page);await page.locator('#cash-panel').waitFor({state:'visible'});assert.deepEqual(await ledger(page),expected);
 page.once('dialog',d=>d.accept());await page.locator('#cash-list tbody tr').last().getByRole('button',{name:'删除'}).click();await message(page,'资金流水已删除');assert.equal((await ledger(page)).accounts[0].cash,'899');assert.match(await page.locator('#cash-history').textContent(),/已删除/);
 await stop();const restored=path.join(temp,'restored');const run=spawnSync(python,['start_owner.py','--restore-from',path.join(data,'backups',backupName),'--data-dir',restored],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});assert.equal(run.status,0,run.stderr);await start(restored);await page.reload();await login(page);await page.locator('#cash-panel').waitFor({state:'visible'});assert.deepEqual(await ledger(page),expected);
 await page.locator('#logout').click();await message(page,'已退出');assert.equal(await page.locator('#cash-list').textContent(),'');assert.equal(await page.locator('#cash-history').textContent(),'');
 assert.deepEqual(problems,[]);const summary={passed:true,unexpectedConsoleErrors:0,expectedValidationRejections:expectedRejections,mobileOverflow:false,viewports:['1440x960','390x844'],checks:['zero opening account funded by deposit','buy consumes funded cash','withdrawal and versioned edit','cash flow does not change holdings or profit','historical invalid edit rejected and input retained','safe notes and history','JSON v2 download and reconcile','Portfolio updated cash','direct cash route after restart','withdrawal delete recomputes balance','restore previous cash history','logout clears private cash data']};fs.writeFileSync(path.join(qa,'cash-browser-result.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
}finally{await browser?.close();await stop();fs.rmSync(temp,{recursive:true,force:true});}
