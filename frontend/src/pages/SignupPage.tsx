import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";

export default function SignupPage() {
  const { user, login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", password2: "", name: "", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.password !== form.password2) {
      setError("비밀번호가 서로 다릅니다");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.signup({ email: form.email, password: form.password, name: form.name, phone: form.phone || null });
      await login(form.email, form.password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit}>
        <h1>보호자 회원가입</h1>
        <label>
          이름
          <input value={form.name} onChange={set("name")} required autoFocus />
        </label>
        <label>
          이메일
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label>
          연락처 <span className="muted">(선택)</span>
          <input value={form.phone} onChange={set("phone")} placeholder="010-0000-0000" />
        </label>
        <label>
          비밀번호 <span className="muted">(8자 이상)</span>
          <input type="password" value={form.password} onChange={set("password")} minLength={8} required />
        </label>
        <label>
          비밀번호 확인
          <input type="password" value={form.password2} onChange={set("password2")} minLength={8} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "가입 중…" : "가입하기"}
        </button>
        <p className="muted small">
          이미 계정이 있으신가요? <Link to="/login">로그인</Link>
        </p>
      </form>
    </div>
  );
}
