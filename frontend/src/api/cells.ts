/**
 * 细胞列表与权限：从网关获取细胞列表，按用户角色/权限过滤
 * 依据：网关规范、PaaS 认证中心返回的 user.allowedCells
 */
import { useState, useEffect } from "react";
import { fetchGatewayCells } from "./gateway";
import { getCellById, type CellConfig } from "@/config/cells";
import { useAuth } from "@/context/AuthContext";

export type AllowedCell = CellConfig & { enabled?: boolean };

/**
 * 从网关拉取细胞列表，并按当前用户 allowedCells 过滤
 * - admin 或 allowedCells 为空：展示网关返回的全部细胞
 * - 否则仅展示 allowedCells 与网关列表的交集
 */
export async function fetchAllowedCellsFromGateway(
  user: { role: string; allowedCells: string[] } | null
): Promise<AllowedCell[]> {
  const res = await fetchGatewayCells();
  if (!res.ok || !res.data?.data) {
    return [];
  }
  const list = res.data.data;
  let ids: string[] = list.map((c) => c.id).filter(Boolean);
  if (user && user.role !== "admin" && Array.isArray(user.allowedCells) && user.allowedCells.length > 0) {
    const set = new Set(user.allowedCells);
    ids = ids.filter((id) => set.has(id));
  }
  return ids
    .map((id) => {
      const gw = list.find((c) => c.id === id);
      const config = getCellById(id);
      if (!config) return null;
      return {
        ...config,
        name: gw?.name ?? config.name,
        enabled: gw?.enabled ?? true,
      } as AllowedCell;
    })
    .filter((c): c is AllowedCell => c != null);
}

/**
 * 基于用户角色的可访问细胞列表（从网关获取并过滤）
 * 仅展示用户有权限访问的业务模块
 */
export function useAllowedCells(): { cells: AllowedCell[]; loading: boolean; error: string | null } {
  const { user } = useAuth();
  const [cells, setCells] = useState<AllowedCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setCells([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetchAllowedCellsFromGateway(user)
      .then(setCells)
      .catch((e) => {
        setError((e as Error).message);
        setCells([]);
      })
      .finally(() => setLoading(false));
  }, [user?.username, user?.role, user?.allowedCells?.join(",")]);

  return { cells, loading, error };
}
