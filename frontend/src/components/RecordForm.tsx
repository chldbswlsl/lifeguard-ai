import { useState, type FormEvent } from "react";
import { api, type DailyRecord, type DailyRecordInput } from "../api";
import { hhmm, isoDate } from "../format";

interface Props {
  seniorId: number;
  initial?: DailyRecord; // 있으면 수정, 없으면 새로 입력
  existingDates: Set<string>;
  onSaved: () => void;
  onCancel: () => void;
}

const toInt = (s: string): number | null => (s.trim() === "" ? null : Number(s));
const toTime = (s: string): string | null => (s === "" ? null : s);

export default function RecordForm({ seniorId, initial, existingDates, onSaved, onCancel }: Props) {
  const [f, setF] = useState({
    date: initial?.date ?? isoDate(new Date()),
    wake_time: initial?.wake_time?.slice(0, 5) ?? "",
    sleep_time: initial?.sleep_time?.slice(0, 5) ?? "",
    activity_level: initial?.activity_level?.toString() ?? "",
    meal_count: initial?.meal_count?.toString() ?? "",
    meal_times: initial?.meal_times?.map(hhmm).join(", ") ?? "",
    outing_minutes: initial?.outing_minutes?.toString() ?? "",
    appliance_usage: initial?.appliance_usage?.toString() ?? "",
    hourly_activity: initial?.hourly_activity?.join(", ") ?? "",
    memo: initial?.memo ?? "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setF({ ...f, [key]: e.target.value });

  function build(): DailyRecordInput {
    const mealTimes = f.meal_times.split(/[,\s]+/).filter(Boolean);
    const bad = mealTimes.find((t) => !/^([01]?\d|2[0-3]):[0-5]\d$/.test(t));
    if (bad) throw new Error(`식사 시각 형식이 올바르지 않습니다: "${bad}" (예: 08:00, 12:30)`);
    const mealTimesPadded = mealTimes.map((t) => t.padStart(5, "0")); // 8:00 → 08:00

    const hourlyParts = f.hourly_activity.split(/[,\s]+/).filter(Boolean);
    const hourly = hourlyParts.map(Number);
    if (hourly.length > 0 && (hourly.length !== 24 || hourly.some((n) => !Number.isInteger(n) || n < 0))) {
      throw new Error(`시간대별 활동량은 0 이상의 정수 24개여야 합니다 (현재 ${hourly.length}개)`);
    }

    return {
      wake_time: toTime(f.wake_time),
      sleep_time: toTime(f.sleep_time),
      // 총 활동량을 비워두면 시간대별 값의 합으로 채운다
      activity_level: toInt(f.activity_level) ?? (hourly.length ? hourly.reduce((a, b) => a + b, 0) : null),
      hourly_activity: hourly.length ? hourly : null,
      meal_count: toInt(f.meal_count) ?? (mealTimes.length || null),
      meal_times: mealTimes.length ? mealTimesPadded : null,
      outing_minutes: toInt(f.outing_minutes),
      appliance_usage: toInt(f.appliance_usage),
      source: "manual",
      memo: f.memo || null,
    };
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    let data: DailyRecordInput;
    try {
      data = build();
    } catch (err) {
      setError((err as Error).message);
      return;
    }
    if (!initial && existingDates.has(f.date) && !confirm(`${f.date} 기록이 이미 있습니다. 덮어쓸까요?`)) return;

    setBusy(true);
    try {
      await api.saveRecord(seniorId, f.date, data);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form record-form" onSubmit={submit}>
      <h3>{initial ? `${initial.date} 기록 수정` : "생활 기록 입력"}</h3>
      <div className="form-row">
        <label>
          날짜
          <input type="date" value={f.date} onChange={set("date")} disabled={!!initial} required />
        </label>
        <label>
          기상 시각
          <input type="time" value={f.wake_time} onChange={set("wake_time")} />
        </label>
        <label>
          취침 시각
          <input type="time" value={f.sleep_time} onChange={set("sleep_time")} />
        </label>
      </div>
      <div className="form-row">
        <label>
          총 활동량 <span className="muted">(움직임 횟수)</span>
          <input type="number" min={0} value={f.activity_level} onChange={set("activity_level")} />
        </label>
        <label>
          외출 시간 <span className="muted">(분)</span>
          <input type="number" min={0} max={1440} value={f.outing_minutes} onChange={set("outing_minutes")} />
        </label>
        <label>
          생활기기 사용 <span className="muted">(회)</span>
          <input type="number" min={0} value={f.appliance_usage} onChange={set("appliance_usage")} />
        </label>
      </div>
      <div className="form-row">
        <label>
          식사 횟수
          <input type="number" min={0} max={10} value={f.meal_count} onChange={set("meal_count")} />
        </label>
        <label className="grow">
          식사 시각 <span className="muted">(쉼표로 구분)</span>
          <input value={f.meal_times} onChange={set("meal_times")} placeholder="08:00, 12:30, 18:00" />
        </label>
      </div>
      <label>
        시간대별 활동량 <span className="muted">(선택 · 0시~23시 24개 값, 쉼표로 구분)</span>
        <input value={f.hourly_activity} onChange={set("hourly_activity")} placeholder="0, 0, 0, 0, 0, 0, 5, 30, …" />
      </label>
      <label>
        메모
        <textarea rows={2} value={f.memo} onChange={set("memo")} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button type="button" onClick={onCancel}>
          취소
        </button>
        <button className="primary" disabled={busy}>
          {busy ? "저장 중…" : "저장"}
        </button>
      </div>
    </form>
  );
}
