import { expect, test } from 'claude-code/testing'

import { fmtStatus, parseQuota } from './quota'

// Windows out of order on the wire: earliest reset is the 5h window.
const SAMPLE = JSON.stringify({
  data: {
    planName: 'GLM Coding Plan Pro',
    limits: [
      { type: 'TIME_LIMIT', percentage: 3, currentValue: 30, usage: 1000 },
      { type: 'TOKENS_LIMIT', percentage: 17, nextResetTime: 2000 },
      { type: 'CREDIT_LIMIT', percentage: 42, currentValue: 42, usage: 100, nextResetTime: 1000 },
    ],
  },
})

test('parse sorts windows by reset and maps MCP', () => {
  const q = parseQuota(SAMPLE)
  expect(q).not.toBe(null)
  expect(q!.plan).toBe('GLM Coding Plan Pro')
  expect(q!.five?.percentage).toBe(42)
  expect(q!.week?.percentage).toBe(17)
  expect(q!.mcp?.currentValue).toBe(30)
})

test('empty data parses to null', () => {
  expect(parseQuota(JSON.stringify({ data: {} }))).toBe(null)
  expect(parseQuota('not json')).toBe(null)
  expect(parseQuota('{}')).toBe(null)
})

test('mcp without counts falls back to percentage', () => {
  const q = parseQuota(JSON.stringify({
    data: { planName: 'Lite', limits: [{ type: 'TIME_LIMIT', percentage: 3 }] },
  }))
  expect(fmtStatus(q)).toBe('GLM Lite | MCP 3%')
})

test('status line is single-width and sections join', () => {
  expect(fmtStatus(parseQuota(SAMPLE))).toBe('GLM coding-plan Pro | 5h 42% | wk 17% | MCP 30/1000')
})

test('non-object limit entries are ignored', () => {
  const q = parseQuota(JSON.stringify({
    data: { planName: 'Pro', limits: [null, { type: 'TOKENS_LIMIT', percentage: 9 }] },
  }))
  expect(q!.five?.percentage).toBe(9)
})

test('a window without nextResetTime sorts last', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [
        { type: 'CREDIT_LIMIT', percentage: 50 },
        { type: 'TOKENS_LIMIT', percentage: 5, nextResetTime: 1000 },
      ],
    },
  }))
  expect(q!.five?.percentage).toBe(5)
  expect(q!.week?.percentage).toBe(50)
})

test('cjk plan name is sanitized', () => {
  const q = parseQuota(JSON.stringify({
    data: { planName: '套餐Pro', limits: [{ type: 'TOKENS_LIMIT', percentage: 1 }] },
  }))
  expect(fmtStatus(q)).toBe('GLM ??Pro | 5h 1%')
})
