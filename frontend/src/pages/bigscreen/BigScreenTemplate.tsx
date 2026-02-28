/**
 * 可视化大屏模板：生产车间监控、物流调度、经营决策等场景，全屏展示
 * 权限：仅展示用户有权限的细胞/模块数据
 */
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchAnalyticsKPI } from "@/api/analytics";

type TemplateType = "production" | "logistics" | "decision";

const templates: Record<TemplateType, { title: string; description: string }> = {
  production: { title: "生产车间监控大屏", description: "工单进度、产能、异常告警" },
  logistics: { title: "物流调度大屏", description: "运单在途、车辆、时效" },
  decision: { title: "经营决策大屏", description: "销售、采购、库存、审批、生产核心指标" },
};

export function BigScreenTemplate() {
  const { type } = useParams<{ type: string }>();
  const templateType = (type === "production" || type === "logistics" || type === "decision" ? type : "decision") as TemplateType;
  const [kpi, setKpi] = useState<{ salesAmount?: number; purchaseAmount?: number; productionCompletionRate?: number } | null>(null);

  useEffect(() => {
    fetchAnalyticsKPI({ period: "month" }).then((r) => {
      if (r.ok && r.data) setKpi(r.data);
    });
  }, []);

  const meta = templates[templateType];

  return (
    <div
      className="bigscreen-wrapper"
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        color: "#e2e8f0",
        padding: 24,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{meta.title}</h1>
        <Link to="/analytics" style={{ color: "#94a3b8", fontSize: 14 }}>退出大屏</Link>
      </div>
      <p style={{ color: "#94a3b8", marginBottom: 24 }}>{meta.description}</p>

      {templateType === "decision" && kpi && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 20, marginBottom: 32 }}>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 8 }}>销售额</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{(kpi.salesAmount ?? 0).toLocaleString()}</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>元</div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 8 }}>采购额</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{(kpi.purchaseAmount ?? 0).toLocaleString()}</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>元</div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 8 }}>生产完成率</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{kpi.productionCompletionRate ?? 0}%</div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 8 }}>库存周转率</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>4.2</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>次</div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ fontSize: 14, color: "#94a3b8", marginBottom: 8 }}>审批效率</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>92%</div>
          </div>
        </div>
      )}

      {templateType === "production" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12 }}>
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>工单进度</h3>
            <div style={{ height: 200, display: "flex", alignItems: "flex-end", gap: 12 }}>
              {[88, 65, 42, 90].map((v, i) => (
                <div key={i} style={{ flex: 1, height: v + "%", background: "var(--color-primary)", borderRadius: 4, minHeight: 20 }} title={v + "%"} />
              ))}
            </div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12 }}>
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>产能利用率</h3>
            <div style={{ fontSize: 48, fontWeight: 700, textAlign: "center" }}>78%</div>
          </div>
        </div>
      )}

      {templateType === "logistics" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12 }}>
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>在途运单</h3>
            <div style={{ fontSize: 48, fontWeight: 700 }}>126</div>
          </div>
          <div style={{ padding: 24, background: "rgba(255,255,255,0.08)", borderRadius: 12 }}>
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>今日准时率</h3>
            <div style={{ fontSize: 48, fontWeight: 700 }}>96%</div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 32, fontSize: 12, color: "#64748b" }}>
        数据按当前用户权限展示，仅包含您有权限的细胞与租户数据。
      </div>
    </div>
  );
}
