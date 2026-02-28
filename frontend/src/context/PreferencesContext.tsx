/**
 * 用户个性化偏好：持久化到 localStorage，支持首页、菜单排序、主题、快捷入口
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "superpaas_preferences";

export type ThemeMode = "light" | "dark" | "system";

export interface ShortcutItem {
  path: string;
  label: string;
}

export interface UserPreferences {
  /** 自定义首页："/" 或 "/cell/{cellId}" */
  homePage: string;
  /** 侧栏菜单顺序：细胞 id 数组，未列出的按默认顺序排在后面 */
  menuOrder: string[];
  /** 主题：light / dark / system */
  theme: ThemeMode;
  /** 常用功能快捷入口，最多 8 个 */
  shortcuts: ShortcutItem[];
}

const DEFAULT_PREFS: UserPreferences = {
  homePage: "/",
  menuOrder: [],
  theme: "system",
  shortcuts: [],
};

function loadPreferences(): UserPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    return {
      homePage: parsed.homePage ?? DEFAULT_PREFS.homePage,
      menuOrder: Array.isArray(parsed.menuOrder) ? parsed.menuOrder : DEFAULT_PREFS.menuOrder,
      theme: (parsed.theme as ThemeMode) ?? DEFAULT_PREFS.theme,
      shortcuts: Array.isArray(parsed.shortcuts) ? parsed.shortcuts : DEFAULT_PREFS.shortcuts,
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

function savePreferences(prefs: UserPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // ignore
  }
}

type PreferencesContextValue = UserPreferences & {
  setHomePage: (path: string) => void;
  setMenuOrder: (order: string[]) => void;
  setTheme: (theme: ThemeMode) => void;
  setShortcuts: (shortcuts: ShortcutItem[]) => void;
  /** 解析后的实际主题（system 时根据 prefers-color-scheme） */
  resolvedTheme: "light" | "dark";
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<UserPreferences>(loadPreferences);
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    savePreferences(prefs);
  }, [prefs]);

  useEffect(() => {
    if (prefs.theme !== "system") {
      setResolvedTheme(prefs.theme);
      document.documentElement.setAttribute("data-theme", prefs.theme);
      return;
    }
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const next = mq.matches ? "dark" : "light";
      setResolvedTheme(next);
      document.documentElement.setAttribute("data-theme", next);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [prefs.theme]);

  const setHomePage = useCallback((path: string) => {
    setPrefs((p) => ({ ...p, homePage: path }));
  }, []);

  const setMenuOrder = useCallback((order: string[]) => {
    setPrefs((p) => ({ ...p, menuOrder: order }));
  }, []);

  const setTheme = useCallback((theme: ThemeMode) => {
    setPrefs((p) => ({ ...p, theme }));
  }, []);

  const setShortcuts = useCallback((shortcuts: ShortcutItem[]) => {
    setPrefs((p) => ({ ...p, shortcuts: shortcuts.slice(0, 8) }));
  }, []);

  const value: PreferencesContextValue = {
    ...prefs,
    setHomePage,
    setMenuOrder,
    setTheme,
    setShortcuts,
    resolvedTheme,
  };

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferences must be used within PreferencesProvider");
  return ctx;
}
