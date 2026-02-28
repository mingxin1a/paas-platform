/**
 * 饼图/环形图示意：用图例+百分比展示，无需 canvas
 */
export interface PieItem {
  name: string;
  value: number;
}

interface SimplePieLegendProps {
  data: PieItem[];
  colors?: string[];
}

const DEFAULT_COLORS = [
  "var(--color-primary)",
  "var(--color-success)",
  "var(--color-warning)",
  "var(--color-info)",
  "var(--color-text-muted)",
];

export function SimplePieLegend({ data, colors = DEFAULT_COLORS }: SimplePieLegendProps) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }} aria-label="饼图图例">
      {data.map((d, i) => (
        <div key={d.name + i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 2,
              background: colors[i % colors.length],
            }}
          />
          <span style={{ fontSize: 14 }}>{d.name}</span>
          <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
            {((d.value / total) * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}
