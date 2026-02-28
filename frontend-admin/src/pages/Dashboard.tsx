import { useAuth } from "@/context/AuthContext";

export function Dashboard() {
  const { user } = useAuth();
  return (
    <div>
      <h1>概览</h1>
      <p>当前用户：{user?.username}，角色：{user?.role === "admin" ? "管理员" : "客户端"}</p>
    </div>
  );
}
