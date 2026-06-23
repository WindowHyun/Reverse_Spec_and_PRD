import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./auth";

export default function RequireAuth({ children, role }: { children: JSX.Element; role?: string }) {
  const { user } = useAuth();
  const location = useLocation();

  // 미인증 사용자는 로그인 페이지로 리다이렉트하고, 로그인 후 원래 페이지로 복귀
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 권한(role)이 지정된 경로는 해당 권한이 없으면 홈으로 차단
  if (role && user.role !== role) {
    return <Navigate to="/" replace />;
  }

  return children;
}
