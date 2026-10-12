// Shared across every instance through $.store (one JSON file per plugin under
// the user's config directory): one reading per refresh window, the rest display.

export type CacheEntry = {
  status: string
  fetchedAt: number
  host: string
  keyTag: string
}

export type Lease = {
  owner: string
  until: number
}

// Store values come back as `unknown`; trust only a validated shape.
export function validateCache(raw: unknown): CacheEntry | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  if (typeof r.status !== 'string' || r.status.length === 0) return null
  if (typeof r.fetchedAt !== 'number' || !Number.isFinite(r.fetchedAt)) return null
  if (typeof r.host !== 'string' || r.host.length === 0) return null
  if (typeof r.keyTag !== 'string' || r.keyTag.length === 0) return null
  return raw as CacheEntry
}

export function validateLease(raw: unknown): Lease | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  if (typeof r.owner !== 'string' || r.owner.length === 0) return null
  if (typeof r.until !== 'number' || !Number.isFinite(r.until)) return null
  return raw as Lease
}

export type Refresh = 'skip' | 'standby' | 'fetch'

// skip: this account's cache is fresh. standby: a peer holds the lease. fetch: ours to do.
export function decide(input: {
  cache: CacheEntry | null
  lease: Lease | null
  now: number
  me: string
  host: string
  keyTag: string
  refreshMs: number
}): Refresh {
  const { cache, lease, now, me, host, keyTag, refreshMs } = input
  const ours = cache && cache.host === host && cache.keyTag === keyTag ? cache : null
  if (ours && now - ours.fetchedAt < refreshMs) return 'skip'
  if (lease && lease.until > now && lease.owner !== me) return 'standby'
  return 'fetch'
}

// djb2 over the key: a fingerprint to tell accounts apart, no key material on disk.
export function keyTagOf(key: string): string {
  let h = 5381
  for (let i = 0; i < key.length; i++) h = ((h << 5) + h + key.charCodeAt(i)) | 0
  return (h >>> 0).toString(36)
}
