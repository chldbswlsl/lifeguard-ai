import { useState, type ChangeEvent, type FormEvent } from "react";
import { api, ApiError, errorMessage, type DailyRecord, type DailyRecordInput } from "../api";
import { daysAgo, hhmm, isoDate } from "../format";
import { useDialog } from "./Dialog";
import FieldError from "./FieldError";
import { useLeaveGuard } from "./useLeaveGuard";

interface Props {
  seniorId: number;
  initial?: DailyRecord; // 있으면 수정, 없으면 새로 입력
  existingDates: Set<string>;
  onSaved: () => void;
  onCancel: () => void;
}

const toInt = (s: string): number | null => (s.trim() === "" ? null : Number(s));
const toTime = (s: string): string | null => (s === "" ? null : s);

function toForm(r?: DailyRecord) {
  return {
    date: r?.date ?? isoDate(new Date()),
    wake_time: r?.wake_time?.slice(0, 5) ?? "",
    sleep_time: r?.sleep_time?.slice(0, 5) ?? "",
    activity_level: r?.activity_level?.toString() ?? "",
    meal_count: r?.meal_count?.toString() ?? "",
    meal_times: r?.meal_times?.map(hhmm).join(", ") ?? "",
    outing_minutes: r?.outing_minutes?.toString() ?? "",
    appliance_usage: r?.appliance_usage?.toString() ?? "",
    hourly_activity: r?.hourly_activity?.join(", ") ?? "",
    memo: r?.memo ?? "",
  };
}

/** 입력값을 API 형식으로 바꾼다. 문제가 있으면 {항목: 메시지}를 던진다. */
function build(f: ReturnType<typeof toForm>): DailyRecordInput {
  const errors: Record<string, string> = {};

  const mealTimes = f.meal_times.split(/[,\s]+/).filter(Boolean);
  const bad = mealTimes.find((t) => !/^([01]?\d|2[0-3]):[0-5]\d$/.test(t));
  if (bad) errors.meal_times = `시각 형식이 올바르지 않습니다: "${bad}" (예: 08:00, 12:30)`;

  const hourly = f.hourly_activity.split(/[,\s]+/).filter(Boolean).map(Number);
  if (hourly.length > 0 && (hourly.length !== 24 || hourly.some((n) => !Number.isInteger(n) || n < 0))) {
    errors.hourly_activity = `0 이상의 정수 24개여야 합니다 (현재 ${hourly.length}개)`;
  }

  for (const key of ["activity_level", "meal_count", "outing_minutes", "appliance_usage"] as const) {
    const v = f[key].trim();
    if (v && (!Number.isInteger(Number(v)) || Number(v) < 0)) errors[key] = "0 이상의 정수를 입력해 주세요";
  }
  if (Object.keys(errors).length) throw errors;

  return {
    wake_time: toTime(f.wake_time),
    sleep_time: toTime(f.sleep_time),
    // 총 활동량을 비워두면 시간대별 값의 합으로 채운다
    activity_level: toInt(f.activity_level) ?? (hourly.length ? hourly.reduce((a, b) => a + b, 0) : null),
    hourly_activity: hourly.length ? hourly : null,
    meal_count: toInt(f.meal_count) ?? (mealTimes.length || null),
    meal_times: mealTimes.length ? mealTimes.map((t) => t.padStart(5, "0")) : null, // 8:00 → 08:00
    outing_minutes: toInt(f.outing_minutes),
    appliance_usage: toInt(f.appliance_usage),
    source: "manual",
    memo: f.memo.trim() || null,
  };
}

export default function RecordForm({ seniorId, initial, existingDates, onSaved, onCancel }: Props) {
  const { confirmDialog, toast } = useDialog();
  const [original] = useState(() => toForm(initial));
  const [f, setF] = useState(original);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useLeaveGuard(!saved && JSON.stringify(f) !== JSON.stringify(original));

  const set = (key: keyof typeof f) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setF({ ...f, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    let data: DailyRecordInput;
    try {
      data = build(f);
    } catch (errs) {
      setFieldErrors(errs as Record<string, string>);
      return;
    }
    if (
      !initial &&
      existingDates.has(f.date) &&
      !(await confirmDialog({
        title: "이미 기록이 있습니다",
        message: `${f.date} 기록을 새 내용으로 덮어쓸까요? 이전 내용은 사라집니다.`,
        confirmText: "덮어쓰기",
        danger: true,
      }))
    ) {
      return;
    }

    setBusy(true);
    try {
      await api.saveRecord(seniorId, f.date, data);
      setSaved(true);
      toast(`${f.date} 기록을 저장했습니다`);
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form record-form" onSubmit={submit} noValidate>
      <h3>{initial ? `${initial.date} 기록 수정` : "생활 기록 입력"}</h3>
      <div className="form-row">
        <label>
          날짜
          <input type="date" value={f.date} onChange={set("date")} max={daysAgo(-1)} disabled={!!initial} required />
          <FieldError errors={fieldErrors} name="date" />
        </label>
        <label>
          기상 시각
          <input type="time" value={f.wake_time} onChange={set("wake_time")} />
          <FieldError errors={fieldErrors} name="wake_time" />
        </label>
        <label>
          취침 시각
          <input type="time" value={f.sleep_time} onChange={set("sleep_time")} />
          <FieldError errors={fieldErrors} name="sleep_time" />
        </label>
      </div>
      <div className="form-row">
        <label>
          총 활동량 <span className="muted">(움직임 횟수)</span>
          <input type="number" min={0} value={f.activity_level} onChange={set("activity_level")} />
          <FieldError errors={fieldErrors} name="activity_level" />
        </label>
        <label>
          외출 시간 <span className="muted">(분)</span>
          <input type="number" min={0} max={1440} value={f.outing_minutes} onChange={set("outing_minutes")} />
          <FieldError errors={fieldErrors} name="outing_minutes" />
        </label>
        <label>
          생활기기 사용 <span className="muted">(회)</span>
          <input type="number" min={0} value={f.appliance_usage} onChange={set("appliance_usage")} />
          <FieldError errors={fieldErrors} name="appliance_usage" />
        </label>
      </div>
      <div className="form-row">
        <label>
          식사 횟수
          <input type="number" min={0} max={10} value={f.meal_count} onChange={set("meal_count")} />
          <FieldError errors={fieldErrors} name="meal_count" />
        </label>
        <label className="grow">
          식사 시각 <span className="muted">(쉼표로 구분)</span>
          <input value={f.meal_times} onChange={set("meal_times")} placeholder="08:00, 12:30, 18:00" />
          <FieldError errors={fieldErrors} name="meal_times" />
        </label>
      </div>
      <label>
        시간대별 활동량 <span className="muted">(선택 · 0시~23시 24개 값, 쉼표로 구분)</span>
        <input value={f.hourly_activity} onChange={set("hourly_activity")} placeholder="0, 0, 0, 0, 0, 0, 5, 30, …" />
        <FieldError errors={fieldErrors} name="hourly_activity" />
      </label>
      <label>
        메모
        <textarea rows={2} value={f.memo} onChange={set("memo")} maxLength={1000} />
        <FieldError errors={fieldErrors} name="memo" />
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
          {busy ? "저장 중…" : "저장"}
        </button>
      </div>
    </form>
  );
}
