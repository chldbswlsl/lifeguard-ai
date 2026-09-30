import { useState, type FormEvent } from "react";
import type { Senior, SeniorInput } from "../api";

interface Props {
  initial?: Senior;
  submitLabel: string;
  onSubmit: (data: SeniorInput) => Promise<void>;
  onCancel: () => void;
}

export default function SeniorForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    birth_year: initial?.birth_year?.toString() ?? "",
    phone: initial?.phone ?? "",
    address: initial?.address ?? "",
    notes: initial?.notes ?? "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit({
        name: form.name.trim(),
        birth_year: form.birth_year ? Number(form.birth_year) : null,
        phone: form.phone || null,
        address: form.address || null,
        notes: form.notes || null,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="form-row">
        <label>
          이름
          <input value={form.name} onChange={set("name")} required autoFocus />
        </label>
        <label>
          출생연도
          <input type="number" min={1900} max={2100} value={form.birth_year} onChange={set("birth_year")} placeholder="1945" />
        </label>
        <label>
          연락처
          <input value={form.phone} onChange={set("phone")} placeholder="010-0000-0000" />
        </label>
      </div>
      <label>
        주소
        <input value={form.address} onChange={set("address")} />
      </label>
      <label>
        메모 <span className="muted">(건강 상태, 복용 약 등)</span>
        <textarea rows={2} value={form.notes} onChange={set("notes")} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button type="button" onClick={onCancel}>
          취소
        </button>
        <button className="primary" disabled={busy}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
