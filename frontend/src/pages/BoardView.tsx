/**
 * 批次2 看板：MES 生产看板（工单按状态分组）/ WMS/TMS 实时概览
 * MES 经网关 GET /api/v1/mes/work-orders 按 status 分组展示；其他细胞 GET /board 或占位
 */
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchBoard, fetchCellList } from "@/api/gateway";
import { getCellById } from "@/config/cells";
import styles from "./CellList.module.css";

const MES_STATUS_LABEL: Record<number, string> = {
  0: "待开工",
  1: "进行中",
  2: "已完成",
};

export function BoardView() {
  const { cellId } = useParams<{ cellId: string }>();
  const navigate = useNavigate();
  const cell = cellId ? getCellById(cellId) : null;
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [mesGroups, setMesGroups] = useState<Record<string, unknown[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cellId || !cell) return;
    setLoading(true);
    setError(null);
    if (cellId === "mes") {
      fetchCellList("mes", "/work-orders", { page: 1, pageSize: 200 })
        .then((res) => {
          if (!res.ok) {
            setError(res.error || "加载失败");
            setMesGroups({});
            return;
          }
          const list = (res.data as { data?: unknown[] })?.data ?? [];
          const arr = Array.isArray(list) ? list : [];
          const byStatus: Record<string, unknown[]> = {};
          arr.forEach((row) => {
            const status = String((row as Record<string, unknown>).status ?? 0);
            if (!byStatus[status]) byStatus[status] = [];
            byStatus[status].push(row);
          });
          setMesGroups(byStatus);
          setData({ total: arr.length });
        })
        .catch(() => setError("网络错误"))
        .finally(() => setLoading(false));
      return;
    }
    fetchBoard(cellId)
      .then((res) => {
        if (res.ok && res.data) setData(res.data as Record<string, unknown>);
        else setError(res.error || "加载失败");
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, [cellId, cell]);

  if (!cell) {
    return <div className={styles.page}><p>未找到该模块。</p></div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(-1)}>← 返回</button>
        <h1 className={styles.title}>{cell.name} 看板</h1>
        <p className={styles.desc}>{cellId === "mes" ? "工单按状态分组" : "实时数据概览"}</p>
      </div>
      {error && <div className={styles.error}>{error}</div>}
      {loading && <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>}
      {!loading && cellId === "mes" && (
        <div style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
          {[0, 1, 2].map((status) => {
            const items = mesGroups[String(status)] ?? [];
            const label = MES_STATUS_LABEL[status] ?? `状态${status}`;
            return (
              <div
                key={status}
                style={{
                  flex: "1 1 280px",
                  minWidth: 280,
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  padding: 12,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 8, color: "var(--color-text-secondary)" }}>
                  {label}（{items.length}）
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {items.slice(0, 10).map((row, i) => {
                    const r = row as Record<string, unknown>;
                    const key = String(r.workOrderId ?? r.orderNo ?? i);
                    return (
                      <div
                        key={key}
                        style={{ padding: 8, background: "var(--color-bg)", borderRadius: 4, fontSize: 13 }}
                      >
                        {String(r.orderNo ?? r.workOrderId ?? "—")} · 数量 {String(r.quantity ?? "—")}
                      </div>
                    );
                  })}
                  {items.length > 10 && <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>…共 {items.length} 条</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {!loading && cellId !== "mes" && data && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 16 }}>
          {Object.entries(data).map(([key, value]) => (
            <div key={key} style={{ background: "var(--color-surface)", padding: 16, borderRadius: 8, minWidth: 160, border: "1px solid var(--color-border)" }}>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{key}</div>
              <div style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>
                {typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "")}
              </div>
            </div>
          ))}
        </div>
      )}
      {!loading && !data && cellId !== "mes" && !error && <div className={styles.empty}>暂无看板数据（该细胞可能未暴露 /board）</div>}
    </div>
  );
}
