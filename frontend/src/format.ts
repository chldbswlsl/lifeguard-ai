/** "07:10:00" → "07:10" */
export function hhmm(time: string | null | undefined): string {
  return time ? time.slice(0, 5) : "-";
}

/** 로컬 날짜 기준 YYYY-MM-DD */
export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 오늘에서 n일 전 (음수면 n일 후) */
export function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDate(d);
}

/** 오늘 기준 며칠 전인지 (날짜 문자열 → 정수) */
export function daysSince(date: string): number {
  const [y, m, d] = date.split("-").map(Number);
  const then = new Date(y, m - 1, d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((today.getTime() - then.getTime()) / 86_400_000);
}

export function age(birthYear: number | null): string {
  return birthYear ? `${new Date().getFullYear() - birthYear}세` : "-"; // 생일 전이면 만 나이보다 1 많을 수 있음
}

export function num(n: number | null | undefined, unit = ""): string {
  return n === null || n === undefined ? "-" : `${n.toLocaleString()}${unit}`;
}

export const SOURCE_LABEL = { manual: "직접 입력", simulated: "가상", sensor: "센서" } as const;

/** 서버와 같은 비밀번호 규칙. 문제가 있으면 메시지, 없으면 "". */
export function checkNewPassword(password: string, email = ""): string {
  if (password.length < 8) return "8자 이상 입력해 주세요";
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return "영문과 숫자를 모두 포함해야 합니다";
  const e = email.trim().toLowerCase();
  if (e && [e, e.split("@")[0]].includes(password.toLowerCase())) return "이메일과 같은 비밀번호는 사용할 수 없습니다";
  return "";
}
