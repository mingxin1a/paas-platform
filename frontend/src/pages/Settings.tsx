/**
 * 个人设置：自定义首页、菜单排序、主题、快捷入口
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePreferences } from "@/context/PreferencesContext";
import { useAllowedCells } from "@/api/cells";
import styles from "./CellList.module.css";

export function Settings() {
  const navigate = useNavigate();
  const { homePage, setHomePage, theme, setTheme, shortcuts, setShortcuts } = usePreferences();
  const { cells } = useAllowedCells();
  const [newShortcutPath, setNewShortcutPath] = useState("");
  const [newShortcutLabel, setNewShortcutLabel] = useState("");

  const homeOptions = [
    { value: "/", label: "概览" },
    ...cells.map((c) => ({ value: `/cell/${c.id}`, label: c.name })),
  ];

  const addShortcut = () => {
    if (!newShortcutPath.trim() || !newShortcutLabel.trim()) return;
    if (shortcuts.length >= 8) return;
    setShortcuts([...shortcuts, { path: newShortcutPath.trim(), label: newShortcutLabel.trim() }]);
    setNewShortcutPath("");
    setNewShortcutLabel("");
  };

  const removeShortcut = (path: string) => {
    setShortcuts(shortcuts.filter((s) => s.path !== path));
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <button type="button" className={styles.back} onClick={() => navigate(-1)}>
          ← 返回
        </button>
        <h1 className={styles.title}>个人设置</h1>
        <p className={styles.desc}>自定义首页、主题与快捷入口</p>
      </div>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>自定义首页</h2>
        <select
          value={homePage}
          onChange={(e) => setHomePage(e.target.value)}
          style={{ padding: 8, minWidth: 200, border: "1px solid var(--color-border)", borderRadius: 4 }}
          aria-label="首页"
        >
          {homeOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>菜单排序</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 8 }}>侧栏模块顺序（留空则使用默认）</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {cells.map((c) => (
            <span key={c.id} style={{ padding: "4px 10px", background: "var(--color-primary-muted)", borderRadius: 4, fontSize: 14 }}>
              {c.name}
            </span>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>主题</h2>
        <div style={{ display: "flex", gap: 12 }}>
          {(["light", "dark", "system"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTheme(t)}
              style={{
                padding: "8px 16px",
                border: "1px solid var(--color-border)",
                borderRadius: 4,
                background: theme === t ? "var(--color-primary-muted)" : "var(--color-surface)",
              }}
            >
              {t === "light" ? "浅色" : t === "dark" ? "深色" : "跟随系统"}
            </button>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>快捷入口（最多 8 个）</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          <input
            type="text"
            placeholder="路径，如 /cell/crm"
            value={newShortcutPath}
            onChange={(e) => setNewShortcutPath(e.target.value)}
            style={{ padding: 6, width: 140, border: "1px solid var(--color-border)", borderRadius: 4 }}
          />
          <input
            type="text"
            placeholder="名称"
            value={newShortcutLabel}
            onChange={(e) => setNewShortcutLabel(e.target.value)}
            style={{ padding: 6, width: 100, border: "1px solid var(--color-border)", borderRadius: 4 }}
          />
          <button type="button" className={styles.exportBtn} onClick={addShortcut} disabled={shortcuts.length >= 8}>
            添加
          </button>
        </div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {shortcuts.map((s) => (
            <li key={s.path} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span>{s.label}</span>
              <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{s.path}</span>
              <button type="button" className={styles.linkBtn} onClick={() => removeShortcut(s.path)}>
                移除
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
