/**
 * 自定义报表引擎：维度、指标、图表类型、保存、导出、定时推送（推送为占位）
 * 权限：仅能选择有权限的细胞数据
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchCustomReport, type ReportData } from "@/api/analytics";
import { useAllowedCells } from "@/api/cells";
import { SimpleBarChart } from "@/components/charts/SimpleBarChart";
import { SimplePieLegend } from "@/components/charts/SimplePieLegend";
import { ReportFilters } from "@/components/reports/ReportFilters";
import { ExportBar } from "@/components/reports/ExportBar";
import styles from "../CellList.module.css";

const SAVED_REPORTS_KEY = "superpaas_saved_reports";

export interface SavedReportConfig {
  id: string;
  name: string;
  cellId: string;
  dimensions: string[];
  metrics: string[];
  chartType: "bar" | "pie";
  createdAt: string;
}

const DIMENSION_OPTIONS = ["时间", "部门", "区域", "产品", "客户"];
const METRIC_OPTIONS = ["金额", "数量", "笔数", "占比"];

function defaultRange() {
  const e = new Date();
  const s = new Date(e.getFullYear(), e.getMonth(), 1);
  return { start: s.toISOString().slice(0, 10), end: e.toISOString().slice(0, 10) };
}

export function CustomReport() {
  const { cells } = useAllowedCells();
  const [cellId, setCellId] = useState("");
  const [dimensions, setDimensions] = useState<string[]>(["时间"]);
  const [metrics, setMetrics] = useState<string[]>(["金额"]);
  const [chartType, setChartType] = useState<"bar" | "pie">("bar");
  const [startDate, setStartDate] = useState(defaultRange().start);
  const [endDate, setEndDate] = useState(defaultRange().end);
  const [compare, setCompare] = useState<"none" | "yoy" | "mom">("none");
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [reportName, setReportName] = useState("");
  const [savedList, setSavedList] = useState<SavedReportConfig[]>(() => {
    try {
      const raw = localStorage.getItem(SAVED_REPORTS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const runQuery = () => {
    setLoading(true);
    fetchCustomReport({
      cellId: cellId || undefined,
      dimensions,
      metrics,
      startDate,
      endDate,
      compare: compare === "none" ? undefined : compare,
    }).then((r) => {
      if (r.ok && r.data) setData(r.data);
      else setData({ series: [] });
    }).finally(() => setLoading(false));
  };

  const saveReport = () => {
    if (!reportName.trim()) return;
    const id = "r-" + Date.now();
    const saved: SavedReportConfig = {
      id,
      name: reportName.trim(),
      cellId,
      dimensions: [...dimensions],
      metrics: [...metrics],
      chartType,
      createdAt: new Date().toISOString(),
    };
    const next = [...savedList, saved];
    setSavedList(next);
    localStorage.setItem(SAVED_REPORTS_KEY, JSON.stringify(next));
  };

  const loadSaved = (s: SavedReportConfig) => {
    setCellId(s.cellId);
    setDimensions(s.dimensions);
    setMetrics(s.metrics);
    setChartType(s.chartType);
    setReportName(s.name);
  };

  const exportExcel = () => {
    const rows = [["自定义报表", ""], ...(data?.series ?? []).map((s) => [s.name, String(s.value)])];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "custom_report.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/analytics" className={styles.back}>← 返回</Link>
        <h1 className={styles.title}>自定义报表</h1>
        <p className={styles.desc}>选择维度、指标与图表类型，保存后支持导出与定时推送</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 24, marginTop: 16 }}>
        <div style={{ padding: 16, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8 }}>
          <h2 style={{ fontSize: 14, marginBottom: 12 }}>数据源（按权限）</h2>
          <select value={cellId} onChange={(e) => setCellId(e.target.value)} style={{ width: "100%", padding: 6, marginBottom: 12 }}>
            <option value="">全平台</option>
            {cells.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <h2 style={{ fontSize: 14, marginBottom: 8 }}>维度</h2>
          {DIMENSION_OPTIONS.map((d) => (
            <label key={d} style={{ display: "block", marginBottom: 4 }}>
              <input type="checkbox" checked={dimensions.includes(d)} onChange={(e) => setDimensions(e.target.checked ? [...dimensions, d] : dimensions.filter((x) => x !== d))} />
              {d}
            </label>
          ))}
          <h2 style={{ fontSize: 14, marginTop: 12, marginBottom: 8 }}>指标</h2>
          {METRIC_OPTIONS.map((m) => (
            <label key={m} style={{ display: "block", marginBottom: 4 }}>
              <input type="checkbox" checked={metrics.includes(m)} onChange={(e) => setMetrics(e.target.checked ? [...metrics, m] : metrics.filter((x) => x !== m))} />
              {m}
            </label>
          ))}
          <h2 style={{ fontSize: 14, marginTop: 12, marginBottom: 8 }}>图表类型</h2>
          <select value={chartType} onChange={(e) => setChartType(e.target.value as "bar" | "pie")} style={{ width: "100%", padding: 6 }}>
            <option value="bar">柱状图</option>
            <option value="pie">饼图</option>
          </select>
          <ReportFilters startDate={startDate} endDate={endDate} compare={compare} onStartDateChange={setStartDate} onEndDateChange={setEndDate} onCompareChange={setCompare} />
          <button type="button" className={styles.exportBtn} onClick={runQuery} disabled={loading} style={{ marginRight: 8 }}>查询</button>
          <input type="text" placeholder="报表名称" value={reportName} onChange={(e) => setReportName(e.target.value)} style={{ padding: 6, width: 120, marginTop: 8 }} />
          <button type="button" className={styles.exportBtn} onClick={saveReport} style={{ marginLeft: 4, marginTop: 8 }}>保存</button>
        </div>

        <div>
          {savedList.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, marginBottom: 8 }}>已保存报表</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {savedList.map((s) => (
                  <button key={s.id} type="button" onClick={() => loadSaved(s)} style={{ padding: "6px 12px", border: "1px solid var(--color-border)", borderRadius: 4 }}>{s.name}</button>
                ))}
              </div>
            </div>
          )}
          <ExportBar onExportExcel={exportExcel} onExportPDF={() => window.print()} loading={loading} />
          {loading ? (
            <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
          ) : data?.series?.length ? (
            chartType === "bar" ? (
              <SimpleBarChart data={data.series.map((s) => ({ name: s.name, value: s.value }))} />
            ) : (
              <SimplePieLegend data={data.series.map((s) => ({ name: s.name, value: s.value }))} />
            )
          ) : (
            <div className={styles.empty}>选择维度与指标后点击「查询」</div>
          )}
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 16 }}>定时推送：对接后端任务配置后，可在此选择推送周期与接收人。</p>
        </div>
      </div>
    </div>
  );
}
