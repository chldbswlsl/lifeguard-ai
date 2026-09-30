// 백엔드 API 호출과 응답 타입. Vite 프록시가 /api → http://localhost:8000 으로 넘긴다.

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

const TOKEN_KEY = "lifeguard_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
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

  const res = await fetch(`/api${path}`, { method, headers, body });
  if (!res.ok) {
    throw new ApiError(res.status, await errorMessage(res));
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

// FastAPI 에러는 {detail: "문자열"} 또는 {detail: [{loc, msg}, ...]} (입력값 검증 실패) 형태다.
async function errorMessage(res: Response): Promise<string> {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("\n");
    }
  } catch {
    // JSON이 아닌 응답
  }
  return `요청에 실패했습니다 (${res.status})`;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", form: { username: email, password } }),
  signup: (data: { email: string; password: string; name: string; phone: string | null }) =>
    request<User>("/auth/signup", { method: "POST", json: data }),
  me: () => request<User>("/auth/me"),
  updateMe: (data: { name?: string; phone?: string | null }) =>
    request<User>("/auth/me", { method: "PATCH", json: data }),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("/auth/me/password", { method: "POST", json: { current_password, new_password } }),

  listSeniors: () => request<SeniorListItem[]>("/seniors"),
  getSenior: (id: number) => request<Senior>(`/seniors/${id}`),
  createSenior: (data: SeniorInput) => request<Senior>("/seniors", { method: "POST", json: data }),
  updateSenior: (id: number, data: Partial<SeniorInput>) =>
    request<Senior>(`/seniors/${id}`, { method: "PATCH", json: data }),
  deleteSenior: (id: number) => request<void>(`/seniors/${id}`, { method: "DELETE" }),
  listGuardians: (id: number) => request<User[]>(`/seniors/${id}/guardians`),
  linkGuardian: (id: number, email: string) =>
    request<User[]>(`/seniors/${id}/guardians`, { method: "POST", json: { email } }),

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
