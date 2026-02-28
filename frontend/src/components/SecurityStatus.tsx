/**
 * 00 修正案 #14 / 01 4.1 安全态势可视化
 * 在登录、支付、敏感操作时展示「当前会话安全」与传输保护提示（国密盾动画占位）
 */
import { useState, useEffect } from "react";
import styles from "./SecurityStatus.module.css";

export function SecurityStatus() {
  const [visible, setVisible] = useState(false);
  const [secure, setSecure] = useState(true);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("superpaas_auth") : null;
    setVisible(!!token);
    setSecure(!!(typeof window !== "undefined" && window.location?.protocol === "https:"));
  }, []);

  if (!visible) return null;

  return (
    <section
      className={styles.wrapper}
      aria-label="安全态势"
      role="region"
    >
      <div className={styles.badge}>
        <span className={styles.icon} aria-hidden>
          {secure ? "🛡️" : "⚠️"}
        </span>
        <span className={styles.text}>
          {secure ? "当前会话安全 · 数据传输受保护" : "建议使用 HTTPS 以保护数据传输"}
        </span>
      </div>
      <div className={styles.animation} aria-hidden>
        <span className={styles.shield}>国密盾</span>
        <span className={styles.dot}>·</span>
      </div>
    </section>
  );
}
