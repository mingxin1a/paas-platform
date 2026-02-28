import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Login } from "@/pages/Login";
import { AdminLayout } from "@/components/AdminLayout";
import { Dashboard } from "@/pages/Dashboard";
import { CellManage } from "@/pages/CellManage";
import { UserPermission } from "@/pages/UserPermission";
import { Audit } from "@/pages/Audit";
import { Monitoring } from "@/pages/Monitoring";
import { TenantManage } from "@/pages/TenantManage";
import { SystemConfig } from "@/pages/SystemConfig";
import { AlertManage } from "@/pages/AlertManage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RequireAuth><AdminLayout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="cells" element={<CellManage />} />
        <Route path="users" element={<UserPermission />} />
        <Route path="audit" element={<Audit />} />
        <Route path="monitoring" element={<Monitoring />} />
        <Route path="tenants" element={<TenantManage />} />
        <Route path="config" element={<SystemConfig />} />
        <Route path="alerts" element={<AlertManage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>;
}
