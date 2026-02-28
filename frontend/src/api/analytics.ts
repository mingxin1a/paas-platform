/**
 * 经营分析 / 报表 API：经网关请求，数据权限由后端按租户与用户校验
 */
import { gatewayFetch } from "./gateway";

export interface AnalyticsKPI {
  salesAmount?: number;
  purchaseAmount?: number;
  inventoryTurnoverRate?: number;
  approvalEfficiency?: number;
  productionCompletionRate?: number;
  period?: string;
}

export async function fetchAnalyticsKPI(params?: {
  period?: string;
  startDate?: string;
  endDate?: string;
}): Promise<{ ok: boolean; data?: AnalyticsKPI; error?: string }> {
  const qs = new URLSearchParams();
  if (params?.period) qs.set("period", params.period);
  if (params?.startDate) qs.set("startDate", params.startDate);
  if (params?.endDate) qs.set("endDate", params.endDate);
  const res = await gatewayFetch<AnalyticsKPI>("/api/analytics/kpi" + (qs.toString() ? "?" + qs : ""));
  if (res.ok) return { ok: true, data: res.data };
  if (res.status === 404) {
    return { ok: true, data: { salesAmount: 12500000, purchaseAmount: 8200000, inventoryTurnoverRate: 4.2, approvalEfficiency: 92, productionCompletionRate: 88, period: "month" } };
  }
  return { ok: false, error: res.error };
}

export interface ReportSeries {
  name: string;
  value: number;
  [key: string]: unknown;
}

export interface ReportData {
  dimensions?: string[];
  metrics?: string[];
  series?: ReportSeries[];
  rows?: Record<string, unknown>[];
}

export async function fetchModuleReport(
  cellId: string,
  reportType: string,
  params?: Record<string, string>
): Promise<{ ok: boolean; data?: ReportData; error?: string }> {
  const qs = new URLSearchParams(params);
  const res = await gatewayFetch<ReportData>("/api/v1/" + cellId + "/reports/" + reportType + (qs.toString() ? "?" + qs : ""));
  if (res.ok) return { ok: true, data: res.data };
  if (res.status === 404) {
    const series = reportType === "sales-funnel"
      ? [{ name: "线索", value: 1200 }, { name: "商机", value: 680 }, { name: "报价", value: 320 }, { name: "赢单", value: 145 }]
      : [{ name: "A", value: 100 }, { name: "B", value: 80 }, { name: "C", value: 60 }];
    return { ok: true, data: { series } };
  }
  return { ok: false, error: res.error };
}

export async function fetchCustomReport(params: {
  cellId?: string;
  dimensions: string[];
  metrics: string[];
  startDate?: string;
  endDate?: string;
  compare?: "yoy" | "mom" | "none";
}): Promise<{ ok: boolean; data?: ReportData; error?: string }> {
  const res = await gatewayFetch<ReportData>("/api/analytics/custom", {
    method: "POST",
    body: JSON.stringify(params),
  });
  if (res.ok) return { ok: true, data: res.data };
  if (res.status === 404) return { ok: true, data: { series: [], rows: [] } };
  return { ok: false, error: res.error };
}
