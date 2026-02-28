/**
 * 通用新建页：根据 cell 的 createFields 渲染表单，提交至 POST /api/v1/{cellId}{path}
 * 批次1 CRM/ERP/OA/SRM 等业务闭环；表单校验、错误提示、成功后跳转列表
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCellPost } from "@/api/gateway";
import { getCellById, type CreateFieldConfig } from "@/config/cells";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import styles from "./CellList.module.css";

export function CellCreate() {
  const { cellId } = useParams<{ cellId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const cell = cellId ? getCellById(cellId) : null;
  const allowed = !user || user.role === "admin" || (cellId && user.allowedCells.includes(cellId));
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const toast = useToast();

  if (!cell) {
    return (
      <div className={styles.page}>
        <p>未找到该模块。</p>
      </div>
    );
  }
  if (!allowed) {
    return (
      <div className={styles.page}>
        <p>无权限访问该细胞。</p>
        <button type="button" onClick={() => navigate("/")}>
          返回概览
        </button>
      </div>
    );
  }

  const fields: CreateFieldConfig[] = cell.createFields ?? [];
  if (fields.length === 0) {
    return (
      <div className={styles.page}>
        <button type="button" className={styles.back} onClick={() => navigate(`/cell/${cell.id}`)}>
          ← 返回列表
        </button>
        <h1 className={styles.title}>{cell.name} · 新建</h1>
        <p className={styles.desc}>该模块暂未配置新建表单。</p>
      </div>
    );
  }

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    fields.forEach((f) => {
      if (f.required && !(values[f.name] ?? "").trim()) {
        next[f.name] = `请填写${f.label}`;
      }
    });
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    if (!validate()) return;
    setLoading(true);
    const body: Record<string, unknown> = {};
    fields.forEach((f) => {
      const v = values[f.name] ?? "";
      if (f.type === "number") body[f.name] = Number(v) || 0;
      else body[f.name] = v.trim();
    });
    fetchCellPost(cell.id, cell.path, body)
      .then((res) => {
        if (res.ok) {
          toast.success("创建成功");
          navigate(`/cell/${cell.id}`, { replace: true });
          return;
        }
        const msg = res.error || "创建失败";
        setSubmitError(msg);
        toast.error(msg);
      })
      .catch(() => {
        setSubmitError("网络错误");
        toast.error("网络错误");
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(`/cell/${cell.id}`)}>
          ← 返回列表
        </button>
        <h1 className={styles.title}>{cell.name} · 新建</h1>
        <p className={styles.desc}>请填写以下必填项并提交。</p>
      </div>
      <form onSubmit={handleSubmit} style={{ maxWidth: 480, marginTop: 16 }}>
        {fields.map((f) => {
          const id = `field-${f.name}`;
          return (
            <div key={f.name} style={{ marginBottom: 14 }}>
              <label htmlFor={id} style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
                {f.label}
                {f.required && <span style={{ color: "var(--color-error)" }}> *</span>}
              </label>
              {f.type === "textarea" ? (
                <textarea
                  id={id}
                  value={values[f.name] ?? ""}
                  onChange={(e) => setValues((prev) => ({ ...prev, [f.name]: e.target.value }))}
                  placeholder={f.placeholder}
                  rows={3}
                  style={{
                    width: "100%",
                    padding: 8,
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              ) : (
                <input
                  id={id}
                  type={f.type === "number" ? "number" : f.type === "email" ? "email" : "text"}
                  value={values[f.name] ?? ""}
                  onChange={(e) => setValues((prev) => ({ ...prev, [f.name]: e.target.value }))}
                  placeholder={f.placeholder}
                  style={{
                    width: "100%",
                    padding: 8,
                    borderRadius: "var(--radius-sm)",
                    border: errors[f.name] ? "1px solid var(--color-error)" : "1px solid var(--color-border)",
                  }}
                />
              )}
              {errors[f.name] && (
                <span style={{ fontSize: 12, color: "var(--color-error)", marginTop: 4 }}>{errors[f.name]}</span>
              )}
            </div>
          );
        })}
        {submitError && <div className={styles.error}>{submitError}</div>}
        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <button type="submit" disabled={loading} className={styles.exportBtn}>
            {loading ? "提交中…" : "提交"}
          </button>
          <button type="button" className={styles.exportBtn} onClick={() => navigate(`/cell/${cell.id}`)}>
            取消
          </button>
        </div>
      </form>
    </div>
  );
}
