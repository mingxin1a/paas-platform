/**
 * 报表通用筛选：日期范围、同比环比、维度筛选
 */
interface ReportFiltersProps {
  startDate: string;
  endDate: string;
  compare: "none" | "yoy" | "mom";
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  onCompareChange: (v: "none" | "yoy" | "mom") => void;
}

export function ReportFilters({
  startDate,
  endDate,
  compare,
  onStartDateChange,
  onEndDateChange,
  onCompareChange,
}: ReportFiltersProps) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginBottom: 16 }}>
      <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <span style={{ fontSize: 14 }}>开始</span>
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          aria-label="开始日期"
          style={{ padding: 6, border: "1px solid var(--color-border)", borderRadius: 4 }}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <span style={{ fontSize: 14 }}>结束</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          aria-label="结束日期"
          style={{ padding: 6, border: "1px solid var(--color-border)", borderRadius: 4 }}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <span style={{ fontSize: 14 }}>对比</span>
        <select
          value={compare}
          onChange={(e) => onCompareChange(e.target.value as "none" | "yoy" | "mom")}
          aria-label="同比环比"
          style={{ padding: 6, border: "1px solid var(--color-border)", borderRadius: 4 }}
        >
          <option value="none">无</option>
          <option value="yoy">同比</option>
          <option value="mom">环比</option>
        </select>
      </label>
    </div>
  );
}
