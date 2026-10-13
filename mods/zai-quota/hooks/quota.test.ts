import { expect, test } from 'claude-code/testing'

import { fmtStatus, parseQuota } from './quota'

// Windows map by unit (3 → 5h, 6 → week); fixture interleaves reset and wire order.
const SAMPLE = JSON.stringify({
  data: {
    planName: 'GLM Coding Plan Pro',
    limits: [
      { type: 'TIME_LIMIT', unit: 5, number: 1, percentage: 100, currentValue: 1001, usage: 1000, remaining: 0, nextResetTime: 1792766618983 },
      { type: 'TOKENS_LIMIT', unit: 6, number: 1, percentage: 81, nextResetTime: 1792344395999 },
      { type: 'TOKENS_LIMIT', unit: 3, number: 5, percentage: 1, nextResetTime: 1791915807512 },
    ],
  },
})

// Verbatim API body captured 2026-10-13 (plan comes from `level`).
const REAL = JSON.stringify({
  code: 200,
  msg: '操作成功',
  data: {
    limits: [
      { type: 'TIME_LIMIT', unit: 5, number: 1, usage: 1000, currentValue: 1001, remaining: 0, percentage: 100, nextResetTime: 1792766618983, usageDetails: [{ modelCode: 'search-prime', usage: 830 }] },
      { type: 'TOKENS_LIMIT', unit: 3, number: 5, percentage: 1, nextResetTime: 1791915807512 },
      { type: 'TOKENS_LIMIT', unit: 6, number: 1, percentage: 81, nextResetTime: 1792344395999 },
    ],
    level: 'pro',
  },
  success: true,
})

test('parse maps windows by unit regardless of reset and wire order', () => {
  const q = parseQuota(SAMPLE)
  expect(q).not.toBe(null)
  expect(q!.plan).toBe('GLM Coding Plan Pro')
  expect(q!.five?.percentage).toBe(1)
  expect(q!.week?.percentage).toBe(81)
  expect(q!.mcp?.currentValue).toBe(1001)
})

test('real API body with level field maps correctly', () => {
  expect(fmtStatus(parseQuota(REAL))).toBe('GLM pro | 5h 1% | wk 81% | MCP 1001/1000')
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
  expect(fmtStatus(parseQuota(SAMPLE))).toBe('GLM coding-plan Pro | 5h 1% | wk 81% | MCP 1001/1000')
})

test('non-object limit entries are ignored', () => {
  const q = parseQuota(JSON.stringify({
    data: { planName: 'Pro', limits: [null, { type: 'TOKENS_LIMIT', percentage: 9 }] },
  }))
  expect(q!.five?.percentage).toBe(9)
})

test('a 0% window without nextResetTime keeps its slot', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [
        { type: 'TOKENS_LIMIT', unit: 6, number: 1, percentage: 81, nextResetTime: 1792344395999 },
        { type: 'TOKENS_LIMIT', unit: 3, number: 5, percentage: 0 },
      ],
    },
  }))
  expect(q!.five?.percentage).toBe(0)
  expect(q!.week?.percentage).toBe(81)
})

test('weekly reset earlier than the 5h reset still maps by unit', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [
        { type: 'TOKENS_LIMIT', unit: 3, number: 5, percentage: 40, nextResetTime: 1792766618983 },
        { type: 'TOKENS_LIMIT', unit: 6, number: 1, percentage: 90, nextResetTime: 1792344395999 },
      ],
    },
  }))
  expect(q!.five?.percentage).toBe(40)
  expect(q!.week?.percentage).toBe(90)
})

test('unknown or missing unit falls back to reset order', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [
        { type: 'TOKENS_LIMIT', unit: 9, percentage: 20, nextResetTime: 2000 },
        { type: 'CREDIT_LIMIT', percentage: 50, nextResetTime: 1000 },
      ],
    },
  }))
  expect(q!.five?.percentage).toBe(50)
  expect(q!.week?.percentage).toBe(20)
})

test('string unit and number are coerced', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [
        { type: 'TOKENS_LIMIT', unit: '3', number: '5', percentage: 7, nextResetTime: 500 },
        { type: 'TOKENS_LIMIT', unit: '6', number: '1', percentage: 9, nextResetTime: 400 },
      ],
    },
  }))
  expect(q!.five?.percentage).toBe(7)
  expect(fmtStatus(q)).toBe('GLM Pro | 5h 7% | wk 9%')
})

test('hour label reflects window size', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: 'Pro',
      limits: [{ type: 'TOKENS_LIMIT', unit: 3, number: 8, percentage: 10 }],
    },
  }))
  expect(fmtStatus(q)).toBe('GLM Pro | 8h 10%')
})

test('cjk plan name is sanitized', () => {
  const q = parseQuota(JSON.stringify({
    data: {
      planName: '套餐Pro',
      limits: [{ type: 'TOKENS_LIMIT', unit: 3, number: 5, percentage: 1 }],
    },
  }))
  expect(fmtStatus(q)).toBe('GLM ??Pro | 5h 1%')
})
