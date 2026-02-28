/**
 * 批次3 HIS 就诊界面：就诊列表、新建就诊，适配医疗场景
 * 经网关 /api/v1/his/visits
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCellList, fetchCellPost } from "@/api/gateway";
import { getCellById } from "@/config/cells";
import styles from "./CellList.module.css";

export function HisVisit() {
  const navigate = useNavigate();
  const cell = getCellById("his");
  const [list, setList] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [patientId, setPatientId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!cell) return;
    setLoading(true);
    fetchCellList("his", "/visits", { page: 1, pageSize: 50 })
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
  }, []);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId.trim()) {
      setCreateError("请填写患者ID");
      return;
    }
    setCreateLoading(true);
    setCreateError(null);
    fetchCellPost("his", "/visits", { patientId: patientId.trim(), departmentId: departmentId.trim() })
      .then((res) => {
        if (res.ok) {
          setPatientId("");
          setDepartmentId("");
          setList((prev) => (res.data ? [res.data as Record<string, unknown>, ...prev] : prev));
          return;
        }
        setCreateError(res.error || "创建失败");
      })
      .finally(() => setCreateLoading(false));
  };

  if (!cell) return <div className={styles.page}><p>未找到模块。</p></div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate("/cell/his")}>
          ← 返回 HIS
        </button>
        <h1 className={styles.title}>就诊管理</h1>
        <p className={styles.desc}>患者就诊登记与列表</p>
      </div>
      <form onSubmit={handleCreate} style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16, alignItems: "flex-end" }}>
        <div>
          <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>患者ID *</label>
          <input
            type="text"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="患者ID"
            style={{ padding: 6, width: 140, border: "1px solid var(--color-border)", borderRadius: 4 }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>科室</label>
          <input
            type="text"
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
            placeholder="科室ID"
            style={{ padding: 6, width: 120, border: "1px solid var(--color-border)", borderRadius: 4 }}
          />
        </div>
        <button type="submit" disabled={createLoading} className={styles.exportBtn}>
          {createLoading ? "提交中…" : "新建就诊"}
        </button>
      </form>
      {createError && <div className={styles.error}>{createError}</div>}
      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className={styles.loading}><div className={styles.spinner} /><span>加载中…</span></div>
      ) : list.length === 0 ? (
        <div className={styles.empty}>暂无就诊记录</div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>就诊ID</th>
                <th>患者ID</th>
                <th>科室</th>
                <th>状态</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {list.map((row, i) => (
                <tr key={String((row as Record<string, unknown>).visitId ?? i)}>
                  <td>{String((row as Record<string, unknown>).visitId ?? "—")}</td>
                  <td>{String((row as Record<string, unknown>).patientId ?? "—")}</td>
                  <td>{String((row as Record<string, unknown>).departmentId ?? "—")}</td>
                  <td>{String((row as Record<string, unknown>).status ?? "—")}</td>
                  <td>{String((row as Record<string, unknown>).createdAt ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
