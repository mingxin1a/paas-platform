import { useState, useEffect } from "react";

const MOCK: { username: string; role: string; cells: string }[] = [
  { username: "admin", role: "admin", cells: "all" },
  { username: "client", role: "client", cells: "crm,erp,wms" },
  { username: "operator", role: "client", cells: "crm,wms,oa" },
];

export function UserPermission() {
  const [list, setList] = useState(MOCK);
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
    fetch("/api/admin/users", { headers: { Authorization: "Bearer " + (token || "") } })
      .then((res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(res.status === 401 ? "未授权" : "请求失败");
        return res.json();
      })
      .then((data: { data?: { username: string; role: string; allowedCells?: string[] }[] } | null) => {
        if (data == null) {
          setList(MOCK);
          setError(null);
          return;
        }
        const arr = data?.data;
        if (Array.isArray(arr) && arr.length > 0) {
          setList(arr.map((u) => ({
            username: u.username,
            role: u.role,
            cells: Array.isArray(u.allowedCells) ? u.allowedCells.join(",") : "all",
          })));
          setError(null);
        } else setList(MOCK);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载失败");
        setList(MOCK);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>用户与权限</h1>
      <p style={{ color: "var(--color-text)", opacity: 0.8 }}>对接 <code>/api/admin/users</code> 后展示真实数据，当前为占位或 Mock。</p>
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}
      {loading ? (
        <p>加载中…</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
          <thead><tr><th>User</th><th>Role</th><th>Cells</th></tr></thead>
          <tbody>{list.map((u) => <tr key={u.username}><td>{u.username}</td><td>{u.role}</td><td>{u.cells}</td></tr>)}</tbody>
        </table>
      )}
    </div>
  );
}
