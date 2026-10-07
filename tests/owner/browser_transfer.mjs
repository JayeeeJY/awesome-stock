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
 await page.goto(base+'/ledger');await page.locator('#auth').waitFor({state:'visible'});await page.locator('#username').fill('synthetic-owner');await page.locator('#password').fill(password);await page.locator('#confirm-password').fill(password);await page.locator('#auth-submit').click();await message(page,'已登录本地账本');
 await page.locator('#account-name').fill('虚构导入测试账户');await page.locator('#opening-cash').fill('1000');await page.locator('#account-form button').click();await message(page,'账户已建立');
 const header='record_id,symbol,side,quantity,price,fee,executed_at\n',buy='fill-1,TEST,buy,10,10,1,2026-01-01T00:00:00Z\n',sell='fill-2,TEST,sell,4,15,1,2026-01-02T00:00:00Z\n';
 const templatePromise=page.waitForEvent('download');await page.locator('#csv-template').click();const template=await templatePromise;assert.equal(fs.readFileSync(await template.path(),'utf8'),header);
 async function upload(csv){await page.locator('#csv-file').setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await page.locator('#csv-preview').click();await message(page,'预览完成');await page.waitForFunction(()=>document.getElementById('csv-result').textContent.length>0&&!document.getElementById('csv-preview').disabled);}
 const initial=await ledger(page);await upload(header+buy+'broken,row\n');assert.match(await page.locator('#csv-result').textContent(),/无效/);assert.equal(await page.locator('#csv-confirm').isVisible(),false);assert.deepEqual(await ledger(page),initial);
 await upload(header+buy+sell);assert.match(await page.locator('#csv-result').textContent(),/1000 → 958/);assert.match(await page.locator('#csv-result').textContent(),/60.6/);assert.deepEqual(await ledger(page),initial);assert.equal(await page.title(),'本地账本 · Awesome Stock');
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(qa,'transfer-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:path.join(qa,'transfer-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:960});
 await page.locator('#csv-confirm').click();await message(page,'已导入 2 笔');const expected=await ledger(page);assert.equal(expected.accounts[0].cash,'958');assert.equal(expected.accounts[0].trades.length,2);
 await upload(header+buy+sell);assert.match(await page.locator('#csv-result').textContent(),/重复跳过 2 笔/);assert.equal(await page.locator('#csv-confirm').isVisible(),false);assert.deepEqual(await ledger(page),expected);
 await upload(header+buy.replace(',10,10,',',11,10,'));assert.match(await page.locator('#csv-result').textContent(),/冲突/);assert.equal(await page.locator('#csv-confirm').isVisible(),false);
 await workspaceNav(page,'settings');await page.locator('#settings-panel').waitFor({state:'visible'});const downloadPromise=page.waitForEvent('download');await page.locator('#settings-tab-data').click();await page.locator('#business-export').click();const download=await downloadPromise;const out=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(out.format,'awesome-stock-owner-business');assert.deepEqual(out.accounts,expected.accounts);assert.equal(out.restores_account,false);assert.equal(Object.hasOwn(out,'credential'),false);assert.equal(Object.hasOwn(out,'username'),false);assert.match(await page.locator('#business-export-result').textContent(),/发起下载/);
 await stop();await start(data);await page.reload();await login(page);assert.deepEqual(await ledger(page),expected);await workspaceNav(page,'ledger');await page.locator('#ledger-panel').waitFor({state:'visible'});await upload(header+buy+sell);assert.match(await page.locator('#csv-result').textContent(),/重复跳过 2 笔/);
 await page.locator('#logout').click();await message(page,'已退出');assert.equal(await page.locator('#csv-result').textContent(),'');assert.equal(await page.locator('#csv-file').inputValue(),'');
 assert.deepEqual(problems,[]);const summary={passed:true,consoleErrors:0,mobileOverflow:false,viewports:['1440x960','390x844'],checks:['template download','invalid row blocks batch','preview leaves ledger unchanged','before/after cash and cost','confirm imports two rows','repeat CSV skips two rows','changed same identifier blocks','JSON download parsed and reconciled','restart retains import and deduplication','logout clears local preview/file']};fs.writeFileSync(path.join(qa,'transfer-browser-result.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
}finally{await browser?.close();await stop();fs.rmSync(temp,{recursive:true,force:true});}
