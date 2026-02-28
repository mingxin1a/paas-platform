/**
 * CRM 专属报表：销售漏斗、客户分析；数据权限由网关按用户/租户过滤
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { fetchModuleReport, type ReportData } from "@/api/analytics";
import { useAuth } from "@/context/AuthContext";
import { SimpleBarChart } from "@/components/charts/SimpleBarChart";
import { SimplePieLegend } from "@/components/charts/SimplePieLegend";
import { ReportFilters } from "@/components/reports/ReportFilters";
import { ExportBar } from "@/components/reports/ExportBar";
import styles from "../CellList.module.css";

function defaultRange() {
  const e = new Date();
  const s = new Date(e.getFullYear(), e.getMonth(), 1);
  return { start: s.toISOString().slice(0, 10), end: e.toISOString().slice(0, 10) };
}

export function CrmReports() {
  const { user } = useAuth();
  const allowed = !user || user.role === "admin" || user.allowedCells?.includes("crm");
  const [funnel, setFunnel] = useState<ReportData | null>(null);
  const [customer, setCustomer] = useState<ReportData | null>(null);
  const [startDate, setStartDate] = useState(defaultRange().start);
  const [endDate, setEndDate] = useState(defaultRange().end);
  const [compare, setCompare] = useState<"none" | "yoy" | "mom">("none");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!allowed) return;
    setLoading(true);
    Promise.all([
      fetchModuleReport("crm", "sales-funnel", { startDate, endDate }),
      fetchModuleReport("crm", "customer-analysis", { startDate, endDate }),
    ]).then(([r1, r2]) => {
      if (r1.ok && r1.data) setFunnel(r1.data);
      if (r2.ok && r2.data) setCustomer(r2.data);
    }).finally(() => setLoading(false));
  }, [allowed, startDate, endDate]);

  const exportExcel = () => {
    const rows = [["销售漏斗", ""], ...(funnel?.series ?? []).map((s) => [s.name, String(s.value)]), [], ["客户分析", ""], ...(customer?.series ?? []).map((s) => [s.name, String(s.value)])];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "crm_report.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!allowed) {
    return (
      <div className={styles.page}><p>无权限查看 CRM 报表。</p><Link to="/">返回</Link></div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/analytics" className={styles.back}>← 返回</Link>
        <h1 className={styles.title}>CRM 报表</h1>
        <p className={styles.desc}>销售漏斗、客户分析</p>
      </div>
      <ReportFilters startDate={startDate} endDate={endDate} compare={compare} onStartDateChange={setStartDate} onEndDateChange={setEndDate} onCompareChange={setCompare} />
      <ExportBar onExportExcel={exportExcel} onExportPDF={() => window.print()} loading={loading} />
      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
          <section>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>销售漏斗</h2>
            {funnel?.series?.length ? <SimpleBarChart data={funnel.series.map((s) => ({ name: s.name, value: s.value }))} /> : <div className={styles.empty}>暂无数据</div>}
          </section>
          <section>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>客户分析</h2>
            {customer?.series?.length ? <SimplePieLegend data={customer.series.map((s) => ({ name: s.name, value: s.value }))} /> : <div className={styles.empty}>暂无数据</div>}
          </section>
        </div>
      )}
    </div>
  );
}
