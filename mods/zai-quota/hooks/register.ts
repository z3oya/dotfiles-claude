import type { EngineInterface, Register } from 'claude-code'

import { decide, keyTagOf, validateCache, validateLease, type CacheEntry } from './cache'
import { fmtStatus, hostOf, parseQuota } from './quota'

const QUOTA_PATH = '/api/monitor/usage/quota/limit'
const INTERVAL_MS = 180_000
// The window is 3/4 of the tick period: fetchedAt lands mid-tick (jitter +
// fetch), so a window equal to the period still reads fresh on the next tick
// and a lone instance would idle to the tick after (~6 minutes, not 3).
const REFRESH_MS = 135_000
const FETCH_TIMEOUT_MS = 15_000
const JITTER_MS = 3_000
const LEASE_MS = 35_000

let lastGood: string | null = null
let inFlight = false
const me = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

async function resolveKey($: EngineInterface): Promise<string | null> {
  return (
    (await $.env.get('ANTHROPIC_AUTH_TOKEN')) ??
    (await $.env.get('ZAI_API_KEY')) ??
    (await $.env.get('BIGMODEL_API_KEY')) ??
    (await $.env.get('ZHIPU_API_KEY')) ??
    null
  )
}

// $.store can refuse (headless runs): degrade to per-instance behaviour.
async function readStore<T>(
  $: EngineInterface,
  key: string,
  validate: (raw: unknown) => T | null,
): Promise<T | null> {
  try {
    return validate(await $.store.get(key))
  } catch {
    return null
  }
}

async function writeStore($: EngineInterface, key: string, value: unknown): Promise<boolean> {
  try {
    await $.store.set(key, value)
    return true
  } catch {
    return false
  }
}

async function clearOwnLease($: EngineInterface): Promise<void> {
  const lease = await readStore($, 'lease', validateLease)
  if (lease?.owner === me) await $.store.delete('lease').catch(() => {})
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
  let claimed = false
  try {
    // A non-GLM relay means the key is not speaking to GLM: idle and clear.
    const host = hostOf(await $.env.get('ANTHROPIC_BASE_URL'))
    if (!host) {
      lastGood = null
      $.ui.status(undefined)
      return
    }
    const key = await resolveKey($)
    if (!key) {
      if (!lastGood) $.ui.status('zai-quota: no API key (ANTHROPIC_AUTH_TOKEN / ZAI_API_KEY)')
      return
    }
    const keyTag = keyTagOf(key)
    const show = (c: CacheEntry | null) =>
      c && c.host === host && c.keyTag === keyTag ? c.status : null

    let cache = await readStore($, 'quota', validateCache)
    let lease = await readStore($, 'lease', validateLease)
    const shown = show(cache)
    if (shown && shown !== lastGood) {
      lastGood = shown
      $.ui.status(shown)
    }

    // Peers waking on the same staleness moment: jitter, then re-read before
    // anyone fetches, so one of us mostly takes the window alone.
    const fresh = { me, host, keyTag, refreshMs: REFRESH_MS }
    if (decide({ ...fresh, cache, lease, now: await $.clock.now() }) === 'fetch') {
      await $.clock.sleep(Math.floor(Math.random() * JITTER_MS))
      cache = await readStore($, 'quota', validateCache)
      lease = await readStore($, 'lease', validateLease)
      const reShown = show(cache)
      if (reShown && reShown !== lastGood) {
        lastGood = reShown
        $.ui.status(reShown)
      }
    }

    const now = await $.clock.now()
    const verdict = decide({ ...fresh, cache, lease, now })
    if (verdict === 'standby' && lease) {
      // A peer holds the lease and its write lands within it: wait it out and
      // show what it wrote instead of idling blank to the next tick.
      const wait = Math.min(lease.until - now + 1_000, LEASE_MS)
      await $.clock.sleep(Math.max(wait, 0))
      const late = show(await readStore($, 'quota', validateCache))
      if (late && late !== lastGood) {
        lastGood = late
        $.ui.status(late)
      }
      return
    }
    if (verdict !== 'fetch') return

    claimed = await writeStore($, 'lease', { owner: me, until: now + LEASE_MS })

    let { code, text: body } = await fetchQuota($, host, key, false)
    if (code === 401) ({ code, text: body } = await fetchQuota($, host, key, true))
    if (code !== 200) {
      if (!lastGood) $.ui.status(`zai-quota: unreachable (HTTP ${code})`)
      return
    }
    const q = parseQuota(body)
    if (!q) {
      if (!lastGood) $.ui.status('zai-quota: empty data (personal key needed)')
      return
    }
    lastGood = fmtStatus(q)
    $.ui.status(lastGood)
    await writeStore($, 'quota', { status: lastGood, fetchedAt: await $.clock.now(), host, keyTag })
  } catch {
    if (!lastGood) $.ui.status('zai-quota: unreachable (network error)')
  } finally {
    inFlight = false
    if (claimed) await clearOwnLease($)
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
    // Not awaited: a network wait must not hold the hook's budget.
    void tick($)
    return next(e)
  }).catch(($, e, next) => next(e))
}
