import {createRequire} from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import net from 'node:net'
import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {setTimeout as delay} from 'node:timers/promises'
import {fileURLToPath} from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const {chromium} = createRequire(root + '/package.json')('playwright')
const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'as-ask-persist-')))
const dataDir = path.join(dir, 'data')
const port = await new Promise(resolve => {
  const socket = net.createServer()
  socket.listen(0, '127.0.0.1', () => {
    const chosen = socket.address().port
    socket.close(() => resolve(chosen))
  })
})
const base = `http://127.0.0.1:${port}`
const password = 'Synthetic-Ask-Persist-2026'
const secret = 'sk-browser-ask-secret-not-real'
const questions = ['第一问：市盈率有什么局限', '第二问：请只根据上一答继续', '第三问：重启前的追问', '另一段对话：只讨论复利']

function start() {
  const child = spawn('python3', ['tests/owner/serve_ai_fixture.py', '--port', String(port), '--data-dir', dataDir], {cwd: root, stdio: ['ignore', 'ignore', 'pipe']})
  let stderr = ''
  child.stderr.on('data', chunk => { stderr += chunk })
  child.stderrText = () => stderr
  return child
}
async function ready(child) {
  for (let i = 0; i < 100; i++) {
    if (child.exitCode !== null) throw Error(child.stderrText())
    try { if ((await fetch(base + '/api/v1/owner/status')).ok) return } catch {}
    await delay(100)
  }
  throw Error('server did not start: ' + child.stderrText())
}
async function stop(child) {
  if (child.exitCode !== null) return
  const exited = new Promise(resolve => child.once('exit', resolve))
  child.kill()
  await exited
}
function turn(ask, question) {
  return ask.getByLabel('Ask Awesome 对话记录', {exact: true}).getByText(question, {exact: true})
}
async function send(ask, page, question) {
  // generate() allows one AI call per second and answers 503 try_later inside that window.
  // Space the test; do not change that product limit.
  await delay(1100)
  const input = ask.getByLabel('给 Ask Awesome 的消息', {exact: true})
  await input.fill(question)
  await ask.getByRole('button', {name: '发送', exact: true}).click()
  const confirmation = page.getByRole('dialog', {name: '确认发送对话', exact: true})
  await confirmation.waitFor()
  await confirmation.getByRole('button', {name: '确认发送', exact: true}).click()
  await confirmation.waitFor({state: 'hidden'})
  await ask.locator('.chat-answer p').filter({hasText: 'Synthetic answer: ' + question}).waitFor()
}
function previewContext(previews) {
  const last = previews.at(-1)
  assert.ok(last, 'missing preview')
  return last.context ? JSON.parse(last.context) : {conversation: [], material: last.context}
}

let server = start()
let browser
try {
  await ready(server)
  browser = await chromium.launch()
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}})
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error' && !/503/.test(message.text())) errors.push(message.text()) })
  const previews = []
  page.on('request', request => { if (request.url().endsWith('/api/v1/owner/ai-preview')) previews.push(request.postDataJSON()) })
  await page.goto(base + '/login')
  await page.getByLabel('用户名', {exact: true}).fill('ask-persist')
  await page.getByLabel('口令', {exact: true}).fill(password)
  await page.getByLabel('确认口令', {exact: true}).fill(password)
  await page.getByRole('button', {name: '创建账号', exact: true}).click()
  await page.getByRole('heading', {name: '账户管理'}).waitFor()
  await page.goto(base + '/settings/connections')
  await page.getByRole('button', {name: 'deepseek-flash', exact: true}).click()
  await page.getByLabel('你自己的模型服务 API Key', {exact: true}).fill(secret)
  await page.getByRole('button', {name: '保存模型连接', exact: true}).click()
  await page.getByText('连接配置已保存。Key 输入框已清空，下一步点击下方「测试连接」。', {exact: true}).waitFor()
  await page.getByRole('button', {name: '打开 Ask Awesome 助手', exact: true}).click()
  const ask = page.getByRole('dialog', {name: 'Ask Awesome', exact: true})
  await send(ask, page, questions[0])
  await send(ask, page, questions[1])
  const followup = previewContext(previews)
  assert.equal(followup.conversation.length, 1)
  assert.equal(followup.conversation[0].question, questions[0])
  assert.match(followup.conversation[0].answer, /Synthetic answer/)
  assert.equal(followup.material, '')
  await page.reload()
  await page.getByRole('button', {name: '打开 Ask Awesome 助手', exact: true}).click()
  await turn(ask, questions[0]).waitFor()
  await turn(ask, questions[1]).waitFor()
  await send(ask, page, questions[2])
  const restoredFollowup = previewContext(previews)
  assert.deepEqual(restoredFollowup.conversation.map(turn => turn.question), questions.slice(0, 2))
  await ask.getByRole('button', {name: '新对话', exact: true}).click()
  await page.getByRole('dialog', {name: '新对话', exact: true}).getByRole('button', {name: '开始新对话', exact: true}).click()
  await ask.getByRole('heading', {name: '想讨论什么？', exact: true}).waitFor()
  await send(ask, page, questions[3])
  assert.equal(previews.at(-1).context, '')
  await stop(server)
  server = start()
  await ready(server)
  await page.goto(base + '/login')
  await page.getByRole('heading', {name: '登录本地账号'}).waitFor()
  await page.getByLabel('用户名', {exact: true}).fill('ask-persist')
  await page.getByLabel('口令', {exact: true}).fill(password)
  await page.getByRole('button', {name: '登录', exact: true}).click()
  await page.getByRole('heading', {name: '账户管理'}).waitFor()
  await page.getByRole('button', {name: '打开 Ask Awesome 助手', exact: true}).click()
  await turn(ask, questions[3]).waitFor()
  await ask.getByLabel('恢复已保存的对话', {exact: true}).selectOption({label: questions[0]})
  await turn(ask, questions[0]).waitFor()
  await turn(ask, questions[1]).waitFor()
  await turn(ask, questions[2]).waitFor()
  assert.equal(await turn(ask, questions[3]).count(), 0)
  const database = fs.readFileSync(path.join(dataDir, 'owner.sqlite3'))
  const stored = database.toString('utf8')
  assert.equal(fs.realpathSync(path.join(dataDir, 'owner.sqlite3')), path.join(dataDir, 'owner.sqlite3'))
  for (const question of questions) assert.ok(stored.includes(question), question)
  assert.equal(stored.includes(secret), false)
  assert.equal(stored.includes('ZXQHOLD'), false)
  assert.deepEqual(errors, [])
  console.log('Ask persistence browser check passed')
} finally {
  if (browser) await browser.close()
  await stop(server)
  fs.rmSync(dir, {recursive: true, force: true})
}
