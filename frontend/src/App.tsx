import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { PreferencesProvider, usePreferences } from "@/context/PreferencesContext";
import { Layout } from "@/components/Layout";

const Login = lazy(() => import("@/pages/Login").then((m) => ({ default: m.Login })));
const Dashboard = lazy(() => import("@/pages/Dashboard").then((m) => ({ default: m.Dashboard })));
const CellList = lazy(() => import("@/pages/CellList").then((m) => ({ default: m.CellList })));
const CellDetail = lazy(() => import("@/pages/CellDetail").then((m) => ({ default: m.CellDetail })));
const CellCreate = lazy(() => import("@/pages/CellCreate").then((m) => ({ default: m.CellCreate })));
const AuditLog = lazy(() => import("@/pages/AuditLog").then((m) => ({ default: m.AuditLog })));
const ScanOperate = lazy(() => import("@/pages/ScanOperate").then((m) => ({ default: m.ScanOperate })));
const TrackView = lazy(() => import("@/pages/TrackView").then((m) => ({ default: m.TrackView })));
const BoardView = lazy(() => import("@/pages/BoardView").then((m) => ({ default: m.BoardView })));
const HisVisit = lazy(() => import("@/pages/HisVisit").then((m) => ({ default: m.HisVisit })));
const LisReport = lazy(() => import("@/pages/LisReport").then((m) => ({ default: m.LisReport })));
const Settings = lazy(() => import("@/pages/Settings").then((m) => ({ default: m.Settings })));
const AnalyticsDashboard = lazy(() => import("@/pages/AnalyticsDashboard").then((m) => ({ default: m.AnalyticsDashboard })));
const CrmReports = lazy(() => import("@/pages/reports/CrmReports").then((m) => ({ default: m.CrmReports })));
const ErpReports = lazy(() => import("@/pages/reports/ErpReports").then((m) => ({ default: m.ErpReports })));
const MesReports = lazy(() => import("@/pages/reports/MesReports").then((m) => ({ default: m.MesReports })));
const CustomReport = lazy(() => import("@/pages/reports/CustomReport").then((m) => ({ default: m.CustomReport })));
const BigScreenTemplate = lazy(() => import("@/pages/bigscreen/BigScreenTemplate").then((m) => ({ default: m.BigScreenTemplate })));

function PageFallback() {
  return (
    <div
      className="page-loading"
      role="status"
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 280,
        color: "var(--color-text-secondary)",
      }}
    >
      <span className="spinner" style={{ width: 24, height: 24, border: "2px solid var(--color-border)", borderTopColor: "var(--color-primary)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <span style={{ marginLeft: 8 }}>加载中…</span>
    </div>
  );
}

function HomeOrRedirect() {
  const { homePage } = usePreferences();
  if (homePage && homePage !== "/") return <Navigate to={homePage} replace />;
  return <Dashboard />;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, authChecked } = useAuth();
  if (!authChecked && user) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", color: "var(--color-text-secondary)" }} role="status">
        校验登录状态…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <AuthProvider>
      <PreferencesProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<Suspense fallback={<PageFallback />}><Login /></Suspense>} />
            <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
              <Route index element={<Suspense fallback={<PageFallback />}><HomeOrRedirect /></Suspense>} />
              <Route path="cell/:cellId" element={<Suspense fallback={<PageFallback />}><CellList /></Suspense>} />
              <Route path="cell/:cellId/new" element={<Suspense fallback={<PageFallback />}><CellCreate /></Suspense>} />
              <Route path="cell/:cellId/detail/:id" element={<Suspense fallback={<PageFallback />}><CellDetail /></Suspense>} />
              <Route path="cell/:cellId/board" element={<Suspense fallback={<PageFallback />}><BoardView /></Suspense>} />
              <Route path="cell/:cellId/scan" element={<Suspense fallback={<PageFallback />}><ScanOperate /></Suspense>} />
              <Route path="cell/:cellId/tracks" element={<Suspense fallback={<PageFallback />}><TrackView /></Suspense>} />
              <Route path="cell/his/visits" element={<Suspense fallback={<PageFallback />}><HisVisit /></Suspense>} />
              <Route path="cell/lis/reports" element={<Suspense fallback={<PageFallback />}><LisReport /></Suspense>} />
              <Route path="audit" element={<Suspense fallback={<PageFallback />}><AuditLog /></Suspense>} />
              <Route path="settings" element={<Suspense fallback={<PageFallback />}><Settings /></Suspense>} />
              <Route path="analytics" element={<Suspense fallback={<PageFallback />}><AnalyticsDashboard /></Suspense>} />
              <Route path="reports/crm" element={<Suspense fallback={<PageFallback />}><CrmReports /></Suspense>} />
              <Route path="reports/erp" element={<Suspense fallback={<PageFallback />}><ErpReports /></Suspense>} />
              <Route path="reports/mes" element={<Suspense fallback={<PageFallback />}><MesReports /></Suspense>} />
              <Route path="reports/custom" element={<Suspense fallback={<PageFallback />}><CustomReport /></Suspense>} />
              <Route path="bigscreen/:type" element={<Suspense fallback={<PageFallback />}><BigScreenTemplate /></Suspense>} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </PreferencesProvider>
    </AuthProvider>
  );
}

export default App;
