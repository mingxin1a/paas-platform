/**
 * 简单柱状图：纯 CSS 条形，用于报表
 */
export interface BarItem {
  name: string;
  value: number;
}

interface SimpleBarChartProps {
  data: BarItem[];
  max?: number;
  height?: number;
  unit?: string;
}

export function SimpleBarChart({ data, max, height = 200, unit = "" }: SimpleBarChartProps) {
  const m = max ?? Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ height }} aria-label="柱状图">
      {data.map((d, i) => (
        <div key={d.name + i} style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
            <span>{d.name}</span>
            <span>{d.value.toLocaleString()}{unit}</span>
          </div>
          <div
            style={{
              height: 20,
              background: "var(--color-bg)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(d.value / m) * 100}%`,
                height: "100%",
                background: "var(--color-primary)",
                borderRadius: 4,
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
