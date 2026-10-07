import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=fs.mkdtempSync(path.join(os.tmpdir(),'awesome-settings-appearance-'));console.log('Appearance evidence: '+output);
const {chromium}=createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE||path.join(root,'package.json'))('playwright');
const temp=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-appearance-data-')));fs.chmodSync(temp,0o700);
const port=await new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const p=socket.address().port;socket.close(()=>resolve(p))})});
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.OWNER_PYTHON||'python3',['tests/owner/serve_market_fixture.py','--port',String(port),'--data-dir',path.join(temp,'data')],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,stderr='';server.stderr.on('data',chunk=>stderr+=chunk);
try{
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(stderr||'server exited');try{if((await fetch(base+'/api/v1/owner/status')).ok)break}catch{}await delay(100)}
 browser=await chromium.launch();const context=await browser.newContext({viewport:{width:1440,height:960},colorScheme:'light'}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/422|503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('appearance-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Settings-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Settings-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();await page.goto(base+'/settings/account');await page.getByRole('heading',{name:'账户与数据管理'}).waitFor();
 await page.getByRole('button',{name:'外观',exact:true}).click();await page.getByRole('heading',{name:'外观设置'}).waitFor();assert.match(await page.title(),/外观设置/);
 const nav=page.getByRole('complementary',{name:'系统设置导航'});assert.equal(await nav.getByRole('button',{name:'外观'}).getAttribute('aria-current'),'page');
 await page.locator('.el-radio').filter({hasText:'深色'}).click();const width=page.locator('.settings-panel .el-slider [role="slider"]');await width.focus();await width.press('End');await page.getByRole('button',{name:'保存外观设置'}).click();await page.getByRole('status').getByText('外观设置已保存。').waitFor();
 assert.equal(await page.locator('html').evaluate(el=>el.classList.contains('dark')),true);await page.waitForFunction(()=>Math.round(document.querySelector('.sidebar').getBoundingClientRect().width)===280);assert.equal(await page.evaluate(()=>localStorage.getItem('awesome-owner-ui-theme-mode')),'dark');
 await page.reload();await page.getByRole('heading',{name:'外观设置'}).waitFor();assert.equal(await page.getByRole('radio',{name:'深色'}).isChecked(),true);await page.waitForFunction(()=>Math.round(document.querySelector('.sidebar').getBoundingClientRect().width)===280);
 await page.screenshot({path:path.join(output,'appearance-dark-1440.png'),animations:'disabled'});
 await page.locator('.el-radio').filter({hasText:'跟随系统'}).click();await page.getByRole('button',{name:'保存外观设置'}).click();assert.equal(await page.locator('html').evaluate(el=>el.classList.contains('dark')),false);
 await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.classList.contains('dark'));
 await page.emulateMedia({colorScheme:'light'});await page.waitForFunction(()=>!document.documentElement.classList.contains('dark'));
 await page.locator('.privacy-card .el-switch').click();await page.getByRole('button',{name:'保存外观设置'}).click();assert.equal(await page.evaluate(()=>localStorage.getItem('awesome-owner-ui-privacy-mode')),'true');
 await page.goto(base+'/cockpit');await page.getByRole('button',{name:'显示金额',exact:true}).waitFor();await page.reload();await page.getByRole('button',{name:'显示金额',exact:true}).waitFor();
 await page.getByRole('button',{name:'打开 Ask Awesome 助手',exact:true}).click();const ask=page.getByRole('dialog',{name:'Ask Awesome',exact:true});await openAskMaterials(ask);await ask.getByRole('button',{name:'载入当前页面材料',exact:true}).click();await ask.getByText('金额处于隐藏状态；如需载入驾驶舱材料，请先主动显示金额。',{exact:true}).waitFor();await ask.getByRole('button',{name:'关闭助手',exact:true}).click();
 await page.getByRole('button',{name:'显示金额',exact:true}).click();assert.equal(await page.evaluate(()=>localStorage.getItem('awesome-owner-ui-privacy-mode')),'false');await page.goto(base+'/settings/appearance');await page.getByRole('heading',{name:'外观设置'}).waitFor();
 await page.getByRole('button',{name:'数据与 AI 连接'}).click();await page.getByRole('heading',{name:'个人连接设置'}).waitFor();await page.getByRole('button',{name:'外观',exact:true}).last().click();await page.getByRole('heading',{name:'外观设置'}).waitFor();
 for(const width of [390,320]){await page.setViewportSize({width,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.screenshot({path:path.join(output,`appearance-${width}.png`),animations:'disabled',fullPage:true})}
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({passed:true,dark_saved:true,width_saved:280,auto_followed_system:true,privacy_saved:true,privacy_material_blocked:true,navigation:true,widths:[1440,390,320],errors,real_user_data:false}));console.log('Appearance browser passed');
}catch(e){fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}throw e}
finally{if(browser)await browser.close();if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped}fs.rmSync(temp,{recursive:true,force:true})}

async function openAskMaterials(panel){const options=panel.locator('.page-material-options');if(!await options.evaluate(e=>e.open))await options.locator(':scope > summary').click()}
