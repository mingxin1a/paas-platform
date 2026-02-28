import { useState, useEffect, useCallback } from "react";
import {
  fetchAdminCells,
  patchCellEnabled,
  fetchGovernanceCells,
  fetchGovernanceHealthCells,
  fetchRoutes,
  fetchVerifyReport,
  triggerCellsVerify,
  getCellDocsUrl,
  fetchAdminUsers,
  patchUserAllowedCells,
  type CellRow,
  type AdminUser,
} from "@/api/admin";

type Tab = "list" | "routes" | "verify" | "permission";

export function CellManage() {
  const [list, setList] = useState<CellRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toggling, setToggling] = useState<string | null>(null);
  const [healthMap, setHealthMap] = useState<Record<string, boolean>>({});
  const [routes, setRoutes] = useState<Record<string, string>>({});
  const [verifyReport, setVerifyReport] = useState<string>("");
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyTriggering, setVerifyTriggering] = useState(false);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [tab, setTab] = useState<Tab>("list");

  const loadCells = useCallback(() => {
    setLoading(true);
    setError("");
    fetchAdminCells()
      .then((r) => {
        if (r.ok) setList(r.data ?? []);
        else setError(r.error ?? "加载失败");
      })
      .finally(() => setLoading(false));
  }, []);

  const loadHealth = useCallback(() => {
    fetchGovernanceHealthCells().then((r) => {
      if (r.ok && r.data) setHealthMap(r.data as Record<string, boolean>);
    });
    fetchGovernanceCells().then((r) => {
      if (r.ok && r.data) {
        const map: Record<string, boolean> = {};
        (r.data as { cell?: string; healthy?: boolean }[]).forEach((c) => {
          if (c.cell != null) map[c.cell] = c.healthy === true;
        });
        setHealthMap((prev) => ({ ...prev, ...map }));
      }
    });
  }, []);

  const loadRoutes = useCallback(() => {
    fetchRoutes().then((r) => {
      if (r.ok && r.routes) setRoutes(r.routes);
    });
  }, []);

  useEffect(() => {
    loadCells();
  }, [loadCells]);

  useEffect(() => {
    if (list.length) {
      loadHealth();
      loadRoutes();
    }
  }, [list.length, loadHealth, loadRoutes]);

  const toggle = (id: string, enabled: boolean) => {
    setToggling(id);
    patchCellEnabled(id, enabled).then((r) => {
      if (r.ok) setList((prev) => prev.map((c) => (c.id === id ? { ...c, enabled } : c)));
    }).finally(() => setToggling(null));
  };

  const loadVerifyReport = useCallback(() => {
    setVerifyLoading(true);
    fetchVerifyReport()
      .then((r) => {
        if (r.ok)
          setVerifyReport(
            [r.message, r.standard, r.reportUrl].filter(Boolean).join("\n") || "无报告内容"
          );
        else setVerifyReport(r.error ?? "获取失败");
      })
      .finally(() => setVerifyLoading(false));
  }, []);

  const triggerVerify = () => {
    setVerifyTriggering(true);
    triggerCellsVerify()
      .then((r) => {
        if (r.ok) {
          setVerifyReport((r.message ?? "已提交") + "\n" + (verifyReport || ""));
          loadVerifyReport();
        } else setVerifyReport(r.error ?? "触发失败");
      })
      .finally(() => setVerifyTriggering(false));
  };

  useEffect(() => {
    if (tab === "permission") {
      fetchAdminUsers().then((r) => {
        if (r.ok) setUsers(r.data ?? []);
      });
    }
  }, [tab]);

  const saveUserCells = (userId: string, allowedCells: string[]) => {
    patchUserAllowedCells(userId, allowedCells).then((r) => {
      if (r.ok) setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, allowedCells: r.data!.allowedCells } : u)));
    });
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "list", label: "列表与启用" },
    { key: "routes", label: "路由配置" },
    { key: "verify", label: "接入校验" },
    { key: "permission", label: "权限配置" },
  ];

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>细胞管理</h1>
      <nav style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: tab === key ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
              background: tab === key ? "var(--color-primary-muted)" : "var(--color-surface)",
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      {error && <div style={{ color: "var(--color-primary)", marginBottom: 12 }}>{error}</div>}

      {tab === "list" && (
        <section>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <span>细胞列表、注册/下线、健康状态、接口文档</span>
            <button type="button" onClick={() => { loadCells(); loadHealth(); }}>刷新</button>
          </div>
          {loading ? (
            <p>加载中...</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <th style={{ textAlign: "left", padding: 10 }}>ID</th>
                    <th style={{ textAlign: "left", padding: 10 }}>名称</th>
                    <th style={{ textAlign: "left", padding: 10 }}>启用</th>
                    <th style={{ textAlign: "left", padding: 10 }}>健康状态</th>
                    <th style={{ textAlign: "left", padding: 10 }}>Base URL</th>
                    <th style={{ textAlign: "left", padding: 10 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((c) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                      <td style={{ padding: 10 }}>{c.id}</td>
                      <td style={{ padding: 10 }}>{c.name}</td>
                      <td style={{ padding: 10 }}>{c.enabled ? "是" : "否"}</td>
                      <td style={{ padding: 10 }}>
                        {healthMap[c.id] === true ? (
                          <span style={{ color: "green" }}>健康</span>
                        ) : healthMap[c.id] === false ? (
                          <span style={{ color: "red" }}>不健康</span>
                        ) : (
                          <span style={{ opacity: 0.7 }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: 10, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }} title={c.baseUrl}>
                        {c.baseUrl}
                      </td>
                      <td style={{ padding: 10 }}>
                        <button
                          type="button"
                          disabled={toggling === c.id}
                          onClick={() => toggle(c.id, !c.enabled)}
                          style={{ marginRight: 8 }}
                        >
                          {c.enabled ? "下线" : "注册/启用"}
                        </button>
                        <a
                          href={getCellDocsUrl(c.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ marginLeft: 4 }}
                        >
                          接口文档
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "routes" && (
        <section>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <span>网关路由配置（细胞 → base_url）</span>
            <button type="button" onClick={loadRoutes}>刷新</button>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <th style={{ textAlign: "left", padding: 10 }}>细胞 ID</th>
                  <th style={{ textAlign: "left", padding: 10 }}>上游地址</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(routes).map(([cellId, url]) => (
                  <tr key={cellId} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: 10 }}>{cellId}</td>
                    <td style={{ padding: 10, wordBreak: "break-all" }}>{url}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {Object.keys(routes).length === 0 && <p style={{ opacity: 0.8 }}>暂无路由数据或治理中心未配置</p>}
        </section>
      )}

      {tab === "verify" && (
        <section>
          <div style={{ marginBottom: 12 }}>
            <button
              type="button"
              disabled={verifyTriggering}
              onClick={triggerVerify}
              style={{ marginRight: 8 }}
            >
              {verifyTriggering ? "提交中…" : "手动触发合规校验"}
            </button>
            <button type="button" disabled={verifyLoading} onClick={loadVerifyReport}>
              {verifyLoading ? "加载中…" : "查看校验报告"}
            </button>
          </div>
          <pre
            style={{
              padding: 16,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              whiteSpace: "pre-wrap",
              minHeight: 120,
            }}
          >
            {verifyReport || "点击「查看校验报告」或「手动触发合规校验」获取内容。"}
          </pre>
        </section>
      )}

      {tab === "permission" && (
        <section>
          <p style={{ marginBottom: 12, opacity: 0.9 }}>用户可访问细胞（allowedCells），对接平台 GET/PATCH /api/admin/users</p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <th style={{ textAlign: "left", padding: 10 }}>用户</th>
                  <th style={{ textAlign: "left", padding: 10 }}>角色</th>
                  <th style={{ textAlign: "left", padding: 10 }}>可访问细胞</th>
                  <th style={{ textAlign: "left", padding: 10 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <UserPermissionRow
                    key={u.id}
                    user={u}
                    cellIds={list.map((c) => c.id)}
                    onSave={(allowedCells) => saveUserCells(u.id, allowedCells)}
                  />
                ))}
              </tbody>
            </table>
          </div>
          {users.length === 0 && <p style={{ opacity: 0.8 }}>暂无用户数据</p>}
        </section>
      )}
    </div>
  );
}

function UserPermissionRow({
  user,
  cellIds,
  onSave,
}: {
  user: AdminUser;
  cellIds: string[];
  onSave: (allowedCells: string[]) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<string[]>(user.allowedCells ?? []);

  const save = () => {
    onSave(selected);
    setEditing(false);
  };

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
      <td style={{ padding: 10 }}>{user.username}</td>
      <td style={{ padding: 10 }}>{user.role}</td>
      <td style={{ padding: 10 }}>
        {editing ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {cellIds.map((id) => (
              <label key={id} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input
                  type="checkbox"
                  checked={selected.includes(id)}
                  onChange={() => toggle(id)}
                />
                {id}
              </label>
            ))}
            <button type="button" onClick={save}>保存</button>
            <button type="button" onClick={() => { setSelected(user.allowedCells ?? []); setEditing(false); }}>取消</button>
          </div>
        ) : (
          <>
            {(user.allowedCells ?? []).join(", ") || "—"}
            <button type="button" onClick={() => setEditing(true)} style={{ marginLeft: 8 }}>编辑</button>
          </>
        )}
      </td>
      <td style={{ padding: 10 }} />
    </tr>
  );
}
