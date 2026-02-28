/**
 * 批次2 扫码操作：WMS 扫码入库/出库
 * 经网关调用 POST /api/v1/wms/scan/inbound | /scan/outbound
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { scanInbound, scanOutbound } from "@/api/gateway";
import styles from "./CellList.module.css";

export function ScanOperate() {
  const { cellId } = useParams<{ cellId: string }>();
  const navigate = useNavigate();
  const [orderId, setOrderId] = useState("");
  const [barcode, setBarcode] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [type, setType] = useState<"inbound" | "outbound">("inbound");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderId.trim() || !barcode.trim()) {
      setMessage({ type: "err", text: "请输入入库单/出库单号和条码" });
      return;
    }
    if (cellId !== "wms") {
      setMessage({ type: "err", text: "扫码功能仅支持 WMS 细胞" });
      return;
    }
    setLoading(true);
    setMessage(null);
    const body = { orderId: orderId.trim(), barcode: barcode.trim(), quantity };
    const fn = type === "inbound" ? scanInbound : scanOutbound;
    fn(cellId, body)
      .then((res) => {
        if (res.ok && res.data?.accepted) {
          setMessage({ type: "ok", text: type === "inbound" ? `入库成功，数量 ${quantity}` : `出库成功，数量 ${quantity}` });
          setBarcode("");
        } else {
          setMessage({ type: "err", text: res.error || (res.data as { message?: string })?.message || "操作失败" });
        }
      })
      .catch(() => setMessage({ type: "err", text: "网络错误" }))
      .finally(() => setLoading(false));
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(-1)}>← 返回</button>
        <h1 className={styles.title}>扫码操作</h1>
        <p className={styles.desc}>WMS 扫码入库 / 出库</p>
      </div>
      <form onSubmit={handleSubmit} style={{ maxWidth: 400, marginTop: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <label>类型</label>
          <select value={type} onChange={(e) => setType(e.target.value as "inbound" | "outbound")} style={{ marginLeft: 8 }}>
            <option value="inbound">扫码入库</option>
            <option value="outbound">扫码出库</option>
          </select>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>单号</label>
          <input type="text" value={orderId} onChange={(e) => setOrderId(e.target.value)} placeholder={type === "inbound" ? "入库单ID" : "出库单ID"} style={{ marginLeft: 8, width: 220 }} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>条码</label>
          <input type="text" value={barcode} onChange={(e) => setBarcode(e.target.value)} placeholder="SKU/批次条码" style={{ marginLeft: 8, width: 220 }} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>数量</label>
          <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value) || 1)} style={{ marginLeft: 8, width: 80 }} />
        </div>
        {message && <div style={{ color: message.type === "ok" ? "green" : "red", marginBottom: 8 }}>{message.text}</div>}
        <button type="submit" disabled={loading}>{loading ? "提交中…" : "提交"}</button>
      </form>
    </div>
  );
}
