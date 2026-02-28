/**
 * 列表数据缓存：按 cacheKey 缓存接口结果，降低重复请求，提升操作流畅度
 * TTL 默认 60 秒，适合列表页快速切换回看
 */
const cache = new Map<
  string,
  { data: unknown[]; total: number; ts: number }
>();
const DEFAULT_TTL_MS = 60 * 1000;

export function getListCache(
  cacheKey: string,
  ttlMs: number = DEFAULT_TTL_MS
): { data: unknown[]; total: number } | null {
  const entry = cache.get(cacheKey);
  if (!entry) return null;
  if (Date.now() - entry.ts > ttlMs) {
    cache.delete(cacheKey);
    return null;
  }
  return { data: entry.data, total: entry.total };
}

export function setListCache(
  cacheKey: string,
  data: unknown[],
  total: number
): void {
  cache.set(cacheKey, { data, total, ts: Date.now() });
}

export function buildListCacheKey(
  cellId: string,
  path: string,
  params: Record<string, string | number>
): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => q.set(k, String(v)));
  return `list:${cellId}:${path}:${q.toString()}`;
}
