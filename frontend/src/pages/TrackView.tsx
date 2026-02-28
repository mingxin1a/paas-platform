/**
 * 批次2 轨迹可视化：TMS 运单轨迹列表（时间轴展示）
 * 经网关 GET /api/v1/tms/tracks?shipmentId=xxx
 */
import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { fetchTracks } from "@/api/gateway";
import styles from "./CellList.module.css";

export function TrackView() {
  const { cellId } = useParams<{ cellId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [shipmentId, setShipmentId] = useState(searchParams.get("shipmentId") || "");
  const [list, setList] = useState<Array<{ trackId?: string; nodeName?: string; lat?: string; lng?: string; occurredAt?: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = (sid: string) => {
    if (!sid.trim() || cellId !== "tms") return;
    setLoading(true);
    setError(null);
    fetchTracks(cellId!, sid.trim())
      .then((res) => {
        if (res.ok && res.data?.data) setList(Array.isArray(res.data.data) ? res.data.data : []);
        else setError(res.error || "加载失败");
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const sid = searchParams.get("shipmentId");
    if (sid) {
      setShipmentId(sid);
      load(sid);
    }
  }, [cellId, searchParams]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(-1)}>← 返回</button>
        <h1 className={styles.title}>运单轨迹</h1>
        <p className={styles.desc}>TMS 运单在途节点与时间</p>
      </div>
      <div style={{ maxWidth: 500, marginTop: 16 }}>
        <input
          type="text"
          value={shipmentId}
          onChange={(e) => setShipmentId(e.target.value)}
          placeholder="输入运单 ID"
          style={{ marginRight: 8, width: 240 }}
        />
        <button type="button" onClick={() => load(shipmentId)} disabled={loading}>查询</button>
      </div>
      {error && <div className={styles.error} style={{ marginTop: 12 }}>{error}</div>}
      {loading && <div className={styles.loading}><span>加载中…</span></div>}
      {!loading && list.length > 0 && (
        <>
          <div style={{ marginTop: 16, padding: 16, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8 }}>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8 }}>轨迹地图（可接入高德/百度地图 API 展示在途点位）</div>
            <div style={{ height: 200, background: "var(--color-bg)", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-muted)" }}>
              地图占位 · 坐标数: {list.filter((t) => t.lat || t.lng).length}
            </div>
          </div>
          <div style={{ marginTop: 24, maxWidth: 560 }}>
            <div style={{ borderLeft: "2px solid var(--color-primary)", paddingLeft: 16 }}>
              {list.map((t, i) => (
                <div key={t.trackId || i} style={{ marginBottom: 16, position: "relative" }}>
                  <span style={{ position: "absolute", left: -24, width: 10, height: 10, borderRadius: "50%", background: "var(--color-primary)", top: 4 }} />
                  <div style={{ fontWeight: 600 }}>{t.nodeName || "节点"}</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{t.occurredAt || "—"}</div>
                  {(t.lat || t.lng) && <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>坐标: {t.lat}, {t.lng}</div>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
      {!loading && !error && shipmentId && list.length === 0 && <div className={styles.empty} style={{ marginTop: 24 }}>暂无轨迹记录</div>}
    </div>
  );
}
