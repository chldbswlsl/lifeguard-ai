import { useEffect } from "react";
import { createBrowserRouter, Navigate, NavLink, Outlet, useLocation } from "react-router";
import { RouterProvider } from "react-router/dom";
import { useAuth } from "./auth";
import ErrorBoundary from "./components/ErrorBoundary";
import LoginPage from "./pages/LoginPage";
import MyPage from "./pages/MyPage";
import SeniorDetailPage from "./pages/SeniorDetailPage";
import SeniorListPage from "./pages/SeniorListPage";
import SignupPage from "./pages/SignupPage";

// useBlocker(작성 중 이탈 경고)를 쓰려면 createBrowserRouter(데이터 라우터)가 필요하다.
const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  {
    element: <RequireLogin />,
    children: [
      { path: "/", element: <SeniorListPage /> },
      { path: "/seniors/:id", element: <SeniorDetailPage /> },
      { path: "/me", element: <MyPage /> },
      // 로그아웃도 "이동"으로 처리해서, 작성 중이면 이탈 경고가 먼저 뜨게 한다
      { path: "/logout", element: <Logout /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}

/** 로그인한 사용자만 들어올 수 있는 화면의 공통 레이아웃 */
function RequireLogin() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="center muted">불러오는 중…</p>;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            LifeGuard <span>AI</span>
          </NavLink>
          <nav>
            <NavLink to="/" end>
              어르신 목록
            </NavLink>
            <NavLink to="/me">내 정보</NavLink>
          </nav>
          <div className="who">
            <span className={`badge ${user.role}`}>{user.role === "admin" ? "관리자" : "보호자"}</span>
            {user.name}
            <NavLink to="/logout" className="link-button">
              로그아웃
            </NavLink>
          </div>
        </div>
      </header>
      <main className="container">
        <ErrorBoundary resetKey={location.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </>
  );
}

function Logout() {
  const { logout } = useAuth();
  useEffect(() => logout(), [logout]);
  return null;
}
