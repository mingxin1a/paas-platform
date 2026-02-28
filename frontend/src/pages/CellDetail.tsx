import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCellDetail } from "@/api/gateway";
import { getCellById, getFieldLabel } from "@/config/cells";
import { useAuth } from "@/context/AuthContext";
import styles from "./CellDetail.module.css";

export function CellDetail() {
  const { cellId, id } = useParams<{ cellId: string; id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const cell = cellId ? getCellById(cellId) : null;
  const allowed = !user || user.role === "admin" || (cellId && user.allowedCells.includes(cellId));
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cell || !id) return;
    setLoading(true);
    setError(null);
    const path = cell.path.replace(/\/$/, "");
    fetchCellDetail(cell.id, path, decodeURIComponent(id)).then((res) => {
      if (!res.ok) {
        setError(res.error || "加载失败");
        setData(null);
        return;
      }
      setData((res.data as Record<string, unknown>) || null);
    }).finally(() => setLoading(false));
  }, [cell, id]);

  if (!cell) return <div className={styles.page}><p>未找到该模块。</p></div>;
  if (!allowed) return <div className={styles.page}><p>无权限访问该细胞。</p><button type="button" onClick={() => navigate("/")}>返回概览</button></div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(`/cell/${cell.id}`)}>
          ← 返回列表
        </button>
        <h1 className={styles.title}>{cell.name} · 详情</h1>
      </div>
      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>加载中…</span>
        </div>
      ) : data ? (
        <div className={styles.card}>
          <dl className={styles.dl}>
            {Object.entries(data).map(([k, v]) => (
              <div key={k} className={styles.row}>
                <dt>{getFieldLabel(cell, k)}</dt>
                <dd>
                  {typeof v === "object" && v !== null && !Array.isArray(v)
                    ? JSON.stringify(v)
                    : Array.isArray(v)
                    ? JSON.stringify(v)
                    : String(v ?? "—")}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : (
        <div className={styles.empty}>无详情数据</div>
      )}
    </div>
  );
}
