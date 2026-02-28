/**
 * 网关 API 客户端：所有请求统一经网关转发，不直接调用细胞接口
 * 《接口设计说明书》3.1.3：X-Request-ID、Authorization、X-Tenant-Id；全链路追踪
 * 开发时由 Vite proxy 将 /api 转发到网关（vite.config.ts）
 */
import { request, newRequestId } from "./request";

export { getGatewayHeaders } from "./request";

export interface GatewayFetchResult<T = unknown> {
  data?: T;
  ok: boolean;
  status: number;
  error?: string;
}

/**
 * 统一经网关的请求：自动附加 X-Request-ID、Authorization、X-Tenant-Id
 * 401 时由 request 模块触发 onUnauthorized，跳转登录
 */
export async function gatewayFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<GatewayFetchResult<T>> {
  const res = await request<T>(path, options);
  return {
    ok: res.ok,
    status: res.status,
    data: res.data,
    error: res.error,
  };
}

/** 请求细胞主列表（经网关 /api/v1/{cellId}{path}），支持分页与查询参数 */
export function fetchCellList(
  cellId: string,
  path: string,
  params?: { page?: number; pageSize?: number; [k: string]: string | number | undefined }
) {
  const search = new URLSearchParams();
  if (params?.page != null) search.set("page", String(params.page));
  if (params?.pageSize != null) search.set("pageSize", String(params.pageSize));
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (k !== "page" && k !== "pageSize" && v !== undefined && v !== "") search.set(k, String(v));
  });
  const qs = search.toString();
  const url = `/api/v1/${cellId}${path}${qs ? `?${qs}` : ""}`;
  return gatewayFetch<{ data?: unknown[]; total?: number }>(url);
}

/** 细胞创建/提交（POST 经网关） */
export function fetchCellPost<T = unknown>(
  cellId: string,
  path: string,
  body: Record<string, unknown>
): Promise<GatewayFetchResult<T>> {
  return gatewayFetch<T>(`/api/v1/${cellId}${path}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** 请求细胞详情（经网关） */
export function fetchCellDetail(cellId: string, path: string, id: string) {
  const detailPath = path.replace(/\/$/, "") + "/" + encodeURIComponent(id);
  return gatewayFetch<Record<string, unknown>>(`/api/v1/${cellId}${detailPath}`);
}

/** 细胞健康检查（经网关） */
export function fetchCellHealth(cellId: string) {
  return gatewayFetch<{ status?: string; cell?: string }>(`/api/v1/${cellId}/health`);
}

/** 从网关获取细胞列表（需鉴权，用于权限过滤与展示） */
export interface GatewayCellItem {
  id: string;
  name: string;
  enabled?: boolean;
  baseUrl?: string;
}

export async function fetchGatewayCells(): Promise<GatewayFetchResult<{ data?: GatewayCellItem[]; total?: number }>> {
  return gatewayFetch<{ data?: GatewayCellItem[]; total?: number }>("/api/admin/cells");
}

/** 批次2 看板数据（MES/WMS/TMS 等） */
export function fetchBoard(cellId: string) {
  return gatewayFetch<Record<string, unknown>>(`/api/v1/${cellId}/board`);
}

/** 批次2 WMS 扫码入库 */
export function scanInbound(
  cellId: string,
  body: { orderId: string; barcode: string; quantity?: number }
) {
  return gatewayFetch<{ accepted?: boolean }>(`/api/v1/${cellId}/scan/inbound`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** 批次2 WMS 扫码出库 */
export function scanOutbound(
  cellId: string,
  body: { orderId: string; barcode: string; quantity?: number }
) {
  return gatewayFetch<{ accepted?: boolean }>(`/api/v1/${cellId}/scan/outbound`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** 批次2 TMS 运单轨迹 */
export function fetchTracks(cellId: string, shipmentId: string) {
  return gatewayFetch<{ data?: Array<{ trackId?: string; nodeName?: string; lat?: string; lng?: string; occurredAt?: string }> }>(
    `/api/v1/${cellId}/tracks?shipmentId=${encodeURIComponent(shipmentId)}`
  );
}

export { newRequestId };
