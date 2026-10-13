export type Limit = {
  type?: string
  unit?: number
  number?: number
  percentage?: number
  usage?: number
  currentValue?: number
  nextResetTime?: number
}

export type QuotaSummary = {
  plan: string
  five: Limit | null
  week: Limit | null
  mcp: Limit | null
}

const ascii = (s: string) => s.replace(/[^\x20-\x7E]/g, '?')

const toNum = (v: unknown): number =>
  typeof v === 'number' ? v : typeof v === 'string' && /^\d+$/.test(v) ? Number(v) : NaN

function planName(data: Record<string, unknown>): string {
  for (const f of ['planName', 'plan', 'plan_type', 'packageName', 'level'] as const) {
    const v = data[f]
    if (v) return String(v)
  }
  return 'unknown'
}

// null: 200 but nothing usable (bad body, or team key without org headers).
export function parseQuota(body: string): QuotaSummary | null {
  let payload: unknown
  try {
    payload = JSON.parse(body)
  } catch {
    return null
  }
  const data = (payload as { data?: Record<string, unknown> } | undefined)?.data
  if (!data || typeof data !== 'object') return null
  const limits = Array.isArray(data.limits)
    ? (data.limits as unknown[]).filter((l): l is Limit => l != null && typeof l === 'object')
    : []
  if (limits.length === 0) return null

  // Identity is type+unit, never reset order: a 0% window omits nextResetTime,
  // and early Monday the weekly reset trails 5h's.
  const windows = limits.filter(l => l.type === 'TOKENS_LIMIT' || l.type === 'CREDIT_LIMIT')
  let five = windows.find(l => toNum(l.unit) === 3) ?? null
  let week = windows.find(l => toNum(l.unit) === 6) ?? null
  if (!five || !week) {
    // No unit on the wire: reset order is the only hint left.
    const resetAt = (l: Limit) => l.nextResetTime ?? Number.POSITIVE_INFINITY
    const rest = windows
      .filter(l => l !== five && l !== week)
      .sort((a, b) => resetAt(a) - resetAt(b) || 0) // `|| 0`: NaN keeps wire order
    if (!five) five = rest.shift() ?? null
    if (!week) week = rest.shift() ?? null
  }
  const mcp = limits.find(l => l.type === 'TIME_LIMIT') ?? null

  return { plan: ascii(planName(data)), five, week, mcp }
}

const pct = (l: Limit | null) =>
  l && Number.isFinite(l.percentage) ? `${l.percentage}%` : '?'

// Label from the wire window size; '5h' when absent or implausible.
const hourLabel = (l: Limit) => {
  const n = toNum(l.number)
  return Number.isInteger(n) && n > 0 ? `${n}h` : '5h'
}

export function fmtStatus(q: QuotaSummary | null): string {
  if (!q) return 'zai-quota: empty data (personal key needed)'
  const label = /^GLM/i.test(q.plan)
    ? q.plan.replace(/^GLM\s+(?:coding\s+plan\s+)?/i, 'GLM coding-plan ')
    : `GLM ${q.plan}`
  const parts = [label]
  if (q.five) parts.push(`${hourLabel(q.five)} ${pct(q.five)}`)
  if (q.week) parts.push(`wk ${pct(q.week)}`)
  if (q.mcp) {
    parts.push(
      q.mcp.currentValue != null && q.mcp.usage != null
        ? `MCP ${q.mcp.currentValue}/${q.mcp.usage}`
        : `MCP ${pct(q.mcp)}`,
    )
  }
  return parts.join(' | ')
}
