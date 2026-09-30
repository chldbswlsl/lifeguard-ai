// 백엔드 API 호출과 응답 타입. Vite 프록시가 /api → 백엔드(기본 http://localhost:8000)로 넘긴다.
//
// - 모든 요청은 10초 제한시간이 있다.
// - 에러는 ApiError 하나로 통일한다 (message: 사용자에게 보여줄 한국어, fieldErrors: 입력 칸별 메시지).
// - 로그인 상태에서 401을 받으면 저장된 로그인 정보를 지우고 "lifeguard-auth-expired" 이벤트를 보낸다.
//   AuthProvider가 이 이벤트를 듣고 로그인 화면으로 보낸다.

export type Role = "guardian" | "admin";
export type RecordSource = "manual" | "simulated" | "sensor";

export interface User {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  role: Role;
}

export interface SeniorInput {
  name: string;
  birth_year: number | null;
  phone: string | null;
  address: string | null;
  notes: string | null;
}

export interface Senior extends SeniorInput {
  id: number;
  created_at: string;
}

export interface SeniorListItem extends Senior {
  guardian_count: number;
  last_record_date: string | null;
  last_activity_level: number | null;
}

export interface DailyRecordInput {
  wake_time: string | null;
  sleep_time: string | null;
  activity_level: number | null;
  hourly_activity: number[] | null;
  meal_count: number | null;
  meal_times: string[] | null;
  outing_minutes: number | null;
  appliance_usage: number | null;
  source: RecordSource;
  memo: string | null;
}

export interface DailyRecord extends DailyRecordInput {
  id: number;
  senior_id: number;
  date: string;
  updated_at: string;
}

// ---------- 로그인 정보 저장 ----------
const STORAGE_PREFIX = "lifeguard_";
const TOKEN_KEY = `${STORAGE_PREFIX}token`;
export const AUTH_EXPIRED_EVENT = "lifeguard-auth-expired";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null; // 사생활 보호 모드 등에서 localStorage 접근이 막힌 경우
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {}
}

/** 로그아웃: 이 앱이 저장한 값을 모두 지운다 (토큰 외에 나중에 추가될 캐시 포함). */
export function clearSession() {
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(STORAGE_PREFIX))
      .forEach((k) => localStorage.removeItem(k));
  } catch {}
}

/** 토큰의 만료 시각(ms). 서명 검증은 하지 않는다 — 서버가 한다. 화면에서 미리 로그아웃시키는 용도. */
export function tokenExpiresAt(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

// ---------- 요청 ----------
const TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  status: number; // 0: 네트워크 오류·시간 초과
  fieldErrors: Record<string, string>;
  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  400: "요청 내용을 확인해 주세요",
  401: "로그인이 필요합니다",
  403: "권한이 없습니다",
  404: "찾을 수 없습니다",
  409: "이미 처리된 요청입니다",
  413: "요청 데이터가 너무 큽니다",
  422: "입력값을 확인해 주세요",
  429: "시도가 너무 많습니다. 잠시 후 다시 시도해 주세요",
};

function statusMessage(status: number): string {
  if (STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];
  if (status === 502 || status === 503 || status === 504) return "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요";
  if (status >= 500) return "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요";
  return `요청에 실패했습니다 (${status})`;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  json?: unknown;
  form?: Record<string, string>;
};

async function request<T>(path: string, { method = "GET", json, form }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (form) {
    body = new URLSearchParams(form);
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  let res: Response;
  try {
    res = await fetch(`/api${path}`, { method, headers, body, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (e) {
    const timedOut = e instanceof DOMException && e.name === "TimeoutError";
    throw new ApiError(0, timedOut ? "서버 응답이 너무 늦습니다. 잠시 후 다시 시도해 주세요" : "서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요");
  }

  const data = await readJson(res);
  if (!res.ok) {
    if (res.status === 401 && token) {
      clearSession();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    const fieldErrors: Record<string, string> = {};
    for (const e of Array.isArray(data?.errors) ? data.errors : []) {
      if (e?.field && !fieldErrors[e.field]) fieldErrors[e.field] = e.message;
    }
    const message = typeof data?.detail === "string" ? data.detail : statusMessage(res.status);
    throw new ApiError(res.status, message, fieldErrors);
  }
  return data as T;
}

/** JSON이 아닌 응답(프록시의 HTML 에러 페이지, 204 등)에도 터지지 않는다. */
async function readJson(res: Response): Promise<any> {
  try {
    const text = await res.text();
    return text ? JSON.parse(text) : undefined;
  } catch {
    return undefined;
  }
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", form: { username: email, password } }),
  signup: (data: { email: string; password: string; name: string; phone: string | null }) =>
    request<User>("/auth/signup", { method: "POST", json: data }),
  me: () => request<User>("/auth/me"),
  updateMe: (data: { name?: string; phone?: string | null }) =>
    request<User>("/auth/me", { method: "PATCH", json: data }),
  /** 성공하면 새 토큰을 저장한다 (이전 토큰은 서버에서 무효가 된다). */
  changePassword: async (current_password: string, new_password: string) => {
    const { access_token } = await request<{ access_token: string }>("/auth/me/password", {
      method: "POST",
      json: { current_password, new_password },
    });
    setToken(access_token);
  },

  listSeniors: () => request<SeniorListItem[]>("/seniors"),
  getSenior: (id: number) => request<Senior>(`/seniors/${id}`),
  createSenior: (data: SeniorInput) => request<Senior>("/seniors", { method: "POST", json: data }),
  updateSenior: (id: number, data: Partial<SeniorInput>) =>
    request<Senior>(`/seniors/${id}`, { method: "PATCH", json: data }),
  deleteSenior: (id: number) => request<void>(`/seniors/${id}`, { method: "DELETE" }),
  listGuardians: (id: number) => request<User[]>(`/seniors/${id}/guardians`),
  linkGuardian: (id: number, email: string) =>
    request<User[]>(`/seniors/${id}/guardians`, { method: "POST", json: { email } }),
  unlinkGuardian: (id: number, userId: number) =>
    request<User[]>(`/seniors/${id}/guardians/${userId}`, { method: "DELETE" }),

  listRecords: (seniorId: number, start?: string, end?: string) => {
    const q = new URLSearchParams();
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    return request<DailyRecord[]>(`/seniors/${seniorId}/records?${q}`);
  },
  saveRecord: (seniorId: number, date: string, data: DailyRecordInput) =>
    request<DailyRecord>(`/seniors/${seniorId}/records/${date}`, { method: "PUT", json: data }),
  deleteRecord: (seniorId: number, date: string) =>
    request<void>(`/seniors/${seniorId}/records/${date}`, { method: "DELETE" }),
};

/** catch 블록에서 사용자에게 보여줄 메시지를 꺼낸다. */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return "알 수 없는 오류가 발생했습니다";
}
