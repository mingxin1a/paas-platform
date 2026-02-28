/**
 * 管理端 - 租户管理：租户列表、状态，对接 /api/admin/tenants
 */
import { useState, useEffect } from "react";
import { fetchTenants, type TenantRow } from "@/api/admin";

export function TenantManage() {
  const [list, setList] = useState<TenantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTenants()
      .then((r) => {
        if (r.ok && r.data) setList(r.data);
        else setError(r.error ?? "加载失败");
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>租户管理</h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: 16 }}>
        全平台租户列表与生命周期，对接 /api/admin/tenants。
      </p>
      {error && <p style={{ color: "var(--color-error)" }}>{error}</p>}
      {loading ? (
        <p>加载中…</p>
      ) : list.length === 0 ? (
        <p style={{ opacity: 0.8 }}>暂无租户数据（或接口未实现）。</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ textAlign: "left", padding: 10 }}>租户ID</th>
              <th style={{ textAlign: "left", padding: 10 }}>名称</th>
              <th style={{ textAlign: "left", padding: 10 }}>状态</th>
              <th style={{ textAlign: "left", padding: 10 }}>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {list.map((t) => (
              <tr key={t.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: 10 }}>{t.id}</td>
                <td style={{ padding: 10 }}>{t.name}</td>
                <td style={{ padding: 10 }}>{t.status ?? "—"}</td>
                <td style={{ padding: 10 }}>{t.createdAt ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
