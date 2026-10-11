import type { EngineInterface, Register } from 'claude-code'

import { fmtStatus, parseQuota } from './quota'

const DEFAULT_HOST = 'https://open.bigmodel.cn'
const QUOTA_PATH = '/api/monitor/usage/quota/limit'
const INTERVAL_MS = 180_000
const FETCH_TIMEOUT_MS = 15_000

let lastGood: string | null = null
let inFlight = false

async function resolveHost($: EngineInterface): Promise<string> {
  const base = await $.env.get('ANTHROPIC_BASE_URL')
  return base && base.includes('z.ai') ? 'https://api.z.ai' : DEFAULT_HOST
}

async function resolveKey($: EngineInterface): Promise<string | null> {
  return (
    (await $.env.get('ANTHROPIC_AUTH_TOKEN')) ??
    (await $.env.get('ZAI_API_KEY')) ??
    (await $.env.get('BIGMODEL_API_KEY')) ??
    (await $.env.get('ZHIPU_API_KEY')) ??
    null
  )
}

// HttpInit has no timeout; the no-op catches keep the losing racer's rejection handled.
async function fetchQuota($: EngineInterface, host: string, key: string, bearer: boolean) {
  const timeout = $.clock.sleep(FETCH_TIMEOUT_MS).then(() => {
    throw new Error(`quota fetch timed out after ${FETCH_TIMEOUT_MS}ms`)
  })
  const res = $.http.fetch(host + QUOTA_PATH, {
    headers: { Authorization: bearer ? `Bearer ${key}` : key, Accept: 'application/json' },
  })
  timeout.catch(() => {})
  res.catch(() => {})
  const done = await Promise.race([res, timeout])
  return { code: done.status, text: done.text }
}

async function tick($: EngineInterface): Promise<void> {
  if (inFlight) return
  inFlight = true
  try {
    const key = await resolveKey($)
    if (!key) {
      if (!lastGood) $.ui.status('zai-quota: no API key (ANTHROPIC_AUTH_TOKEN / ZAI_API_KEY)')
      return
    }
    const host = await resolveHost($)
    let { code, text } = await fetchQuota($, host, key, false)
    if (code === 401) ({ code, text } = await fetchQuota($, host, key, true))
    if (code !== 200) {
      if (!lastGood) $.ui.status(`zai-quota: unreachable (HTTP ${code})`)
      return
    }
    const q = parseQuota(text)
    if (!q) {
      if (!lastGood) $.ui.status('zai-quota: empty data (personal key needed)')
      return
    }
    lastGood = fmtStatus(q)
    $.ui.status(lastGood)
  } catch {
    if (!lastGood) $.ui.status('zai-quota: unreachable (network error)')
  } finally {
    inFlight = false
  }
}

export const register: Register = on => {
  let armed = false

  // session.start fires per fresh load; the flag keeps one timer per environment.
  on('session.start', async ($, e, next) => {
    if (!armed) {
      armed = true
      $.clock.every(INTERVAL_MS, () => void tick($))
    }
    await tick($)
    return next(e)
  }).catch(($, e, next) => next(e))
}
