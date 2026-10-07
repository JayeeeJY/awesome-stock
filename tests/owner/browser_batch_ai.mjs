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
const failOnce=process.env.OWNER_BATCH_FAIL_ONCE==='1',resultPath=root+(failOnce?'/qa/batch-ai-retry-results.json':'/qa/batch-ai-results.json');
const server=spawn(process.env.OWNER_PYTHON || 'python3',['tests/owner/serve_ai_fixture.py',...(failOnce?['--fail-once-symbol','TWO']:[]),'--port',String(port),'--data-dir',path.join(dir,'data')],{cwd:root,stdio:['ignore','ignore','pipe'],env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
let browser,serverErrors='';server.stderr.on('data',d=>serverErrors+=d);
try {
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(serverErrors || 'server exited');try{if((await fetch(base+'/api/v1/owner/status')).ok)break}catch{}await delay(100)}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/422|503/.test(m.text()))errors.push(m.text())});
 await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill('portfolio-check');await page.getByLabel('口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByLabel('确认口令',{exact:true}).fill('Synthetic-Portfolio-2026');await page.getByRole('button',{name:'创建账号',exact:true}).click();await page.getByRole('heading',{name:'账户管理'}).waitFor();
 const api=async(path,method='GET',body)=>page.evaluate(async({path,method,body})=>{const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='));const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Requested-With':'awesome-owner'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(JSON.stringify(d));return d},{path,method,body});

 const callCount=()=>fs.existsSync(path.join(dir,'calls.json'))?JSON.parse(fs.readFileSync(path.join(dir,'calls.json'),'utf8')).length:0;
 await api('/api/v1/owner/connections','POST',{kind:'ai',provider:'ollama',model:'synthetic-only',key:'',enabled:true});
 await page.goto(base+'/research/batch');await page.getByLabel('批量研究标的',{exact:true}).fill('ONE TWO');const originalQuestion=await page.getByLabel('批量研究问题',{exact:true}).inputValue();await page.getByRole('button',{name:'准备逐标的材料',exact:true}).click();await page.locator('.batch-summary').waitFor();assert.equal(callCount(),0);
 await page.getByRole('button',{name:'预览整批发送内容',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.batch-detail .preview-panel').length===2);assert.equal(callCount(),0);
 await page.getByLabel('批量研究问题',{exact:true}).fill('Changed question');assert.equal(await page.getByRole('button',{name:'确认发送已预览项（2 次请求）',exact:true}).isEnabled(),false);assert.equal(await page.locator('.batch-detail:visible').getByRole('button',{name:'确认发送并生成草稿',exact:true}).isEnabled(),false);assert.equal(callCount(),0);
 await page.getByLabel('批量研究问题',{exact:true}).fill(originalQuestion);await page.getByRole('button',{name:'确认发送已预览项（2 次请求）',exact:true}).click();if(failOnce){await page.locator('.result-row.failed').waitFor();assert.equal(await page.locator('.draft-panel').count(),1);assert.equal(callCount(),2);await delay(1500);assert.equal(callCount(),2);await page.locator('.result-row').filter({hasText:'TWO'}).getByRole('button').click();const failedDetail=page.locator('.batch-detail:visible');await failedDetail.getByRole('button',{name:'预览发送内容',exact:true}).click();await failedDetail.getByRole('button',{name:'确认发送并生成草稿',exact:true}).waitFor();assert.equal(callCount(),2);await failedDetail.getByRole('button',{name:'确认发送并生成草稿',exact:true}).click();}await page.waitForFunction(()=>document.querySelectorAll('.batch-detail .draft-panel').length===2);assert.equal(callCount(),failOnce?3:2);assert.equal(await page.evaluate(()=>window.untrustedExecuted),undefined);
 for(const symbol of ['ONE','TWO']){await page.locator('.result-row').filter({hasText:symbol}).getByRole('button').click();const detail=page.locator('.batch-detail:visible');assert.match(await detail.locator('.draft-panel').innerText(),new RegExp('本次研究标的：'+symbol));const receipt=JSON.parse(await detail.locator('.draft-panel details pre').textContent());assert.equal(JSON.parse(receipt.context).symbol,symbol);const savingResponse=page.waitForResponse(r=>r.url().endsWith('/api/v1/owner/documents')&&r.request().method()==='POST');await detail.getByRole('button',{name:'保存为未核验研究笔记',exact:true}).click();assert.ok((await savingResponse).ok());}
 const notes=(await api('/api/v1/owner/documents')).documents;assert.deepEqual(notes.map(n=>n.symbol).sort(),['ONE','TWO']);assert.ok(notes.every(n=>n.content.includes('Synthetic daily summary')));assert.equal(callCount(),failOnce?3:2);assert.deepEqual(errors,[]);
 await page.getByRole('link',{name:'投资判断',exact:true}).click();await page.getByRole('button',{name:'继续',exact:true}).click();await page.waitForURL(base+'/decisions');await page.getByRole('heading',{name:'投资判断',exact:true}).waitFor();
 await page.goto(base+'/research/batch');await page.getByLabel('批量研究标的',{exact:true}).fill('ONE TWO');await page.getByRole('button',{name:'准备逐标的材料',exact:true}).click();await page.locator('.batch-summary').waitFor();
 await page.route(/\/assets\/Screening-[^/]+\.js$/,route=>route.abort());
 await page.getByRole('link',{name:'机会筛选',exact:true}).click();
 await page.getByRole('button',{name:'继续',exact:true}).click();
 await page.getByText('页面资源已经更新，当前标签需要刷新才能继续导航。刷新会丢弃未保存的输入。',{exact:true}).waitFor();
 assert.equal(new URL(page.url()).pathname,'/research/batch');assert.equal(await page.title(),'批量研究 · Awesome Stock');
 await page.getByRole('button',{name:'暂不刷新',exact:true}).click();
 fs.writeFileSync(resultPath,JSON.stringify({passed:true,transport:'isolated synthetic Ollama',preview_calls:0,generate_calls:failOnce?3:2,no_automatic_retry:failOnce,notes:2,input_change_blocks_send:true,script_text_not_executed:true}));console.log('Batch AI browser passed');
} catch(e) {fs.writeFileSync(resultPath,JSON.stringify({passed:false,error:String(e)}));const page=browser?.contexts()[0]?.pages()[0];if(page){await page.screenshot({path:root+'/qa/batch-ai-failure.png'});console.error(await page.locator('body').innerText())}throw e;
} finally {
 if(browser)await browser.close();
 if(server.exitCode===null){const stopped=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await stopped;}
 fs.rmSync(dir,{recursive:true,force:true});
}
