/**
 * KPI 卡片：经营分析大屏与报表页
 */
interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  sub?: string;
  trend?: "up" | "down" | "flat";
  onClick?: () => void;
}

export function KpiCard({ title, value, unit = "", sub, trend, onClick }: KpiCardProps) {
  const displayValue = typeof value === "number" ? value.toLocaleString() : value;
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => e.key === "Enter" && onClick() : undefined}
      style={{
        padding: 16,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 8,
        minWidth: 140,
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{displayValue}{unit ? " " + unit : ""}</div>
      {sub != null && <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>{sub}</div>}
      {trend === "up" && <span style={{ fontSize: 12, color: "var(--color-success)" }}>↑</span>}
      {trend === "down" && <span style={{ fontSize: 12, color: "var(--color-error)" }}>↓</span>}
    </div>
  );
}
