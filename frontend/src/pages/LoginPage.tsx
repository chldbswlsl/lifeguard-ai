import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router";
import { errorMessage } from "../api";
import { useAuth } from "../auth";
import PasswordInput from "../components/PasswordInput";

export default function LoginPage() {
  const { user, notice, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit}>
        <h1 className="brand">
          LifeGuard <span>AI</span>
        </h1>
        <p className="muted">독거노인 생활 안전 관리 서비스</p>
        {notice && <p className="notice">{notice}</p>}
        <label>
          이메일
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            maxLength={255}
            required
            autoFocus
          />
        </label>
        <label>
          비밀번호
          <PasswordInput
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            maxLength={128}
            required
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "로그인 중…" : "로그인"}
        </button>
        <p className="muted small">
          계정이 없으신가요? <Link to="/signup">보호자 회원가입</Link>
        </p>
      </form>
    </div>
  );
}
