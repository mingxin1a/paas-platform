import { useState, useEffect } from "react";

type AuditEntry = { id: string; time: string; user: string; action: string; resource?: string; traceId?: string };

export function Audit() {
  const [list, setList] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = (() => {
      try {
        const raw = localStorage.getItem("superpaas_admin_auth");
        if (!raw) return null;
        const j = JSON.parse(raw);
        return j.token || null;
      } catch {
        return null;
      }
    })();
    setLoading(true);
    setError(null);
    fetch("/api/admin/audit", { headers: { Authorization: "Bearer " + (token || "") } })
      .then((res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(res.status === 401 ? "未授权" : "请求失败");
        return res.json();
      })
      .then((data: { data?: AuditEntry[] } | null) => {
        if (data == null) {
          setList([]);
          setError(null);
          return;
        }
        if (Array.isArray(data?.data)) setList(data.data);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载失败");
        setList([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>审计日志</h1>
      <p style={{ color: "var(--color-text)", opacity: 0.8 }}>对接 <code>/api/admin/audit</code> 后展示与 trace_id 关联的访问记录。</p>
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {loading ? (
        <p>加载中…</p>
      ) : list.length === 0 ? (
        <p>暂无审计记录。</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
          <thead><tr><th>时间</th><th>用户</th><th>操作</th><th>资源</th><th>TraceId</th></tr></thead>
          <tbody>
            {list.map((e) => (
              <tr key={e.id}>
                <td>{e.time}</td><td>{e.user}</td><td>{e.action}</td><td>{e.resource ?? "—"}</td><td>{e.traceId ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
