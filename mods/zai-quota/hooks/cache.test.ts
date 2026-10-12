import { expect, test } from 'claude-code/testing'

import { decide, keyTagOf, validateCache, validateLease, type CacheEntry } from './cache'

const GOOD: CacheEntry = {
  status: 'GLM Pro | 5h 1%',
  fetchedAt: 10_000,
  host: 'https://api.z.ai',
  keyTag: 'abc',
}

const BASE = {
  now: 180_000,
  me: 'a',
  host: 'https://api.z.ai',
  keyTag: 'abc',
  refreshMs: 180_000,
}

test('fresh cache for this account skips the fetch', () => {
  expect(decide({ ...BASE, cache: GOOD, lease: null })).toBe('skip')
})

test('stale cache asks for a fetch', () => {
  expect(decide({ ...BASE, cache: { ...GOOD, fetchedAt: -1 }, lease: null })).toBe('fetch')
})

test('a window exactly as old as refreshMs is stale', () => {
  expect(decide({ ...BASE, cache: { ...GOOD, fetchedAt: 0 }, lease: null })).toBe('fetch')
})

test('a fresh cache from another host or account is not used', () => {
  const foreign = { ...GOOD, fetchedAt: BASE.now, keyTag: 'zzz' }
  expect(decide({ ...BASE, cache: foreign, lease: null })).toBe('fetch')
  const otherHost = { ...GOOD, fetchedAt: BASE.now, host: 'https://open.bigmodel.cn' }
  expect(decide({ ...BASE, cache: otherHost, lease: null })).toBe('fetch')
})

test('a lease held by a peer puts us on standby', () => {
  const stale = { ...GOOD, fetchedAt: -1 }
  expect(decide({ ...BASE, cache: stale, lease: { owner: 'b', until: BASE.now + 1 } })).toBe('standby')
})

test('an expired or own lease leaves the fetch to us', () => {
  const stale = { ...GOOD, fetchedAt: -1 }
  expect(decide({ ...BASE, cache: stale, lease: { owner: 'b', until: BASE.now } })).toBe('fetch')
  expect(decide({ ...BASE, cache: stale, lease: { owner: 'a', until: BASE.now + 1 } })).toBe('fetch')
})

test('validateCache accepts a well-formed entry and rejects the rest', () => {
  const ok = { status: 's', fetchedAt: 1, host: 'h', keyTag: 'k' }
  expect(validateCache(ok)).toBe(ok)
  expect(validateCache(null)).toBe(null)
  expect(validateCache('x')).toBe(null)
  expect(validateCache({ status: '', fetchedAt: 1, host: 'h', keyTag: 'k' })).toBe(null)
  expect(validateCache({ status: 's', fetchedAt: NaN, host: 'h', keyTag: 'k' })).toBe(null)
  expect(validateCache({ status: 's', fetchedAt: 1, host: '', keyTag: 'k' })).toBe(null)
  expect(validateCache({ status: 's', fetchedAt: 1, host: 'h', keyTag: '' })).toBe(null)
})

test('validateLease accepts a well-formed lease and rejects the rest', () => {
  const ok = { owner: 'a', until: 5 }
  expect(validateLease(ok)).toBe(ok)
  expect(validateLease(undefined)).toBe(null)
  expect(validateLease({ owner: '', until: 1 })).toBe(null)
  expect(validateLease({ owner: 'a', until: Infinity })).toBe(null)
})

test('keyTag is stable and input-sensitive', () => {
  expect(keyTagOf('sk-abc')).toBe(keyTagOf('sk-abc'))
  expect(keyTagOf('sk-abc')).not.toBe(keyTagOf('sk-abd'))
})
