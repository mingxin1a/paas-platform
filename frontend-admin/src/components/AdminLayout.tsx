import { useState } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const AUTH_KEY = "superpaas_admin_auth";

export function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [panicSent, setPanicSent] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nav = [
    { path: "/", label: "概览" },
    { path: "/cells", label: "细胞治理" },
    { path: "/tenants", label: "租户管理" },
    { path: "/users", label: "权限配置" },
    { path: "/audit", label: "审计日志" },
    { path: "/monitoring", label: "监控大盘" },
    { path: "/alerts", label: "告警管理" },
    { path: "/config", label: "系统配置" },
  ];

  const triggerPanic = () => {
    if (panicSent) return;
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      const j = raw ? JSON.parse(raw) : {};
      const token = j.token || "";
      fetch("/api/admin/panic", { method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" } })
        .then(() => setPanicSent(true))
        .catch(() => {});
    } catch { /* noop */ }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gridTemplateRows: "56px 1fr", gridTemplateAreas: '"header header" "sidebar main"', minHeight: "100vh" }}>
      <header style={{ gridArea: "header", display: "flex", alignItems: "center", padding: "0 16px", background: "var(--color-surface)", borderBottom: "1px solid var(--color-border)" }}>
        <Link to="/" style={{ fontWeight: 700, textDecoration: "none", color: "var(--color-text)" }}>SuperPaaS 管理端</Link>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14 }}>{user?.username} ({user?.role})</span>
          <button type="button" onClick={triggerPanic} disabled={panicSent} title="01 4.3 一键求救：踢出会话、冻结、锁屏、告警" style={{ fontSize: 12, padding: "4px 8px", background: panicSent ? "#94a3b8" : "#dc2626", color: "#fff", border: "none", borderRadius: 6 }} aria-label="一键求救">{panicSent ? "已发送" : "一键求救"}</button>
          <button type="button" onClick={() => { logout(); navigate("/login", { replace: true }); }} aria-label="退出登录">退出</button>
        </div>
      </header>
      <aside style={{ gridArea: "sidebar", padding: 16, borderRight: "1px solid var(--color-border)", background: "var(--color-surface)" }}>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {nav.map(({ path, label }) => (
            <Link
            key={path}
            to={path}
            style={{
              padding: 10,
              borderRadius: 8,
              textDecoration: "none",
              color: path === "/" ? (location.pathname === "/" ? "var(--color-primary)" : "var(--color-text)") : (location.pathname.startsWith(path) ? "var(--color-primary)" : "var(--color-text)"),
            }}
          >
            {label}
          </Link>
          ))}
        </nav>
      </aside>
      <main style={{ gridArea: "main", padding: 24 }}><Outlet /></main>
    </div>
  );
}
