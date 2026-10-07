// Synthetic, delayed BYOK transport: pause must not send the next billable request.
import { createRequire } from 'node:module'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const { chromium } = createRequire(process.env.OWNER_PLAYWRIGHT_PACKAGE || path.join(root, 'package.json'))('playwright')
const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'awesome-batch-p191-')))
fs.chmodSync(dir, 0o700)
const port = await new Promise(resolve => { const socket = net.createServer(); socket.listen(0, '127.0.0.1', () => { const value = socket.address().port; socket.close(() => resolve(value)) }) })
const base = `http://127.0.0.1:${port}`
const server = spawn(process.env.OWNER_PYTHON || 'python3', ['tests/owner/serve_ai_fixture.py', '--port', String(port), '--data-dir', path.join(dir, 'data'), '--delay-seconds', '0.8', '--draft-chars', '7000'], { cwd: root, stdio: ['ignore', 'ignore', 'pipe'], env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } })
let browser, serverErrors = ''
server.stderr.on('data', chunk => { serverErrors += chunk })
const calls = () => fs.existsSync(path.join(dir, 'calls.json')) ? JSON.parse(fs.readFileSync(path.join(dir, 'calls.json'), 'utf8')).length : 0
const evidence = { synthetic: true, beforePreview: null, afterPreview: null, afterPause: null, afterResume: null, longDraftChars: null, phoneOverflow: null, errors: [] }

try {
  for (let i = 0; i < 100; i++) {
    if (server.exitCode !== null) throw Error(serverErrors || 'fixture exited')
    try { if ((await fetch(`${base}/api/v1/owner/status`)).ok) break } catch {}
    await delay(100)
  }
  browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 390, height: 900 } })
  page.on('pageerror', error => evidence.errors.push(error.message))
  await page.route('**/*', async route => {
    if (new URL(route.request().url()).origin === base) await route.continue()
    else await route.abort()
  })
  await page.goto(`${base}/login`)
  await page.getByLabel('用户名', { exact: true }).fill('batch-p191')
  await page.getByLabel('口令', { exact: true }).fill('Synthetic-Batch-2026')
  await page.getByLabel('确认口令', { exact: true }).fill('Synthetic-Batch-2026')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  await page.getByRole('heading', { name: '账户管理' }).waitFor()
  const configure = await page.evaluate(async () => {
    const csrf = decodeURIComponent(document.cookie.split('; ').find(part => part.startsWith('__Host-awesome_owner_csrf=')).split('=').slice(1).join('='))
    const response = await fetch('/api/v1/owner/connections', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'X-Requested-With': 'awesome-owner' }, body: JSON.stringify({ kind: 'ai', provider: 'ollama', model: 'synthetic-only', key: '', enabled: true }) })
    return response.status
  })
  assert.equal(configure, 200)
  await page.goto(`${base}/research/batch`)
  await page.getByLabel('批量研究标的', { exact: true }).fill('ONE TWO THREE')
  await page.getByRole('button', { name: '准备逐标的材料', exact: true }).click()
  await page.locator('.batch-summary').waitFor()
  evidence.beforePreview = calls()
  assert.equal(evidence.beforePreview, 0)
  await page.getByRole('button', { name: '预览整批发送内容', exact: true }).click()
  await page.waitForFunction(() => document.querySelectorAll('.batch-detail .preview-panel').length === 3)
  evidence.afterPreview = calls()
  assert.equal(evidence.afterPreview, 0)
  await page.getByRole('button', { name: '确认发送已预览项（3 次请求）', exact: true }).click()
  for (let i = 0; i < 100 && calls() !== 1; i++) await delay(20)
  assert.equal(calls(), 1)
  await page.getByRole('button', { name: '暂停后续请求', exact: true }).click()
  await page.waitForFunction(() => document.querySelectorAll('.batch-detail .draft-panel').length === 1)
  await page.getByRole('button', { name: '确认发送已预览项（2 次请求）', exact: true }).waitFor({ state: 'visible' })
  await delay(1400)
  evidence.afterPause = calls()
  assert.equal(evidence.afterPause, 1)
  const first = page.locator('.batch-detail').filter({ has: page.locator('.draft-panel') }).first()
  const draft = await first.locator('.draft-panel pre').last().textContent()
  evidence.longDraftChars = draft.length
  assert.ok(draft.length >= 7000)
  evidence.phoneOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)
  assert.equal(evidence.phoneOverflow, false)
  assert.equal(await page.evaluate(() => window.untrustedExecuted), undefined)
  await page.getByRole('button', { name: '确认发送已预览项（2 次请求）', exact: true }).click()
  await page.waitForFunction(() => document.querySelectorAll('.batch-detail .draft-panel').length === 3)
  evidence.afterResume = calls()
  assert.equal(evidence.afterResume, 3)
  assert.deepEqual(evidence.errors, [])
  fs.mkdirSync(path.join(root, 'qa/p191-batch-pause-long'), { recursive: true })
  fs.writeFileSync(path.join(root, 'qa/p191-batch-pause-long/result.json'), JSON.stringify(evidence, null, 2))
  console.log('Batch pause, resume and 7000-character mobile draft passed')
} finally {
  if (browser) await browser.close()
  if (server.exitCode === null) { const stopped = new Promise(resolve => server.once('exit', resolve)); server.kill('SIGTERM'); await stopped }
  fs.rmSync(dir, { recursive: true, force: true })
}
