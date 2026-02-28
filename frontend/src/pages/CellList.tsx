/**
 * 细胞列表页：支持缓存、快捷搜索、高级筛选、列自定义、批量选择、导出/打印、Toast 反馈
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCellList, getGatewayHeaders } from "@/api/gateway";
import { getCellById, getFieldLabel } from "@/config/cells";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { getListCache, setListCache, buildListCacheKey } from "@/hooks/useListCache";
import styles from "./CellList.module.css";

const PAGE_SIZE = 20;
const LIST_CACHE_TTL = 60 * 1000;
const COLUMNS_STORAGE_PREFIX = "superpaas_columns_";

function loadVisibleColumns(cellId: string, defaultKeys: string[]): string[] {
  try {
    const raw = localStorage.getItem(COLUMNS_STORAGE_PREFIX + cellId);
    if (!raw) return defaultKeys;
    const parsed = JSON.parse(raw) as string[];
    return Array.isArray(parsed) ? defaultKeys.filter((k) => parsed.includes(k)).length ? parsed.filter((k) => defaultKeys.includes(k)) : defaultKeys : defaultKeys;
  } catch {
    return defaultKeys;
  }
}

function saveVisibleColumns(cellId: string, keys: string[]) {
  try {
    localStorage.setItem(COLUMNS_STORAGE_PREFIX + cellId, JSON.stringify(keys));
  } catch {
    // ignore
  }
}

export function CellList() {
  const { cellId } = useParams<{ cellId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();
  const cell = cellId ? getCellById(cellId) : null;
  const allowed = !user || user.role === "admin" || (cellId && user.allowedCells.includes(cellId));
  const [list, setList] = useState<unknown[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterKey, setFilterKey] = useState<string>("");
  const [filterValue, setFilterValue] = useState("");
  const [columnPickerOpen, setColumnPickerOpen] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const idKey = cell?.idKey ?? "";

  useEffect(() => {
    if (!cell) return;
    const cacheKey = buildListCacheKey(cell.id, cell.path, { page, pageSize: PAGE_SIZE });
    const cached = getListCache(cacheKey, LIST_CACHE_TTL);
    if (cached) {
      setList(cached.data);
      setTotal(cached.total);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetchCellList(cell.id, cell.path, { page, pageSize: PAGE_SIZE }).then((res) => {
      if (!res.ok) {
        setError(res.error || "请求失败");
        setList([]);
        setTotal(0);
        return;
      }
      const data = res.data as Record<string, unknown> | undefined;
      const arr = (data && (data[cell.listKey || "data"] as unknown[])) || [];
      const result = Array.isArray(arr) ? arr : [];
      setList(result);
      setTotal((data && (data.total as number)) ?? result.length);
      setListCache(cacheKey, result, (data && (data.total as number)) ?? result.length);
    }).finally(() => setLoading(false));
  }, [cell, page]);

  useEffect(() => {
    if (!list.length) {
      setVisibleColumns([]);
      return;
    }
    const first = list[0] as Record<string, unknown>;
    const keys = Object.keys(first);
    setVisibleColumns((prev) => (prev.length ? prev : loadVisibleColumns(cell?.id ?? "", keys)));
  }, [cell?.id, list]);

  const handleExport = useCallback(() => {
    if (!cell?.exportPath) return;
    setExporting(true);
    const url = `/api/v1/${cell.id}${cell.exportPath}?format=csv`;
    fetch(url, { headers: getGatewayHeaders() })
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${cell.id}_export.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast.success("导出成功");
      })
      .catch(() => toast.error("导出失败，请重试"))
      .finally(() => setExporting(false));
  }, [cell, toast]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const toggleColumn = useCallback(
    (key: string) => {
      setVisibleColumns((prev) => {
        const next = prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key];
        if (cell?.id) saveVisibleColumns(cell.id, next);
        return next;
      });
    },
    [cell?.id]
  );

  const toggleSelectAll = useCallback(() => {
    if (!idKey) return;
    setSelectedIds((prev) => {
      if (prev.size === list.length) return new Set();
      return new Set(list.map((row, i) => String((row as Record<string, unknown>)[idKey] ?? i)));
    });
  }, [list, idKey]);

  const toggleSelectOne = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const first = list[0] as Record<string, unknown> | undefined;
  const allKeys = first ? Object.keys(first) : [];
  const filteredList = useMemo((): Record<string, unknown>[] => {
    let out: Record<string, unknown>[] = list as Record<string, unknown>[];
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      out = out.filter((row) => Object.values(row).some((v) => String(v ?? "").toLowerCase().includes(term)));
    }
    if (filterKey && filterValue.trim()) {
      const val = filterValue.trim().toLowerCase();
      out = out.filter((row) => String(row[filterKey] ?? "").toLowerCase().includes(val));
    }
    return out;
  }, [list, searchTerm, filterKey, filterValue]);

  const displayKeys = visibleColumns.length ? allKeys.filter((k) => visibleColumns.includes(k)) : allKeys;

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

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(-1)} aria-label="返回">
          ← 返回
        </button>
        <h1 className={styles.title}>{cell.name}</h1>
        {cell.description && <p className={styles.desc}>{cell.description}</p>}
        <p className={styles.subtitle}>共 {total} 条</p>
        {cell.createFields && cell.createFields.length > 0 && (
          <button type="button" className={styles.exportBtn} onClick={() => navigate(`/cell/${cell.id}/new`)}>
            新建
          </button>
        )}
        {["mes", "wms", "tms"].includes(cell.id) && (
          <button type="button" className={styles.exportBtn} style={{ marginLeft: 8 }} onClick={() => navigate(`/cell/${cell.id}/board`)}>
            看板
          </button>
        )}
        {cell.id === "wms" && (
          <button type="button" className={styles.exportBtn} style={{ marginLeft: 8 }} onClick={() => navigate(`/cell/${cell.id}/scan`)}>
            扫码
          </button>
        )}
        {cell.id === "tms" && (
          <button type="button" className={styles.exportBtn} style={{ marginLeft: 8 }} onClick={() => navigate(`/cell/${cell.id}/tracks`)}>
            轨迹
          </button>
        )}
        {cell.id === "his" && (
          <button type="button" className={styles.exportBtn} style={{ marginLeft: 8 }} onClick={() => navigate("/cell/his/visits")}>
            就诊管理
          </button>
        )}
        {cell.id === "lis" && (
          <button type="button" className={styles.exportBtn} style={{ marginLeft: 8 }} onClick={() => navigate("/cell/lis/reports")}>
            检验报告
          </button>
        )}
        {cell.exportPath && (
          <button type="button" className={styles.exportBtn} onClick={handleExport} disabled={exporting}>
            {exporting ? "导出中…" : "导出 CSV"}
          </button>
        )}
        <button type="button" className={styles.exportBtn} onClick={handlePrint}>
          打印
        </button>
        <div className={styles.columnPickerWrap}>
          <button
            type="button"
            className={styles.exportBtn}
            onClick={() => setColumnPickerOpen((o) => !o)}
            aria-expanded={columnPickerOpen}
            aria-haspopup="true"
          >
            列设置
          </button>
          {columnPickerOpen && (
            <div className={styles.columnPickerDropdown} role="menu">
              {allKeys.map((k) => (
                <label key={k} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px" }}>
                  <input
                    type="checkbox"
                    checked={visibleColumns.includes(k)}
                    onChange={() => toggleColumn(k)}
                  />
                  {getFieldLabel(cell, k)}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className={styles.toolbar}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="快捷搜索当前页…"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          aria-label="快捷搜索"
        />
        {allKeys.length > 0 && (
          <>
            <select
              className={styles.filterSelect}
              value={filterKey}
              onChange={(e) => setFilterKey(e.target.value)}
              aria-label="筛选字段"
            >
              <option value="">筛选字段</option>
              {allKeys.map((k) => (
                <option key={k} value={k}>
                  {getFieldLabel(cell, k)}
                </option>
              ))}
            </select>
            <input
              type="text"
              className={styles.filterInput}
              placeholder="筛选值"
              value={filterValue}
              onChange={(e) => setFilterValue(e.target.value)}
              aria-label="筛选值"
            />
          </>
        )}
      </div>

      {selectedIds.size > 0 && (
        <div className={styles.batchBar} role="status">
          <span>已选 {selectedIds.size} 条</span>
          <button type="button" className={styles.exportBtn} onClick={() => setSelectedIds(new Set())}>
            取消选择
          </button>
        </div>
      )}

      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}
      {loading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>加载中…</span>
        </div>
      ) : filteredList.length === 0 ? (
        <div className={styles.empty}>
          {list.length === 0 ? "暂无数据" : "当前筛选无结果"}
        </div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                {idKey && (
                  <th scope="col">
                    <input
                      type="checkbox"
                      aria-label="全选"
                      checked={selectedIds.size === filteredList.length && filteredList.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                )}
                {displayKeys.map((k) => (
                  <th key={k} scope="col">{getFieldLabel(cell, k)}</th>
                ))}
                {idKey && <th scope="col">操作</th>}
              </tr>
            </thead>
            <tbody>
              {filteredList.map((row, i) => {
                const r = row as Record<string, unknown>;
                const id = idKey ? String(r[idKey] ?? i) : String(i);
                return (
                  <tr key={id}>
                    {idKey && (
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`选择 ${id}`}
                          checked={selectedIds.has(id)}
                          onChange={() => toggleSelectOne(id)}
                        />
                      </td>
                    )}
                    {displayKeys.map((k) => (
                      <td key={k}>{String(r[k] ?? "—")}</td>
                    ))}
                    {idKey && (
                      <td>
                        <button
                          type="button"
                          className={styles.linkBtn}
                          onClick={() => navigate(`/cell/${cell.id}/detail/${encodeURIComponent(id)}`)}
                        >
                          详情
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {total > PAGE_SIZE && (
        <div className={styles.pagination}>
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            上一页
          </button>
          <span>第 {page} 页，共 {total} 条</span>
          <button type="button" disabled={page * PAGE_SIZE >= total} onClick={() => setPage((p) => p + 1)}>
            下一页
          </button>
        </div>
      )}

      <style>{`@media print { .skip-link, header, aside, .back, .exportBtn, .pagination, .toolbar, .batchBar, .columnPickerWrap { display: none !important; } }`}</style>
    </div>
  );
}
