import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import styles from "./Login.module.css";

export function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await login(username, password);
    setLoading(false);
    if (result.ok) navigate("/", { replace: true });
    else setError(result.error || "登录失败");
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>SuperPaaS 客户端</h1>
        <p className={styles.subtitle}>使用各细胞业务，请先登录。</p>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.label}>
            用户名
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className={styles.input} autoComplete="username" required />
          </label>
          <label className={styles.label}>
            密码
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={styles.input} autoComplete="current-password" required />
          </label>
          {error && <div className={styles.error}>{error}</div>}
          <button type="submit" className={styles.btn} disabled={loading}>{loading ? "登录中…" : "登录"}</button>
        </form>
        <p className={styles.hint}>演示：client / 123 或 operator / 123</p>
      </div>
    </div>
  );
}
