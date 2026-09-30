import { useState, type ChangeEvent, type FormEvent } from "react";
import { ApiError, errorMessage, type Senior, type SeniorInput } from "../api";
import FieldError from "./FieldError";
import { useLeaveGuard } from "./useLeaveGuard";

interface Props {
  initial?: Senior;
  submitLabel: string;
  onSubmit: (data: SeniorInput) => Promise<void>;
  onCancel: () => void;
}

function toForm(s?: Senior) {
  return {
    name: s?.name ?? "",
    birth_year: s?.birth_year?.toString() ?? "",
    phone: s?.phone ?? "",
    address: s?.address ?? "",
    notes: s?.notes ?? "",
  };
}

export default function SeniorForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [original] = useState(() => toForm(initial));
  const [form, setForm] = useState(original);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const dirty = !saved && JSON.stringify(form) !== JSON.stringify(original);
  useLeaveGuard(dirty);

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setFieldErrors({});
    try {
      setSaved(true); // 저장 후 다른 화면으로 이동할 때 이탈 경고가 뜨지 않게
      await onSubmit({
        name: form.name.trim(),
        birth_year: form.birth_year ? Number(form.birth_year) : null,
        phone: form.phone.trim() || null,
        address: form.address.trim() || null,
        notes: form.notes.trim() || null,
      });
    } catch (err) {
      setSaved(false);
      setError(errorMessage(err));
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="form-row">
        <label>
          이름
          <input value={form.name} onChange={set("name")} maxLength={50} required autoFocus />
          <FieldError errors={fieldErrors} name="name" />
        </label>
        <label>
          출생연도
          <input
            type="number"
            min={1900}
            max={new Date().getFullYear()}
            value={form.birth_year}
            onChange={set("birth_year")}
            placeholder="1945"
          />
          <FieldError errors={fieldErrors} name="birth_year" />
        </label>
        <label>
          연락처
          <input type="tel" value={form.phone} onChange={set("phone")} placeholder="010-0000-0000" maxLength={20} />
          <FieldError errors={fieldErrors} name="phone" />
        </label>
      </div>
      <label>
        주소
        <input value={form.address} onChange={set("address")} maxLength={255} />
        <FieldError errors={fieldErrors} name="address" />
      </label>
      <label>
        메모 <span className="muted">(건강 상태, 복용 약 등)</span>
        <textarea rows={2} value={form.notes} onChange={set("notes")} maxLength={2000} />
        <FieldError errors={fieldErrors} name="notes" />
      </label>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="actions">
        <button type="button" onClick={onCancel}>
          취소
        </button>
        <button className="primary" disabled={busy}>
          {busy ? "저장 중…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
