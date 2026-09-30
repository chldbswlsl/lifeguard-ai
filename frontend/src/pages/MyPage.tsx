import { useState, type FormEvent } from "react";
import { api, ApiError, errorMessage } from "../api";
import { useAuth, useUser } from "../auth";
import { useDialog } from "../components/Dialog";
import FieldError from "../components/FieldError";
import PasswordInput from "../components/PasswordInput";
import { useLeaveGuard } from "../components/useLeaveGuard";
import { checkNewPassword } from "../format";

export default function MyPage() {
  const user = useUser();
  const { setUser } = useAuth();
  const { toast } = useDialog();

  const [name, setName] = useState(user.name);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [infoErrors, setInfoErrors] = useState<Record<string, string>>({});

  const [pw, setPw] = useState({ current: "", next: "", next2: "" });
  const [pwErrors, setPwErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const infoDirty = name !== user.name || phone !== (user.phone ?? "");
  const pwDirty = !!(pw.current || pw.next || pw.next2);
  useLeaveGuard(infoDirty || pwDirty);

  async function saveInfo(e: FormEvent) {
    e.preventDefault();
    setInfoErrors({});
    setBusy(true);
    try {
      setUser(await api.updateMe({ name: name.trim(), phone: phone.trim() || null }));
      toast("저장했습니다");
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setInfoErrors(err.fieldErrors);
      else toast(errorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPwErrors({});
    const problem = checkNewPassword(pw.next, user.email);
    if (problem) return setPwErrors({ new_password: problem });
    if (pw.next !== pw.next2) return setPwErrors({ next2: "새 비밀번호가 서로 다릅니다" });

    setBusy(true);
    try {
      await api.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", next2: "" });
      toast("비밀번호를 변경했습니다. 다른 기기에서는 다시 로그인해야 합니다");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) setPwErrors({ current_password: err.message });
      else if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setPwErrors(err.fieldErrors);
      else toast(errorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>내 정보</h1>
      <div className="grid-2">
        <form className="card form" onSubmit={saveInfo}>
          <h2>기본 정보</h2>
          <label>
            이메일
            <input value={user.email} disabled />
          </label>
          <label>
            이름
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={50} required />
            <FieldError errors={infoErrors} name="name" />
          </label>
          <label>
            연락처
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" maxLength={20} />
            <FieldError errors={infoErrors} name="phone" />
          </label>
          <button className="primary" disabled={busy || !infoDirty}>
            저장
          </button>
        </form>

        <form className="card form" onSubmit={changePassword} noValidate>
          <h2>비밀번호 변경</h2>
          <label>
            현재 비밀번호
            <PasswordInput
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
              autoComplete="current-password"
              maxLength={128}
              required
            />
            <FieldError errors={pwErrors} name="current_password" />
          </label>
          <label>
            새 비밀번호 <span className="muted">(8자 이상, 영문과 숫자 포함)</span>
            <PasswordInput
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
              autoComplete="new-password"
              maxLength={128}
              required
            />
            <FieldError errors={pwErrors} name="new_password" />
          </label>
          <label>
            새 비밀번호 확인
            <PasswordInput
              value={pw.next2}
              onChange={(e) => setPw({ ...pw, next2: e.target.value })}
              autoComplete="new-password"
              maxLength={128}
              required
            />
            <FieldError errors={pwErrors} name="next2" />
          </label>
          <button className="primary" disabled={busy || !pw.current || !pw.next}>
            변경
          </button>
        </form>
      </div>
    </>
  );
}
