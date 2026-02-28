/**
 * 统一 API 请求封装
 * 依据：网关规范、《接口设计说明书》3.1.3
 * - 所有请求经网关转发，不直接调用细胞接口
 * - 统一添加 X-Request-ID（全链路追踪）、Authorization、X-Tenant-Id、Content-Type
 * - 401 时触发 onUnauthorized，由 AuthContext 清空登录态并跳转登录页
 */

const AUTH_KEY = "superpaas_client_auth";

/** 网关 Base URL：开发时由 Vite proxy 转发 /api -> 网关，生产同源 */
const BASE = "";

function newRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    const j = JSON.parse(raw);
    return j?.token ?? null;
  } catch {
    return null;
  }
}

export type UnauthorizedCallback = () => void;

let onUnauthorized: UnauthorizedCallback | null = null;

export function setUnauthorizedCallback(cb: UnauthorizedCallback | null): void {
  onUnauthorized = cb;
}

/**
 * 构建默认请求头（对齐网关规范）
 * - Content-Type: application/json
 * - Authorization: Bearer <token>
 * - X-Tenant-Id
 * - X-Request-ID（全链路追踪，每个请求唯一）
 */
export function buildHeaders(options?: { skipAuth?: boolean }): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-ID": newRequestId(),
    "X-Tenant-Id": typeof window !== "undefined" ? (localStorage.getItem("tenantId") || "default") : "default",
  };
  if (!options?.skipAuth) {
    const token = getStoredToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export interface RequestResult<T = unknown> {
  ok: boolean;
  status: number;
  data?: T;
  error?: string;
}

/**
 * 统一请求：经网关、带规范请求头，401 时触发登出并跳转登录
 */
export async function request<T = unknown>(
  path: string,
  init: RequestInit = {},
  options?: { skipAuth?: boolean }
): Promise<RequestResult<T>> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers = new Headers(init.headers as HeadersInit);
  const defaultHeaders = buildHeaders(options);
  for (const [k, v] of Object.entries(defaultHeaders)) {
    if (!headers.has(k)) headers.set(k, v);
  }
  if (!headers.has("X-Request-ID")) headers.set("X-Request-ID", newRequestId());

  try {
    const res = await fetch(url, { ...init, headers });
    let data: T | undefined;
    const ct = res.headers.get("content-type");
    if (ct?.includes("application/json")) {
      try {
        data = (await res.json()) as T;
      } catch {
        // ignore
      }
    }

    if (res.status === 401) {
      onUnauthorized?.();
      const err = (data as { message?: string })?.message ?? "登录已过期，请重新登录";
      return { ok: false, status: 401, error: err, data };
    }

    if (!res.ok) {
      const err = (data as { message?: string })?.message ?? res.statusText;
      return { ok: false, status: res.status, error: err, data };
    }
    return { ok: true, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, error: (e as Error).message };
  }
}

/** 兼容旧用法：返回默认请求头（含 X-Request-ID、Authorization、X-Tenant-Id） */
export function getGatewayHeaders(): Record<string, string> {
  return buildHeaders();
}

export { BASE, AUTH_KEY, newRequestId, getStoredToken };
