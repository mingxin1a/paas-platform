/**
 * 动态水印（01 4.1）：用户名、时间，防止截屏泄密与责任追溯。
 * 当前为占位实现；生产可接入真实用户与 IP。
 */
import { useEffect, useState } from "react";

export function Watermark() {
  const [label, setLabel] = useState("");

  useEffect(() => {
    const user = typeof window !== "undefined" ? (localStorage.getItem("userName") || "访客") : "访客";
    const t = new Date().toLocaleString("zh-CN", { dateStyle: "short", timeStyle: "short" });
    setLabel(`${user} ${t}`);
    const id = setInterval(() => {
      const t2 = new Date().toLocaleString("zh-CN", { dateStyle: "short", timeStyle: "short" });
      setLabel(`${user} ${t2}`);
    }, 60000);
    return () => clearInterval(id);
  }, []);

  if (!label) return null;

  return (
    <div
      className="watermark-layer"
      aria-hidden
      style={{
        position: "fixed",
        inset: 0,
        pointerEvents: "none",
        zIndex: 9999,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%) rotate(-22deg)",
          whiteSpace: "nowrap",
          fontSize: "14px",
          color: "rgba(0,0,0,0.06)",
          fontFamily: "var(--font-sans)",
          userSelect: "none",
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "120px 200px",
          width: "200%",
          height: "200%",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {Array.from({ length: 20 }, (_, i) => (
          <span key={i}>{label}</span>
        ))}
      </div>
    </div>
  );
}
