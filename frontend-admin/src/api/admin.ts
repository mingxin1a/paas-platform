/**
 * 管理端标准化 API：全部对接 PaaS 平台管理接口，不耦合具体业务细胞逻辑。
 * 基础路径经 Vite 代理到网关 /api
 */

const AUTH_KEY = "superpaas_admin_auth";

function getToken(): string | null {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    const j = JSON.parse(raw);
    return j.token || null;
  } catch {
    return null;
  }
}

function requestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function adminHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    Authorization: "Bearer " + (getToken() || ""),
    "X-Request-ID": requestId(),
    "Content-Type": "application/json",
    ...extra,
  };
}

const api = (path: string, opts?: RequestInit) =>
  fetch(path.startsWith("/") ? path : `/api${path}`, { ...opts, headers: adminHeaders(opts?.headers as Record<string, string>) });

// ---------- 细胞管理 ----------

export type CellRow = { id: string; name: string; enabled: boolean; baseUrl: string };

export async function fetchAdminCells(): Promise<{ ok: boolean; data?: CellRow[]; error?: string }> {
  const res = await api("/api/admin/cells");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: [] };
  return { ok: true, data: (data as { data?: CellRow[] }).data ?? [] };
}

export async function patchCellEnabled(cellId: string, enabled: boolean): Promise<{ ok: boolean; data?: { id: string; enabled: boolean }; error?: string }> {
  const res = await fetch("/api/admin/cells/" + cellId, {
    method: "PATCH",
    headers: adminHeaders(),
    body: JSON.stringify({ enabled }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, data: data as { id: string; enabled: boolean } };
}

// ---------- 治理中心（健康状态等，经网关代理） ----------

export type GovernanceCell = { cell: string; base_url?: string; healthy?: boolean; status?: string };

export async function fetchGovernanceCells(): Promise<{ ok: boolean; data?: GovernanceCell[]; error?: string }> {
  const res = await api("/api/admin/governance/cells");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: [] };
  const list = Array.isArray(data) ? data : (data as { cells?: GovernanceCell[]; data?: GovernanceCell[] }).cells ?? (data as { data?: GovernanceCell[] }).data ?? [];
  return { ok: true, data: list };
}

/** 治理中心健康摘要（各细胞健康状态） */
export async function fetchGovernanceHealthCells(): Promise<{ ok: boolean; data?: Record<string, boolean>; error?: string }> {
  const res = await api("/api/admin/governance/health/cells");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: {} };
  return { ok: true, data: (data as Record<string, unknown>)?.cells ?? data ?? {} };
}

// ---------- 路由配置 ----------

export async function fetchRoutes(): Promise<{ ok: boolean; routes?: Record<string, string>; total?: number; error?: string }> {
  const res = await api("/api/admin/routes");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, routes: {} };
  return { ok: true, routes: (data as { routes?: Record<string, string> }).routes ?? {}, total: (data as { total?: number }).total ?? 0 };
}

// ---------- 接入校验 ----------

export async function fetchVerifyReport(): Promise<{ ok: boolean; message?: string; reportUrl?: string; standard?: string; error?: string }> {
  const res = await api("/api/admin/verify-report");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, ...(data as { message?: string; reportUrl?: string; standard?: string }) };
}

export async function triggerCellsVerify(): Promise<{ ok: boolean; message?: string; status?: string; error?: string }> {
  const res = await fetch("/api/admin/cells/verify", {
    method: "POST",
    headers: adminHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, ...(data as { message?: string; status?: string }) };
}

/** 细胞接口文档 URL（经网关代理，新窗口打开） */
export function getCellDocsUrl(cellId: string, path = "docs"): string {
  const base = typeof window !== "undefined" ? window.location.origin : "";
  return `${base}/api/admin/cells/${encodeURIComponent(cellId)}/docs${path ? "/" + path : ""}`;
}

// ---------- 用户与权限配置 ----------

export type AdminUser = { id: string; username: string; role: string; allowedCells: string[] };

export async function fetchAdminUsers(): Promise<{ ok: boolean; data?: AdminUser[]; error?: string }> {
  const res = await api("/api/admin/users");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: [] };
  return { ok: true, data: (data as { data?: AdminUser[] }).data ?? [] };
}

export async function patchUserAllowedCells(userId: string, allowedCells: string[]): Promise<{ ok: boolean; data?: { id: string; allowedCells: string[] }; error?: string }> {
  const res = await fetch("/api/admin/users/" + encodeURIComponent(userId), {
    method: "PATCH",
    headers: adminHeaders(),
    body: JSON.stringify({ allowedCells }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, data: data as { id: string; allowedCells: string[] } };
}

// ---------- PaaS 核心层运行监控 ----------

export type HealthSummary = { gateway?: string; cells?: { cell?: string; status?: string }[]; governanceError?: string };

export async function fetchHealthSummary(): Promise<{ ok: boolean; data?: HealthSummary; error?: string }> {
  const res = await api("/api/admin/health-summary");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, data: data as HealthSummary };
}

// ---------- 租户管理（对接 /api/admin/tenants） ----------

export type TenantRow = { id: string; name: string; status?: string; createdAt?: string };

export async function fetchTenants(): Promise<{ ok: boolean; data?: TenantRow[]; error?: string }> {
  const res = await api("/api/admin/tenants");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: [] };
  return { ok: true, data: (data as { data?: TenantRow[] }).data ?? [] };
}

// ---------- 系统配置（对接 /api/admin/config） ----------

export async function fetchSystemConfig(): Promise<{ ok: boolean; data?: Record<string, unknown>; error?: string }> {
  const res = await api("/api/admin/config");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message };
  return { ok: true, data: (data as Record<string, unknown>) ?? {} };
}

// ---------- 告警管理（对接 /api/admin/alerts 或 Prometheus Alertmanager） ----------

export type AlertRow = { id?: string; alertname?: string; severity?: string; state?: string; summary?: string };

export async function fetchAlerts(): Promise<{ ok: boolean; data?: AlertRow[]; error?: string }> {
  const res = await api("/api/admin/alerts");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: (data as { message?: string }).message, data: [] };
  return { ok: true, data: (data as { data?: AlertRow[] }).data ?? [] };
}
