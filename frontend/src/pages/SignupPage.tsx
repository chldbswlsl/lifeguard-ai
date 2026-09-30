import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate } from "react-router";
import { api, ApiError, errorMessage } from "../api";
import { useAuth } from "../auth";
import FieldError from "../components/FieldError";
import PasswordInput from "../components/PasswordInput";
import { checkNewPassword } from "../format";

export default function SignupPage() {
  const { user, login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", password2: "", name: "", phone: "" });
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    const pwProblem = checkNewPassword(form.password, form.email);
    if (pwProblem) return setFieldErrors({ password: pwProblem });
    if (form.password !== form.password2) return setFieldErrors({ password2: "비밀번호가 서로 다릅니다" });

    setBusy(true);
    try {
      const email = form.email.trim();
      await api.signup({ email, password: form.password, name: form.name.trim(), phone: form.phone.trim() || null });
      await login(email, form.password);
    } catch (err) {
      setError(errorMessage(err));
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>보호자 회원가입</h1>
        <label>
          이름
          <input value={form.name} onChange={set("name")} maxLength={50} autoComplete="name" required autoFocus />
          <FieldError errors={fieldErrors} name="name" />
        </label>
        <label>
          이메일
          <input type="email" value={form.email} onChange={set("email")} maxLength={255} autoComplete="email" required />
          <FieldError errors={fieldErrors} name="email" />
        </label>
        <label>
          연락처 <span className="muted">(선택)</span>
          <input
            type="tel"
            value={form.phone}
            onChange={set("phone")}
            placeholder="010-0000-0000"
            maxLength={20}
            autoComplete="tel"
          />
          <FieldError errors={fieldErrors} name="phone" />
        </label>
        <label>
          비밀번호 <span className="muted">(8자 이상, 영문과 숫자 포함)</span>
          <PasswordInput value={form.password} onChange={set("password")} maxLength={128} autoComplete="new-password" required />
          <FieldError errors={fieldErrors} name="password" />
        </label>
        <label>
          비밀번호 확인
          <PasswordInput value={form.password2} onChange={set("password2")} maxLength={128} autoComplete="new-password" required />
          <FieldError errors={fieldErrors} name="password2" />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
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
