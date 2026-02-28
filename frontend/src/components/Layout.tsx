import { useState, useMemo } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useAllowedCells } from "@/api/cells";
import { usePreferences } from "@/context/PreferencesContext";
import { Watermark } from "./Watermark";
import styles from "./Layout.module.css";

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { cells: rawCells } = useAllowedCells();
  const { menuOrder, setTheme, resolvedTheme, shortcuts } = usePreferences();

  const allowedCells = useMemo(() => {
    if (!menuOrder.length) return rawCells;
    const orderSet = new Set(menuOrder);
    const ordered = menuOrder.filter((id) => rawCells.some((c) => c.id === id)).map((id) => rawCells.find((c) => c.id === id)!);
    const rest = rawCells.filter((c) => !orderSet.has(c.id));
    return [...ordered, ...rest];
  }, [rawCells, menuOrder]);

  const toggleTheme = () => {
    setTheme(resolvedTheme === "light" ? "dark" : "light");
  };

  return (
    <div className={styles.wrapper}>
      <a href="#main-content" className="skip-link">跳到主内容</a>
      <Watermark />
      <header className={styles.header} role="banner">
        <button
          type="button"
          className={styles.menuBtn}
          onClick={() => setSidebarOpen((o) => !o)}
          aria-label="切换导航"
        >
          <span className={styles.menuIcon} />
        </button>
        <Link to="/" className={styles.logo}>
          SuperPaaS 控制台
        </Link>
        <div className={styles.headerRight}>
          {shortcuts.length > 0 && (
            <div className={styles.shortcutsWrap}>
              <button
                type="button"
                className={styles.themeBtn}
                onClick={() => setShortcutsOpen((o) => !o)}
                aria-expanded={shortcutsOpen}
                aria-haspopup="true"
                aria-label="快捷入口"
              >
                快捷
              </button>
              {shortcutsOpen && (
                <div className={styles.shortcutsDropdown} role="menu">
                  {shortcuts.map((s) => (
                    <button
                      key={s.path}
                      type="button"
                      role="menuitem"
                      onClick={() => { navigate(s.path); setShortcutsOpen(false); }}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <span className={styles.userName} aria-hidden="true">{user?.username}</span>
          <Link to="/settings" className={styles.navLink}>个人设置</Link>
          <Link to="/audit" className={styles.navLink}>数据访问记录</Link>
          <button type="button" className={styles.themeBtn} onClick={toggleTheme} aria-label="切换主题（当前：深色/浅色）">
            {resolvedTheme === "light" ? "🌙" : "☀️"}
          </button>
          <button type="button" className={styles.logoutBtn} onClick={() => { logout(); navigate("/login", { replace: true }); }}>退出</button>
        </div>
      </header>
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ""}`} aria-label="主导航">
        <nav className={styles.nav}>
          <Link to="/" className={location.pathname === "/" ? styles.navItemActive : styles.navItem} onClick={() => setSidebarOpen(false)}>
            概览
          </Link>
          <Link to="/analytics" className={location.pathname.startsWith("/analytics") || location.pathname.startsWith("/reports") || location.pathname.startsWith("/bigscreen") ? styles.navItemActive : styles.navItem} onClick={() => setSidebarOpen(false)}>
            经营分析
          </Link>
          {allowedCells.map((c) => (
            <Link
              key={c.id}
              to={`/cell/${c.id}`}
              className={location.pathname.startsWith(`/cell/${c.id}`) ? styles.navItemActive : styles.navItem}
              onClick={() => setSidebarOpen(false)}
            >
              {c.name}
            </Link>
          ))}
        </nav>
      </aside>
      {sidebarOpen && (
        <div className={styles.overlay} onClick={() => setSidebarOpen(false)} aria-hidden />
      )}
      <main id="main-content" className={styles.main} role="main" tabIndex={-1}><Outlet /></main>
    </div>
  );
}
