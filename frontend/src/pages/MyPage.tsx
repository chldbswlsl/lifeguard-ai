import { useState, type FormEvent } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function MyPage() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user!.name);
  const [phone, setPhone] = useState(user!.phone ?? "");
  const [infoMsg, setInfoMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [pw, setPw] = useState({ current: "", next: "", next2: "" });
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function saveInfo(e: FormEvent) {
    e.preventDefault();
    try {
      setUser(await api.updateMe({ name, phone: phone || null }));
      setInfoMsg({ ok: true, text: "저장했습니다" });
    } catch (err) {
      setInfoMsg({ ok: false, text: (err as Error).message });
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    if (pw.next !== pw.next2) {
      setPwMsg({ ok: false, text: "새 비밀번호가 서로 다릅니다" });
      return;
    }
    try {
      await api.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", next2: "" });
      setPwMsg({ ok: true, text: "비밀번호를 변경했습니다" });
    } catch (err) {
      setPwMsg({ ok: false, text: (err as Error).message });
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
            <input value={user!.email} disabled />
          </label>
          <label>
            이름
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            연락처
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" />
          </label>
          {infoMsg && <p className={infoMsg.ok ? "success" : "error"}>{infoMsg.text}</p>}
          <button className="primary">저장</button>
        </form>

        <form className="card form" onSubmit={changePassword}>
          <h2>비밀번호 변경</h2>
          <label>
            현재 비밀번호
            <input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required />
          </label>
          <label>
            새 비밀번호 <span className="muted">(8자 이상)</span>
            <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} minLength={8} required />
          </label>
          <label>
            새 비밀번호 확인
            <input type="password" value={pw.next2} onChange={(e) => setPw({ ...pw, next2: e.target.value })} minLength={8} required />
          </label>
          {pwMsg && <p className={pwMsg.ok ? "success" : "error"}>{pwMsg.text}</p>}
          <button className="primary">변경</button>
        </form>
      </div>
    </>
  );
}
