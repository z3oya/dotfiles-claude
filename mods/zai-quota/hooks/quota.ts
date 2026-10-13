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
  five: Limit | null
  week: Limit | null
  mcp: Limit | null
}

// The mod only speaks to GLM endpoints: an unset base keeps the bigmodel
// default, any other relay opts the mod out (null).
export const BIGMODEL_HOST = 'https://open.bigmodel.cn'
export const ZAI_HOST = 'https://api.z.ai'

export function hostOf(base: string | null | undefined): string | null {
  if (!base) return BIGMODEL_HOST
  if (base.includes('z.ai')) return ZAI_HOST
  if (base.includes('bigmodel.cn')) return BIGMODEL_HOST
  return null
}

const toNum = (v: unknown): number =>
  typeof v === 'number' ? v : typeof v === 'string' && /^\d+$/.test(v) ? Number(v) : NaN

// null: 200 but nothing usable (bad body, a team key without org headers, or
// no limit type we display).
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
  if (windows.length === 0 && !mcp) return null

  return { five, week, mcp }
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
  const parts: string[] = []
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
