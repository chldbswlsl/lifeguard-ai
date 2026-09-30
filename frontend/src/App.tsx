import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from "react-router";
import { useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import MyPage from "./pages/MyPage";
import SeniorDetailPage from "./pages/SeniorDetailPage";
import SeniorListPage from "./pages/SeniorListPage";
import SignupPage from "./pages/SignupPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<RequireLogin />}>
          <Route path="/" element={<SeniorListPage />} />
          <Route path="/seniors/:id" element={<SeniorDetailPage />} />
          <Route path="/me" element={<MyPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

/** 로그인한 사용자만 들어올 수 있는 화면의 공통 레이아웃 */
function RequireLogin() {
  const { user, loading, logout } = useAuth();
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
            <button className="link" onClick={logout}>
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
