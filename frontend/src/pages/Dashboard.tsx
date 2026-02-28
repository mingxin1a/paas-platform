import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { fetchCellHealth } from "@/api/gateway";
import { useAllowedCells } from "@/api/cells";
import styles from "./Dashboard.module.css";

const HINT_DISMISS_KEY = "superpaas_dashboard_hint_dismissed";

interface CellStatus {
  id: string;
  name: string;
  description?: string;
  ok: boolean;
  status: number;
  text: string;
}

export function Dashboard() {
  const { cells: allowedCells, loading: cellsLoading, error: cellsError } = useAllowedCells();
  const [cells, setCells] = useState<CellStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [hintDismissed, setHintDismissed] = useState(() => typeof localStorage !== "undefined" && localStorage.getItem(HINT_DISMISS_KEY) === "1");

  useEffect(() => {
    if (allowedCells.length === 0 && !cellsLoading) {
      setCells([]);
      setLoading(false);
      return;
    }
    if (allowedCells.length === 0) {
      setLoading(cellsLoading);
      return;
    }
    setLoading(true);
    Promise.all(
      allowedCells.map(async (c) => {
        const res = await fetchCellHealth(c.id);
        return {
          id: c.id,
          name: c.name,
          description: c.description,
          ok: res.ok,
          status: res.status,
          text: res.ok ? (res.data?.cell ?? "OK") : (res.error || `${res.status}`),
        };
      })
    )
      .then(setCells)
      .finally(() => setLoading(false));
  }, [allowedCells, cellsLoading]);

  const isLoading = cellsLoading || (allowedCells.length > 0 && loading);

  const dismissHint = () => {
    setHintDismissed(true);
    try { localStorage.setItem(HINT_DISMISS_KEY, "1"); } catch { /* ignore */ }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>概览</h1>
      <p className={styles.subtitle}>各细胞模块运行状态，仅展示您有权限访问的业务模块。</p>
      {!hintDismissed && (
        <div role="region" aria-label="操作指引" style={{ marginBottom: 16, padding: 12, background: "var(--color-primary-muted)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span>您可在 <Link to="/settings">个人设置</Link> 中自定义首页、主题与快捷入口。</span>
          <button type="button" onClick={dismissHint} aria-label="关闭指引" style={{ padding: "4px 8px", border: "none", background: "transparent", cursor: "pointer" }}>×</button>
        </div>
      )}
      {cellsError && <div className={styles.error} role="alert">{cellsError}</div>}
      {isLoading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>检测中…</span>
        </div>
      ) : (
        <div className={styles.grid}>
          {cells.map((c) => (
            <Link key={c.id} to={`/cell/${c.id}`} className={styles.card}>
              <span className={styles.cardName}>{c.name}</span>
              {c.description && <span className={styles.cardDesc}>{c.description}</span>}
              <span className={c.ok ? styles.badgeOk : styles.badgeFail}>
                {c.ok ? "正常" : "异常"}
              </span>
              {!c.ok && <span className={styles.cardHint}>{c.text}</span>}
            </Link>
          ))}
          {!isLoading && allowedCells.length === 0 && !cellsError && (
            <p className={styles.empty}>暂无已授权的业务模块。</p>
          )}
        </div>
      )}
    </div>
  );
}
