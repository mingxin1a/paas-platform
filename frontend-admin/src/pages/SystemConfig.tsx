/**
 * 管理端 - 系统配置：全局配置项展示与编辑占位，对接 /api/admin/config
 */
import { useState, useEffect } from "react";
import { fetchSystemConfig } from "@/api/admin";

export function SystemConfig() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSystemConfig()
      .then((r) => {
        if (r.ok && r.data) setData(r.data);
        else setError(r.error ?? "加载失败");
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>系统配置</h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: 16 }}>
        平台全局配置（网关、治理中心、监控等），对接 <code>/api/admin/config</code>。
      </p>
      {error && <p style={{ color: "var(--color-error)" }}>{error}</p>}
      {loading ? (
        <p>加载中…</p>
      ) : data && Object.keys(data).length > 0 ? (
        <pre style={{ padding: 16, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, overflow: "auto" }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <p style={{ opacity: 0.8 }}>暂无配置数据（或接口未实现）。</p>
      )}
    </div>
  );
}
