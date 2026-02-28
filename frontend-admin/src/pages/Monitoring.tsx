/**
 * 管理端 - 监控大盘：健康度、细胞状态、Grafana 入口
 * 数据来源：GET /api/admin/health-summary
 */
import { useState, useEffect } from "react";
import { fetchHealthSummary, type HealthSummary } from "@/api/admin";

const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || "";

export function Monitoring() {
  const [data, setData] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchHealthSummary()
      .then((r) => {
        if (r.ok && r.data) setData(r.data);
        else setError(r.error ?? "加载失败");
      })
      .finally(() => setLoading(false));
    const t = setInterval(() => {
      fetchHealthSummary().then((r) => r.ok && r.data && setData(r.data));
    }, 30000);
    return () => clearInterval(t);
  }, []);

  if (loading) return <div>加载中…</div>;
  if (error) return <div style={{ color: "var(--color-error)" }}>{error}</div>;

  const cells = data?.cells ?? [];
  const gatewayUp = data?.gateway === "up";

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>监控大盘</h1>
      {GRAFANA_URL && (
        <p style={{ marginBottom: 16 }}>
          <a href={GRAFANA_URL} target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary)" }}>
            打开 Grafana 监控大盘 →
          </a>
        </p>
      )}
      <section style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>健康度</h2>
        <p>网关：<span style={{ color: gatewayUp ? "green" : "red" }}>{gatewayUp ? "正常" : "异常"}</span></p>
        {data?.governanceError && <p style={{ color: "orange" }}>治理中心：{data.governanceError}</p>}
        <table style={{ borderCollapse: "collapse", marginTop: 8, width: "100%", maxWidth: 480 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ textAlign: "left", padding: 10 }}>细胞</th>
              <th style={{ textAlign: "left", padding: 10 }}>状态</th>
            </tr>
          </thead>
          <tbody>
            {cells.length ? cells.map((c: { cell?: string; status?: string }, i: number) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: 10 }}>{c.cell ?? "-"}</td>
                <td style={{ padding: 10 }}>{c.status ?? (c as unknown as { healthy?: boolean }).healthy ? "正常" : "未知"}</td>
              </tr>
            )) : (
              <tr><td colSpan={2} style={{ padding: 10 }}>暂无细胞数据（请配置治理中心）</td></tr>
            )}
          </tbody>
        </table>
      </section>
      <section style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>QPS / 资源占用</h2>
        <p style={{ color: "var(--color-text-secondary)" }}>对接 Prometheus/Grafana 后可在此嵌入或跳转至详细大盘。</p>
      </section>
    </div>
  );
}
