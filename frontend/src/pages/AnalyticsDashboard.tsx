/**
 * 全平台经营分析首页大屏：销售额、采购额、库存周转率、审批效率、生产完成率
 * 数据权限：仅展示用户有权限的汇总指标，数据来自 /api/analytics/kpi
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchAnalyticsKPI, type AnalyticsKPI } from "@/api/analytics";
import { useAuth } from "@/context/AuthContext";
import { KpiCard } from "@/components/charts/KpiCard";
import styles from "./CellList.module.css";

function defaultDateRange() {
  const e = new Date();
  const s = new Date(e.getFullYear(), e.getMonth(), 1);
  return { start: s.toISOString().slice(0, 10), end: e.toISOString().slice(0, 10) };
}

export function AnalyticsDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [kpi, setKpi] = useState<AnalyticsKPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState("month");
  const { start, end } = defaultDateRange();

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalyticsKPI({ period, startDate: start, endDate: end })
      .then((r) => {
        if (r.ok && r.data) setKpi(r.data);
        else setError(r.error ?? "加载失败");
      })
      .finally(() => setLoading(false));
  }, [period, start, end]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>经营分析大屏</h1>
        <p className={styles.desc}>核心经营指标（数据按权限展示）</p>
        <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            aria-label="统计周期"
            style={{ padding: 6, border: "1px solid var(--color-border)", borderRadius: 4 }}
          >
            <option value="day">本日</option>
            <option value="week">本周</option>
            <option value="month">本月</option>
            <option value="quarter">本季</option>
            <option value="year">本年</option>
          </select>
          <Link to="/reports/custom" className={styles.exportBtn}>自定义报表</Link>
          <Link to="/bigscreen/decision" className={styles.exportBtn}>大屏</Link>
        </div>
      </div>
      {error && <div className={styles.error} role="alert">{error}</div>}
      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
      ) : kpi ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
          <KpiCard title="销售额" value={kpi.salesAmount ?? 0} unit="元" sub={period === "month" ? "本月" : period} onClick={() => navigate("/reports/erp")} />
          <KpiCard title="采购额" value={kpi.purchaseAmount ?? 0} unit="元" sub={period === "month" ? "本月" : period} onClick={() => navigate("/reports/erp")} />
          <KpiCard title="库存周转率" value={kpi.inventoryTurnoverRate ?? 0} unit="次" onClick={() => navigate("/reports/erp")} />
          <KpiCard title="审批效率" value={kpi.approvalEfficiency ?? 0} unit="%" />
          <KpiCard title="生产完成率" value={kpi.productionCompletionRate ?? 0} unit="%" onClick={() => navigate("/reports/mes")} />
        </div>
      ) : null}
      <section style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>模块报表入口</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {user?.allowedCells?.includes("crm") && <Link to="/reports/crm" className={styles.exportBtn}>CRM 报表</Link>}
          {user?.allowedCells?.includes("erp") && <Link to="/reports/erp" className={styles.exportBtn}>ERP 报表</Link>}
          {user?.allowedCells?.includes("mes") && <Link to="/reports/mes" className={styles.exportBtn}>MES 报表</Link>}
          {(user?.role === "admin" || (user?.allowedCells?.length ?? 0) === 0) && (
            <>
              <Link to="/reports/crm" className={styles.exportBtn}>CRM 报表</Link>
              <Link to="/reports/erp" className={styles.exportBtn}>ERP 报表</Link>
              <Link to="/reports/mes" className={styles.exportBtn}>MES 报表</Link>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
