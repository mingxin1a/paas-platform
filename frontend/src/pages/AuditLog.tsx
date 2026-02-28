/**
 * 透明化审计（01 4.1）：谁在什么时候访问了我的数据。
 * 当前为占位页；生产需对接后端 trace_id 关联的访问日志。
 */
import styles from "./AuditLog.module.css";

export function AuditLog() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>数据访问记录</h1>
      <p className={styles.subtitle}>
        展示与 trace_id 关联的访问日志，满足透明化审计要求。接入后端审计 API 后此处将展示真实记录。
      </p>
      <div className={styles.placeholder}>
        <p>暂无访问记录</p>
        <p className={styles.hint}>请通过网关请求业务接口，审计日志将在此处展示。</p>
      </div>
    </div>
  );
}
