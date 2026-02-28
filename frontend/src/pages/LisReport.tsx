/**
 * 批次3 LIS 检验报告界面：报告列表、按样本筛选、报告详情（审核/发布状态）
 * 经网关 /api/v1/lis/reports
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCellList } from "@/api/gateway";
import { getCellById } from "@/config/cells";
import styles from "./CellList.module.css";

const STATUS_MAP: Record<number, string> = {
  0: "待审核",
  1: "已审核",
  2: "已发布",
};

export function LisReport() {
  const navigate = useNavigate();
  const cell = getCellById("lis");
  const [list, setList] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sampleId, setSampleId] = useState("");

  useEffect(() => {
    if (!cell) return;
    setLoading(true);
    const params: Record<string, string | number> = { page: 1, pageSize: 50 };
    if (sampleId.trim()) params.sampleId = sampleId.trim();
    fetchCellList("lis", "/reports", params)
      .then((res) => {
        if (!res.ok) {
          setError(res.error || "请求失败");
          setList([]);
          return;
        }
        const data = res.data as { data?: unknown[] };
        setList(Array.isArray(data?.data) ? (data.data as Record<string, unknown>[]) : []);
      })
      .finally(() => setLoading(false));
  }, [sampleId]);

  if (!cell) return <div className={styles.page}><p>未找到模块。</p></div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate("/cell/lis")}>
          ← 返回 LIS
        </button>
        <h1 className={styles.title}>检验报告</h1>
        <p className={styles.desc}>报告列表与审核状态</p>
      </div>
      <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>
        <label>样本ID</label>
        <input
          type="text"
          value={sampleId}
          onChange={(e) => setSampleId(e.target.value)}
          placeholder="筛选样本"
          style={{ padding: 6, width: 180, border: "1px solid var(--color-border)", borderRadius: 4 }}
        />
      </div>
      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
      ) : list.length === 0 ? (
        <div className={styles.empty}>暂无报告</div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>报告ID</th>
                <th>样本ID</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>审核时间</th>
              </tr>
            </thead>
            <tbody>
              {list.map((row, i) => {
                const r = row as Record<string, unknown>;
                const status = typeof r.status === "number" ? STATUS_MAP[r.status] ?? r.status : r.status;
                return (
                  <tr key={String(r.reportId ?? i)}>
                    <td>{String(r.reportId ?? "—")}</td>
                    <td>{String(r.sampleId ?? "—")}</td>
                    <td>{String(status)}</td>
                    <td>{String(r.createdAt ?? "—")}</td>
                    <td>{String(r.reviewedAt ?? "—")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
