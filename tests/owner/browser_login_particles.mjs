// Login visuals and original Owner authentication exercised against an isolated shipped build.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import net from 'node:net';
import assert from 'node:assert/strict'; import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=process.env.OWNER_LOGIN_EVIDENCE || fs.mkdtempSync(path.join(os.tmpdir(),'awesome-login-particles-'));
fs.mkdirSync(output,{recursive:true});
const {chromium}=createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE || path.join(root,'package.json'))('playwright');
const data=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'awesome-login-data-')));
const port=await new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.OWNER_PYTHON || 'python3',['start_owner.py','--port',String(port),'--data-dir',data],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,stderr='';server.stderr.on('data',d=>stderr+=d);
const errors=[],external=[],captures=[];
function watch(page){page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());});}
async function fingerprint(page){return page.locator('.particle-bg canvas').evaluate(c=>{const pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let nonzero=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i])nonzero++;let hash=2166136261;for(const value of pixels)hash=Math.imul(hash^value,16777619);return {nonzero,image:hash};});}
async function shot(page,name){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(await page.locator('vite-error-overlay').count(),0);await page.screenshot({path:path.join(output,name+'.png'),animations:'disabled'});captures.push(name);}
try {
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(stderr);try{if((await fetch(base+'/api/v1/owner/status')).ok)break;}catch{}await delay(100);}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}});watch(page);
 await page.goto(base+'/login');await page.locator('.particle-bg canvas').waitFor();await delay(1600);
 const first=await fingerprint(page);assert.ok(first.nonzero>100,'stars and links actually render');await delay(300);assert.notEqual((await fingerprint(page)).image,first.image,'particles animate');
 await shot(page,'create-desktop');let setupRequests=0;page.on('request',r=>{if(r.url().endsWith('/api/v1/owner/setup'))setupRequests++;});
 await page.getByLabel('用户名',{exact:true}).fill('star-review');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Login-Only-2026');await page.getByLabel('确认口令',{exact:true}).fill('mismatch');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByText('两次口令不一致。',{exact:true}).waitFor();assert.equal(setupRequests,0);
 await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Login-Only-2026');await page.getByLabel('确认口令',{exact:true}).press('Enter');await page.getByRole('heading',{name:'账户管理',exact:true}).waitFor();assert.equal(setupRequests,1);assert.equal(await page.locator('.particle-bg,canvas').count(),0,'canvas removed on login route exit');
 // New browser context has no login cookie; it sees existing-account authentication.
 const context=await browser.newContext({viewport:{width:1440,height:1000}});const login=await context.newPage();watch(login);await login.goto(base+'/login');await login.getByRole('heading',{name:'登录本地账号',exact:true}).waitFor();await login.locator('.particle-bg canvas').waitFor();await delay(1600);assert.equal(await login.getByLabel('确认口令',{exact:true}).count(),0);
 await login.getByLabel('用户名',{exact:true}).fill('star-review');await login.getByLabel('口令',{exact:true}).fill('Synthetic-wrong-only');await login.getByRole('button',{name:'登录',exact:true}).click();await login.locator('.el-alert--error').waitFor();assert.equal(new URL(login.url()).pathname,'/login');await login.getByLabel('口令',{exact:true}).fill('');
 for(const width of [1440,390,320]){await login.setViewportSize({width,height:1000});await delay(700);const b=await login.getByRole('button',{name:'登录',exact:true}).boundingBox();assert.ok(b&&b.x>=0&&b.x+b.width<=width,'login stays reachable');await shot(login,'login-'+width);}
 await login.emulateMedia({reducedMotion:'reduce'});await delay(100);const frozen=await fingerprint(login);assert.ok(frozen.nonzero>100);await delay(300);assert.equal((await fingerprint(login)).image,frozen.image,'runtime reduced-motion preference pauses canvas');
 await login.emulateMedia({reducedMotion:'no-preference'});await delay(300);assert.notEqual((await fingerprint(login)).image,frozen.image,'normal motion resumes');
 await login.getByLabel('口令',{exact:true}).fill('Synthetic-Login-Only-2026');await login.getByLabel('口令',{exact:true}).press('Enter');await login.getByRole('heading',{name:'账户管理',exact:true}).waitFor();assert.equal(await login.locator('.particle-bg').count(),0);
 const reduced=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});const staticPage=await reduced.newPage();watch(staticPage);await staticPage.goto(base+'/login');await staticPage.locator('.particle-bg canvas').waitFor();await delay(300);const staticFrame=await fingerprint(staticPage);assert.ok(staticFrame.nonzero>100,'reduced-motion first load retains visible stars');await delay(300);assert.equal((await fingerprint(staticPage)).image,staticFrame.image);await shot(staticPage,'reduced-motion');
 await staticPage.getByLabel('用户名',{exact:true}).focus();await staticPage.keyboard.press('Tab');assert.equal(await staticPage.getByLabel('口令',{exact:true}).evaluate(e=>e===document.activeElement),true,'keyboard reaches password');
 // Lazy initialization must not leave a canvas on authenticated routes.
 await page.goto(base+'/login');await page.locator('.particle-bg canvas').waitFor();await page.goto(base+'/portfolio/accounts');await page.getByRole('heading',{name:'账户管理',exact:true}).waitFor();await delay(300);assert.equal(await page.locator('.particle-bg').count(),0);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({passed:true,synthetic_data_only:true,provider_calls:0,external_requests:external,errors,captures,checks:['animated visible stars','create mismatch no request','create via Enter','incorrect login','existing login via Enter','route cleanup','1440/390/320','live motion preference','reduced-motion initial static stars','keyboard']},null,2)+'\n');console.log('LOGIN PARTICLES PASS',output);
}finally{if(browser)await browser.close();server.kill('SIGTERM');}
