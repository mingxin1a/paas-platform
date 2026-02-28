/**
 * 报表导出：Excel(CSV)、PDF(打印)，遵循数据权限（仅导出当前可见数据）
 */
interface ExportBarProps {
  onExportExcel: () => void;
  onExportPDF: () => void;
  loading?: boolean;
}

export function ExportBar({ onExportExcel, onExportPDF, loading }: ExportBarProps) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
      <button
        type="button"
        onClick={onExportExcel}
        disabled={loading}
        style={{ padding: "6px 12px", border: "1px solid var(--color-border)", borderRadius: 4, background: "var(--color-surface)", cursor: loading ? "not-allowed" : "pointer" }}
      >
        {loading ? "导出中…" : "导出 Excel"}
      </button>
      <button
        type="button"
        onClick={onExportPDF}
        disabled={loading}
        style={{ padding: "6px 12px", border: "1px solid var(--color-border)", borderRadius: 4, background: "var(--color-surface)", cursor: loading ? "not-allowed" : "pointer" }}
      >
        导出 PDF
      </button>
    </div>
  );
}
