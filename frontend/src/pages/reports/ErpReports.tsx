/**
 * ERP 专属报表：采购、销售、库存；权限由网关校验
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { fetchModuleReport, type ReportData } from "@/api/analytics";
import { useAuth } from "@/context/AuthContext";
import { SimpleBarChart } from "@/components/charts/SimpleBarChart";
import { ReportFilters } from "@/components/reports/ReportFilters";
import { ExportBar } from "@/components/reports/ExportBar";
import styles from "../CellList.module.css";

function defaultRange() {
  const e = new Date();
  const s = new Date(e.getFullYear(), e.getMonth(), 1);
  return { start: s.toISOString().slice(0, 10), end: e.toISOString().slice(0, 10) };
}

export function ErpReports() {
  const { user } = useAuth();
  const allowed = !user || user.role === "admin" || user.allowedCells?.includes("erp");
  const [purchase, setPurchase] = useState<ReportData | null>(null);
  const [sales, setSales] = useState<ReportData | null>(null);
  const [inventory, setInventory] = useState<ReportData | null>(null);
  const [startDate, setStartDate] = useState(defaultRange().start);
  const [endDate, setEndDate] = useState(defaultRange().end);
  const [compare, setCompare] = useState<"none" | "yoy" | "mom">("none");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!allowed) return;
    setLoading(true);
    Promise.all([
      fetchModuleReport("erp", "purchase", { startDate, endDate }),
      fetchModuleReport("erp", "sales", { startDate, endDate }),
      fetchModuleReport("erp", "inventory", { startDate, endDate }),
    ]).then(([r1, r2, r3]) => {
      if (r1.ok && r1.data) setPurchase(r1.data);
      if (r2.ok && r2.data) setSales(r2.data);
      if (r3.ok && r3.data) setInventory(r3.data);
    }).finally(() => setLoading(false));
  }, [allowed, startDate, endDate]);

  const exportExcel = () => {
    const rows = [
      ["采购", ""],
      ...(purchase?.series ?? []).map((s) => [s.name, String(s.value)]),
      [],
      ["销售", ""],
      ...(sales?.series ?? []).map((s) => [s.name, String(s.value)]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "erp_report.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!allowed) {
    return (
      <div className={styles.page}>
        <p>无权限查看 ERP 报表。</p>
        <Link to="/">返回</Link>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/analytics" className={styles.back}>← 返回</Link>
        <h1 className={styles.title}>ERP 报表</h1>
        <p className={styles.desc}>采购、销售、库存</p>
      </div>
      <ReportFilters
        startDate={startDate}
        endDate={endDate}
        compare={compare}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onCompareChange={setCompare}
      />
      <ExportBar onExportExcel={exportExcel} onExportPDF={() => window.print()} loading={loading} />
      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 24 }}>
          <section>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>采购趋势</h2>
            {purchase?.series?.length ? (
              <SimpleBarChart data={purchase.series.map((s) => ({ name: s.name, value: s.value }))} unit="万" />
            ) : (
              <div className={styles.empty}>暂无数据</div>
            )}
          </section>
          <section>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>销售趋势</h2>
            {sales?.series?.length ? (
              <SimpleBarChart data={sales.series.map((s) => ({ name: s.name, value: s.value }))} unit="万" />
            ) : (
              <div className={styles.empty}>暂无数据</div>
            )}
          </section>
          <section>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>库存分析</h2>
            {inventory?.series?.length ? (
              <SimpleBarChart data={inventory.series.map((s) => ({ name: s.name, value: s.value }))} />
            ) : (
              <div className={styles.empty}>暂无数据</div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
