/**
 * 全局 Toast 反馈：成功/失败/提示，用于操作结果与异常提示
 */
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
  ts: number;
}

type ToastContextValue = {
  toasts: ToastItem[];
  add: (type: ToastType, message: string, duration?: number) => void;
  remove: (id: string) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION: Record<ToastType, number> = {
  success: 3000,
  error: 5000,
  info: 4000,
  warning: 4000,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const add = useCallback(
    (type: ToastType, message: string, duration?: number) => {
      const id = "toast-" + Date.now() + "-" + Math.random().toString(36).slice(2, 9);
      const d = duration ?? DEFAULT_DURATION[type];
      setToasts((prev) => [...prev, { id, type, message, duration: d, ts: Date.now() }]);
      if (d > 0) setTimeout(() => remove(id), d);
    },
    [remove]
  );

  const value: ToastContextValue = {
    toasts,
    add,
    remove,
    success: (msg: string, d?: number) => add("success", msg, d),
    error: (msg: string, d?: number) => add("error", msg, d),
    info: (msg: string, d?: number) => add("info", msg, d),
    warning: (msg: string, d?: number) => add("warning", msg, d),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={remove} />
    </ToastContext.Provider>
  );
}

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: ToastItem[];
  onRemove: (id: string) => void;
}) {
  return (
    <div
      className="toast-container"
      role="region"
      aria-label="通知消息"
      style={{
        position: "fixed",
        top: "var(--header-height)",
        right: 16,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        maxWidth: 360,
      }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={"toast toast-" + t.type}
          style={{
            padding: "12px 16px",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-md)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <span>{t.message}</span>
          <button
            type="button"
            onClick={() => onRemove(t.id)}
            aria-label="关闭"
            style={{
              border: "none",
              background: "none",
              cursor: "pointer",
              padding: 4,
              fontSize: 18,
              lineHeight: 1,
              color: "var(--color-text-secondary)",
            }}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
