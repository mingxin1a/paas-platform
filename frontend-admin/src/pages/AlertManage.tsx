/**
 * 管理端 - 告警管理：告警列表与状态，对接 /api/admin/alerts 或 Prometheus Alertmanager
 */
import { useState, useEffect } from "react";
import { fetchAlerts, type AlertRow } from "@/api/admin";

export function AlertManage() {
  const [list, setList] = useState<AlertRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAlerts()
      .then((r) => {
        if (r.ok && r.data) setList(r.data);
        else setError(r.error ?? "加载失败");
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>告警管理</h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: 16 }}>
        平台告警规则与当前告警列表，对接 <code>/api/admin/alerts</code> 或 Prometheus Alertmanager。
      </p>
      {error && <p style={{ color: "var(--color-error)" }}>{error}</p>}
      {loading ? (
        <p>加载中…</p>
      ) : list.length === 0 ? (
        <p style={{ opacity: 0.8 }}>暂无告警（或接口未实现）。</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ textAlign: "left", padding: 10 }}>告警名</th>
              <th style={{ textAlign: "left", padding: 10 }}>级别</th>
              <th style={{ textAlign: "left", padding: 10 }}>状态</th>
              <th style={{ textAlign: "left", padding: 10 }}>摘要</th>
            </tr>
          </thead>
          <tbody>
            {list.map((a, i) => (
              <tr key={a.id ?? i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: 10 }}>{a.alertname ?? "—"}</td>
                <td style={{ padding: 10 }}>{a.severity ?? "—"}</td>
                <td style={{ padding: 10 }}>{a.state ?? "—"}</td>
                <td style={{ padding: 10 }}>{a.summary ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
