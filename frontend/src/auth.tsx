// 로그인 상태. 토큰은 localStorage에 저장하고, 사용자 정보는 서버에서 받아온다.
//
// 자동 로그아웃되는 경우
// - API가 401을 돌려줄 때 (api.ts가 AUTH_EXPIRED_EVENT를 보낸다)
// - 토큰 만료 시각이 지났을 때 (창에 다시 들어올 때, 탭이 다시 보일 때, 1분마다 확인)

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, AUTH_EXPIRED_EVENT, clearSession, getToken, setToken, tokenExpiresAt, type User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  /** 로그인 화면에 보여줄 안내 (예: 세션 만료) */
  notice: string;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

function isExpired(): boolean {
  const token = getToken();
  const exp = token ? tokenExpiresAt(token) : null;
  return exp !== null && exp <= Date.now();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // 저장된 토큰이 유효해 보일 때만 "불러오는 중"으로 시작한다
  const [loading, setLoading] = useState(() => {
    const usable = !!getToken() && !isExpired();
    if (!usable) clearSession();
    return usable;
  });
  const [notice, setNotice] = useState("");

  // 새로고침해도 로그인이 유지되도록, 저장된 토큰으로 내 정보를 불러온다.
  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => clearSession())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const expire = () => {
      clearSession();
      setUser((prev) => {
        if (prev) setNotice("로그인이 만료되었습니다. 다시 로그인해 주세요");
        return null;
      });
    };
    const check = () => {
      if (getToken() && isExpired()) expire();
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, expire);
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    const timer = setInterval(check, 60_000);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, expire);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
      clearInterval(timer);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    setNotice("");
    setUser(await api.me());
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setNotice("");
    setUser(null);
  }, []);

  return <AuthContext value={{ user, loading, notice, login, logout, setUser }}>{children}</AuthContext>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth는 AuthProvider 안에서만 사용할 수 있습니다");
  return ctx;
}

/** 로그인한 화면에서만 쓴다. user가 없으면 에러 (RequireLogin이 먼저 막아준다). */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("로그인한 화면에서만 사용할 수 있습니다");
  return user;
}
