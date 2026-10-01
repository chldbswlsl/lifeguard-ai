# LifeGuard AI

AI를 활용한 독거노인 생활 안전 관리 서비스.
어르신의 평소 생활 패턴을 기록·분석하고, 평소와 다른 변화가 보이면 보호자에게 먼저 알려준다.
사고가 난 뒤에 대응하는 방식이 아니라, 위험 가능성을 미리 감지하는 것이 목표다.

- 기획 문서: `LifeGuard_AI_프로젝트_계획_보고서.docx`는 목표, 기능, 월별 일정의 원본이다. **저장소에는 올리지 않았으니** 필요하면 담당자에게 받는다.
- 저장소: https://github.com/chldbswlsl/lifeguard-ai (공개)
- **진행 상황·일정·다음 작업·작업 로그는 [PROGRESS.md](PROGRESS.md)에 있다.** 작업을 하면 그쪽을 갱신한다.

---

## 무엇을 하나

| 기능 | 내용 |
|---|---|
| 생활 기록 | 기상·취침, 활동량, 식사·외출, 시간대별 활동을 날짜별로 기록 |
| 평소 패턴 비교 | 최근 7일(또는 14일) 기록으로 평소 패턴을 구하고 오늘과 비교 |
| 위험도 | 이상 징후가 겹칠수록 가중해 0~100점, 안전·주의·위험 3단계와 이유 문장으로 표시 |
| 보호자 알림 | 위험도가 기준을 넘으면 보호자에게 알림 |
| 화면 | 보호자용(담당 어르신 상태), 관리자용(여러 명을 위험도 순으로) |

어디까지 만들었는지는 [PROGRESS.md](PROGRESS.md)를 본다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python, FastAPI, SQLAlchemy 2, uv |
| DB | PostgreSQL 17 (Docker), 개발용 SQLite 가능 |
| 프론트엔드 | React 19, Vite, TypeScript, react-router |
| 테스트·검사 | pytest, Playwright e2e, ruff, ESLint, GitHub Actions |

---

## 목차

1. [처음 세팅하기](#처음-세팅하기)
2. [매일 개발 시작하기](#매일-개발-시작하기)
3. [폴더 구조](#폴더-구조)
4. [데이터 모델](#데이터-모델)
5. [API](#api)
6. [프론트엔드 구조](#프론트엔드-구조)
7. [보안](#보안)
8. [설계 결정과 이유](#설계-결정과-이유)
9. [테스트와 코드 검사](#테스트와-코드-검사)
10. [Git 작업 규칙](#git-작업-규칙)
11. [알려진 문제와 주의사항](#알려진-문제와-주의사항)

---

## 처음 세팅하기

### 필요한 프로그램

| 프로그램 | 확인한 버전 | 용도 |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.12 | Python 패키지·가상환경 관리 (pip 대신 사용) |
| Python | 3.12 이상 (uv가 자동 설치) | 백엔드 |
| Node.js | 24 | 프론트엔드 |
| Docker Desktop | 29 | PostgreSQL 실행 |

### 순서

```bash
# 0) 코드 받기
git clone https://github.com/chldbswlsl/lifeguard-ai.git
cd lifeguard-ai

# 1) DB — Docker Desktop을 먼저 켠다
docker compose up -d                 # postgres:17, localhost:5432, 계정/비번/DB 모두 lifeguard

# 2) 백엔드
cd backend
cp .env.example .env                 # 필요하면 값 수정
uv sync                              # 패키지 설치 (.venv 생성)
uv run python -m app.seed            # 테스트 계정 + 어르신 3명 + 28일치 가상 기록
uv run playwright install chromium   # e2e 테스트용 브라우저 (처음 한 번, 약 115MB)

# 3) 프론트엔드
cd ../frontend
npm install
```

### 테스트 계정 (seed가 만든다)

| 역할 | 이메일 | 비밀번호 | 비고 |
|---|---|---|---|
| 관리자 | admin@lifeguard.dev | admin1234 | 모든 어르신 조회, 삭제, 보호자 연결 |
| 보호자 | guardian@lifeguard.dev | guardian1234 | A 어르신만 담당 |

- 어르신: A(평범한 패턴), B(아침형·활동 적음), C(저녁형·외출 많음). 기록은 seed를 실행한 날 기준 **어제까지 28일치**다.
- seed는 관리자 계정이 이미 있으면 아무것도 하지 않는다. 처음부터 다시 만들려면 [DB 초기화](#db-초기화)를 본다.

---

## 매일 개발 시작하기

터미널 3개를 쓴다.

```bash
docker compose up -d                                  # 1) DB (이미 켜져 있으면 생략)
cd backend  && uv run fastapi dev app/main.py         # 2) API  http://localhost:8000/docs
cd frontend && npm run dev                            # 3) 웹   http://localhost:5173
```

- 웹은 http://localhost:5173 으로 접속한다. 프론트엔드의 `/api/...` 요청은 Vite 프록시가 `localhost:8000`으로 넘긴다(`frontend/vite.config.ts`). 그래서 CORS 설정 없이 동작한다.
- API를 직접 눌러보려면 http://localhost:8000/docs 에 들어가서 **Authorize**를 누르고, username에 이메일을 넣는다.
- Docker 없이 급하게 확인해야 하면 `backend/.env`에 `DATABASE_URL=sqlite:///./dev.db`를 넣어 SQLite로도 실행할 수 있다.

### DB 초기화

모델(테이블 구조)을 바꿨거나 데이터를 처음 상태로 되돌리고 싶을 때:

```bash
docker compose down -v        # ⚠ DB 데이터 전부 삭제
docker compose up -d
cd backend && uv run python -m app.seed
```

---

## 폴더 구조

```
lifeguard/
├── README.md                  # ← 이 문서 (인수인계용)
├── LifeGuard_AI_프로젝트_계획_보고서.docx   # 로컬에만 있음 (.gitignore)
├── docker-compose.yml         # PostgreSQL 17
├── .github/workflows/ci.yml   # GitHub Actions (코드 검사 + 테스트 + e2e)
├── backend/                   # FastAPI 서버
│   ├── pyproject.toml         # 의존성 (uv), pytest·coverage·ruff 설정
│   ├── .env.example           # 환경변수 예시·설명 → .env로 복사해서 사용 (.env는 git 제외)
│   ├── app/
│   │   ├── main.py            # 앱 생성, CORS, 라우터 등록, /health, 시작 시 테이블 생성
│   │   ├── config.py          # 환경변수 (운영 환경에서 약한 SECRET_KEY면 시작 거부)
│   │   ├── database.py        # SQLAlchemy 엔진·세션, get_db
│   │   ├── models.py          # DB 테이블 정의
│   │   ├── schemas.py         # 요청/응답 형식 (Pydantic) + 입력 검증
│   │   ├── security.py        # 비밀번호 해시(argon2), JWT 발급·검증, 시도 횟수 제한(RateLimiter)
│   │   ├── http.py            # 보안 헤더, 본문 크기 제한, 에러 응답 형식(한국어), 클라이언트 IP
│   │   ├── deps.py            # 로그인 사용자, 관리자 확인, 어르신 접근 권한 확인
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth — 가입, 로그인, 내 정보, 비밀번호 변경
│   │   │   ├── seniors.py     # /seniors — 어르신 CRUD, 목록 요약, 보호자 연결
│   │   │   └── records.py     # /seniors/{id}/records — 생활 기록
│   │   ├── simulate.py        # 가상 생활 데이터 생성기 (LifeProfile → 하루 기록)
│   │   └── seed.py            # 개발용 초기 데이터
│   └── tests/
│       ├── conftest.py        # 공통 fixture (SQLite 메모리 DB, 로그인된 guardian/admin 헤더)
│       ├── test_auth.py / test_seniors.py / test_records.py / test_http.py
│       └── e2e/               # Playwright 브라우저 테스트 (pytest -m e2e)
└── frontend/                  # React 웹 (Vite + TypeScript)
    ├── vite.config.ts         # /api → 백엔드 프록시 (API_URL 환경변수로 변경 가능)
    ├── eslint.config.js       # 코드 검사 규칙
    └── src/
        ├── main.tsx           # 진입점 (ErrorBoundary → DialogProvider → AuthProvider → App)
        ├── App.tsx            # 라우팅, 로그인 필요 화면의 공통 레이아웃(상단 메뉴)
        ├── api.ts             # 백엔드 호출 함수 + 응답 타입 + 에러 처리 (API가 바뀌면 여기부터 수정)
        ├── auth.tsx           # 로그인 상태, 토큰 만료·401 시 자동 로그아웃
        ├── format.ts          # 날짜·시간·숫자 표시, 비밀번호 규칙 검사
        ├── index.css          # 전체 스타일 (색은 :root 변수)
        ├── pages/
        │   ├── LoginPage.tsx
        │   ├── SignupPage.tsx
        │   ├── SeniorListPage.tsx    # 어르신 목록 = 기본 관리자 페이지
        │   ├── SeniorDetailPage.tsx  # 어르신 상세 + 보호자 + 생활 기록 표
        │   └── MyPage.tsx            # 내 정보, 비밀번호 변경
        └── components/
            ├── SeniorForm.tsx        # 어르신 등록·수정 폼
            ├── RecordForm.tsx        # 생활 기록 입력·수정 폼
            ├── HourlyBars.tsx        # 시간대별 활동량 막대 24개
            ├── Dialog.tsx            # 확인창·알림(toast) — window.confirm/alert 대신 사용
            ├── ErrorBoundary.tsx     # 화면 오류가 나도 앱 전체가 멈추지 않게
            ├── useLeaveGuard.ts      # 작성 중 이탈 경고
            ├── PasswordInput.tsx     # 보기/숨기기 버튼이 있는 비밀번호 입력
            └── FieldError.tsx        # 입력 칸 아래 에러 메시지
```

---

## 데이터 모델

```
users ──< guardian_senior >── seniors ──< daily_records
(보호자·관리자)   (N:N 연결)      (어르신)      (날짜별 생활 기록, 어르신당 하루 1건)
```

### users
| 컬럼 | 설명 |
|---|---|
| email | 로그인 ID, 소문자로 저장, 중복 불가 |
| password_hash | argon2 해시 |
| name, phone | 이름, 연락처 |
| role | `guardian`(보호자) / `admin`(관리자) |
| token_version | 비밀번호를 바꿀 때마다 1 증가. 토큰 안의 버전과 다르면 그 토큰은 무효 |

### seniors
| 컬럼 | 설명 |
|---|---|
| name, birth_year, phone, address | 기본 정보 |
| notes | 메모 (건강 상태, 복용 약 등) |

### daily_records — `(senior_id, date)` 조합이 유일하다
| 컬럼 | 타입 | 설명 |
|---|---|---|
| date | date | 기록 날짜 |
| wake_time, sleep_time | time | 기상·취침 시각. 자정을 넘겨 자면 `00:30`처럼 기록 |
| activity_level | int | 하루 총 움직임 (움직임 감지 횟수 또는 걸음 수) |
| hourly_activity | JSON `int[24]` | 0시~23시 시간대별 움직임. **AI 분석의 핵심 데이터** |
| meal_count | int | 식사 횟수 |
| meal_times | JSON `["08:00", …]` | 식사 시각 |
| outing_minutes | int | 외출 시간(분) |
| appliance_usage | int | 냉장고·TV 등 생활기기 사용 횟수 |
| source | str | `manual`(직접 입력) / `simulated`(가상) / `sensor`(센서) |
| memo | text | 메모 |

모든 생활 항목은 비워둘 수 있다(nullable). 센서마다 수집 가능한 항목이 다르기 때문이다.

---

## API

로그인 후 받은 토큰을 `Authorization: Bearer <토큰>` 헤더에 넣는다. 자세한 형식은 http://localhost:8000/docs 에서 확인한다.

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| POST | `/auth/signup` | 누구나 | 보호자 회원가입 (관리자 계정은 seed로만 만든다) |
| POST | `/auth/login` | 누구나 | form 형식: `username`=이메일, `password` → `access_token` |
| GET | `/auth/me` | 로그인 | 내 정보 |
| PATCH | `/auth/me` | 로그인 | 이름·연락처 수정 (보낸 필드만 바뀜) |
| POST | `/auth/me/password` | 로그인 | 비밀번호 변경 (현재 비밀번호 필요). **새 토큰을 돌려준다** — 이전 토큰은 모두 무효 |
| GET | `/seniors` | 로그인 | 어르신 목록 + 최근 기록 요약(`last_record_date`, `last_activity_level`, `guardian_count`). 보호자는 담당 어르신만 |
| POST | `/seniors` | 로그인 | 어르신 등록. 보호자가 등록하면 자동으로 본인과 연결 |
| GET | `/seniors/{id}` | 담당·관리자 | 어르신 조회 |
| PATCH | `/seniors/{id}` | 담당·관리자 | 어르신 수정 (보낸 필드만 바뀜) |
| DELETE | `/seniors/{id}` | 관리자 | 어르신과 모든 기록 삭제 |
| GET | `/seniors/{id}/guardians` | 담당·관리자 | 담당 보호자 목록 |
| POST | `/seniors/{id}/guardians` | 관리자 | 가입된 보호자를 이메일로 연결 |
| DELETE | `/seniors/{id}/guardians/{user_id}` | 관리자 | 보호자 연결 해제 (계정은 남는다) |
| GET | `/seniors/{id}/records?start=&end=` | 담당·관리자 | 기간 조회 (양 끝 포함, 날짜 오름차순, **최대 366일**). start를 생략하면 end로부터 366일 전부터 |
| PUT | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 그날 기록 저장. 새로 만들면 201, 있으면 **전체 덮어쓰기** 후 200. 내일보다 미래 날짜는 거절 |
| GET | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 하루 기록 |
| DELETE | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 하루 기록 삭제 |
| GET | `/health` | 누구나 | 서버와 DB 상태 (`{"status":"ok","db":"ok"}`, DB가 안 되면 503) |

### 에러 응답 형식

모든 에러는 `{"detail": "사용자에게 보여줄 한국어 메시지"}` 형식이다 (`app/http.py`).
입력값 검증 실패(422)는 항목별 에러가 추가된다.

```json
{
  "detail": "비밀번호: 8자 이상 입력해 주세요 / 연락처: 형식이 올바르지 않습니다",
  "errors": [
    {"field": "password", "label": "비밀번호", "message": "8자 이상 입력해 주세요"},
    {"field": "phone", "label": "연락처", "message": "형식이 올바르지 않습니다"}
  ]
}
```

| 상태 코드 | 의미 |
|---|---|
| 401 | 로그인 필요 / 토큰 만료·무효 (프론트엔드는 자동 로그아웃) |
| 403 | 권한 없음 (보호자가 관리자 기능 요청) |
| 404 | 없음, **또는 담당이 아닌 어르신** |
| 409 | 중복 (이미 가입된 이메일) |
| 413 | 요청 본문이 너무 큼 (기본 512KB) |
| 422 | 입력값 오류 (정의되지 않은 필드를 보내도 422) |
| 429 | 시도 횟수 초과 (`Retry-After` 헤더에 기다릴 초) |
| 500 | 서버 오류. 내부 정보는 응답에 넣지 않고 서버 로그에만 남긴다 |

---

## 프론트엔드 구조

| 경로 | 화면 | 누가 |
|---|---|---|
| `/login`, `/signup` | 로그인, 보호자 회원가입 | 누구나 |
| `/` | 어르신 목록. 관리자에게는 현황 카드(등록 수, 2일 이상 기록 없음, 보호자 미연결)가 보인다 | 로그인 |
| `/seniors/:id` | 기본 정보, 보호자(관리자는 연결 가능), 최근 28일 생활 기록 표, 기록 입력·수정·삭제 | 담당·관리자 |
| `/me` | 내 정보 수정, 비밀번호 변경 | 로그인 |

### 화면 코드 작성 규칙

| 하고 싶은 것 | 방법 |
|---|---|
| API 호출 | `src/api.ts`에 타입과 함수를 추가하고 `api.xxx()`로 호출한다. 화면 코드에서 `fetch`를 직접 쓰지 않는다 |
| 에러 메시지 표시 | `catch (e) { setError(errorMessage(e)) }`. 입력 칸별 에러는 `e.fieldErrors` → `<FieldError errors={…} name="필드명" />` |
| 삭제 등 확인 받기 | `const { confirmDialog } = useDialog();` → `if (!(await confirmDialog({ title, message, confirmText: "삭제", danger: true }))) return;` — **`window.confirm` 금지** |
| 성공·실패 알림 | `toast("저장했습니다")`, `toast("실패", "error")` — **`alert` 금지** |
| 작성 중 이탈 경고 | 폼 컴포넌트에서 `useLeaveGuard(수정했는지)` |
| 비밀번호 입력 | `<PasswordInput autoComplete="current-password" 또는 "new-password" />` |
| 로그인한 사용자 | `const user = useUser();` (로그인 화면이 아닌 곳에서만) |

- API 요청은 10초가 지나면 "서버 응답이 너무 늦습니다"로 실패한다.
- 로그인 토큰은 `localStorage`의 `lifeguard_token`에 저장된다. 만료 기간은 24시간이다(`ACCESS_TOKEN_EXPIRE_MINUTES`). API가 401을 주거나 만료 시각이 지나면 자동으로 로그인 화면으로 가고 "로그인이 만료되었습니다" 안내가 뜬다. 로그아웃하면 `lifeguard_`로 시작하는 저장값이 모두 지워진다.
- 로그아웃은 `/logout` 경로로 **이동**하는 방식이다. 그래서 작성 중이면 이탈 경고가 먼저 뜬다.
- 별도 UI 라이브러리 없이 `index.css` 하나로 스타일을 관리한다. 색은 `:root`의 변수로 정의되어 있다.
- 목록의 **위험도** 칸은 지금 "분석 준비 중"이라고만 표시한다. 10월 AI 작업이 끝나면 실제 값으로 바꾼다(`SeniorListPage.tsx`).

---

## 보안

공개 저장소이고 어르신 생활 정보는 민감한 개인정보다(계획서 6장). 아래 항목은 **테스트로 확인하고 있으니** 바꿀 때 테스트도 같이 고친다.
bp-portal, CO2 프로젝트에서 쓰던 방식을 맞춰서 적용했다.

| 항목 | 내용 | 위치 |
|---|---|---|
| 비밀번호 저장 | argon2 해시 | `security.py` |
| 비밀번호 규칙 | 8~128자, 영문과 숫자 포함, 이메일(또는 이메일 앞부분)과 같으면 거절 | `schemas.py`, 화면은 `format.ts` |
| 가입 여부 숨김 | 없는 이메일로 로그인해도 해시 검증을 똑같이 수행한다 → 응답 시간·메시지가 같다 | `security.py` |
| 로그인 시도 제한 | 같은 이메일 또는 같은 IP로 5번 실패하면 15분 잠금 (429). 성공하면 이메일 카운터만 초기화, IP 카운터는 유지 | `security.py`, `routers/auth.py` |
| 가입·비밀번호 변경 제한 | 가입: IP당 1시간 10번. 비밀번호 변경 실패: 사용자당 5분 10번 | 같음 |
| 토큰 무효화 | 비밀번호를 바꾸면 `token_version`이 올라가서 다른 기기의 토큰이 모두 무효가 된다 | `deps.py` |
| 담당 아닌 데이터 | 다른 보호자의 어르신은 존재 여부도 알 수 없게 404 | `deps.py` |
| 권한 상승 방지 | 가입 요청에 `role` 등 정의되지 않은 필드를 넣으면 422 | `schemas.py` (`extra="forbid"`) |
| 입력 검증 | 앞뒤 공백 제거, 글자 수·숫자 범위 상한, 전화번호 형식, 미래 날짜 거절, 조회 기간 최대 366일 | `schemas.py`, `routers/records.py` |
| 보안 헤더 | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, https일 때 HSTS | `http.py` |
| 본문 크기 제한 | 512KB 초과 요청은 413 | `http.py` |
| 에러 정보 숨김 | 예상치 못한 오류는 "서버 내부 오류" 메시지만 응답하고, 상세 내용은 서버 로그에만 남긴다 | `http.py` |
| 운영 설정 검사 | `APP_ENV=production`인데 SECRET_KEY가 기본값이거나 32자 미만이면 서버가 시작하지 않는다. `/docs`도 꺼진다 | `config.py` |
| 프록시 IP | `TRUST_PROXY=true`일 때만 `X-Forwarded-For`의 **마지막** 값(프록시가 붙인 값)을 믿는다 | `http.py` |
| 화면 | 401이나 토큰 만료 시 자동 로그아웃. 로그아웃하면 저장값 삭제 | `api.ts`, `auth.tsx` |

**아직 없는 것** (운영 배포 전에 검토): HTTPS 설정(nginx), 요청 제한의 Redis 이전(서버 여러 대일 때), CSP 헤더, 감사 로그, 계정 잠금 해제 기능.

---

## 설계 결정과 이유

작업을 이어받는 사람이 "왜 이렇게 했지?" 싶을 만한 부분을 정리했다.

| 결정 | 이유 |
|---|---|
| 기록 저장을 `PUT /records/{날짜}` 하나로 처리 (upsert) | 센서나 입력 화면이 하루 기록을 반복해서 보내도 중복 없이 하루 1건이 유지된다. **보내지 않은 필드는 null로 덮어써진다.** 그래서 수정 화면은 기존 값을 전부 채워서 보낸다 |
| `hourly_activity`를 24칸 배열로 저장 | 계획서의 "평소 식사 시간에 활동 없음", "장시간 움직임 없음"은 하루 합계만으로는 판단할 수 없다 |
| 담당이 아닌 어르신을 요청하면 403이 아니라 **404** | 다른 보호자에게 어르신이 존재하는지조차 알려주지 않기 위해서다 (개인정보 보호) |
| 관리자 계정은 회원가입으로 만들 수 없음 | 누구나 관리자가 되는 것을 막는다. 관리자는 seed나 DB에서 직접 만든다 |
| 보호자가 어르신을 등록하면 자동 연결 | 보호자가 부모님을 직접 등록하는 흐름이 자연스럽다 |
| JSON 컬럼은 PostgreSQL 전용 JSONB 대신 범용 `JSON` | 테스트를 SQLite 메모리 DB로 돌리기 위해서다 |
| enum은 DB에 문자열 값(`guardian`)으로 저장 | DB를 직접 볼 때 읽기 쉽고, PostgreSQL enum 타입의 마이그레이션 문제를 피한다 |
| 마이그레이션 도구(Alembic) 없이 시작할 때 `create_all` | 초기 개발 속도를 위해서다. **이미 있는 테이블은 바뀌지 않으므로** 모델을 바꾸면 DB를 초기화해야 한다. 실제 데이터가 쌓이기 시작하면 Alembic을 도입한다 |
| 가상 데이터는 `random.Random(42)` 고정 시드 | 누가 seed를 돌려도 같은 데이터가 나와서, AI 결과를 비교·재현할 수 있다 |
| 카메라 없이 센서·생활 데이터만 수집 | 계획서 6장 개인정보 보호 방안 |

---

## 테스트와 코드 검사

커밋 전에 아래가 모두 통과해야 한다. GitHub Actions(`.github/workflows/ci.yml`)도 push·PR마다 같은 것을 돌린다.

```bash
# 백엔드 — Docker 불필요 (SQLite 메모리 DB)
cd backend
uv run ruff check . && uv run ruff format --check .   # 코드 검사 (자동 수정: ruff check --fix . && ruff format .)
uv run pytest --cov                                   # 단위 테스트 + 커버리지 (90% 미만이면 실패)
uv run pytest -m e2e                                  # 브라우저 e2e 테스트 (약 15초)

# 프론트엔드
cd frontend
npm run lint                                          # ESLint
npm run build                                         # 타입 검사 + 빌드
```

### 단위 테스트 (`backend/tests/`)
- 파일: `test_auth.py`(가입·로그인·시도 제한·토큰), `test_seniors.py`(권한·수정·삭제·보호자 연결), `test_records.py`(저장·조회·검증), `test_http.py`(보안 헤더·에러 형식·설정 검사)
- 테스트 이름은 기대 결과를 한국어 문장으로 쓴다. 예: `test_담당이_아니면_404`
- 공통 fixture(`conftest.py`): `guardian`, `other_guardian`, `admin`은 로그인된 헤더를 돌려준다. 테스트마다 DB와 요청 제한 카운터를 초기화한다.
- 날짜는 `dt.date.today()` 기준으로 만든다. 고정 날짜는 1년이 지나면 조회 기간(366일)에서 벗어나 테스트가 깨진다.
- **새 API를 만들면 테스트도 같이 추가한다.** 권한 확인(다른 보호자가 접근하면 404가 나는지)을 꼭 넣는다.

### e2e 테스트 (`backend/tests/e2e/`)
- Playwright(Chromium)로 실제 화면을 조작한다. 테스트 전용 백엔드(포트 8765, 임시 SQLite + seed)와 빌드된 프론트엔드(포트 4174)를 직접 띄우므로 **개발 서버·DB에 영향이 없다.**
- 확인 내용: 로그인 실패 안내, 관리자·보호자 화면 차이, 기록 입력과 덮어쓰기 확인, 칸별 에러, 작성 중 이탈 경고, 어르신 등록·삭제, 보호자 연결·해제, 회원가입 규칙, 토큰 만료 시 자동 로그아웃, 로그아웃 시 저장값 삭제
- 각 테스트가 끝날 때 화면을 `backend/e2e-screenshots/`에 저장한다(git 제외). CI에서 실패하면 Actions 화면에서 캡처를 내려받을 수 있다.
- 화면을 바꾸면 e2e 테스트의 선택자(버튼 이름, 라벨)도 같이 확인한다.

---

## Git 작업 규칙

- 기본 브랜치는 `main`이다. 기능 단위로 브랜치를 만든다(예: `feat/baseline`, `fix/record-form`). 작업이 끝나면 PR을 올리거나 main에 병합한다.
- 커밋하기 전에 [테스트와 코드 검사](#테스트와-코드-검사)가 모두 통과하는지 확인한다. push하면 GitHub Actions가 다시 확인한다.
- **올리면 안 되는 것**: `backend/.env`(비밀키), `*.db`, `node_modules/`, `.venv/`, 계획 보고서(`*.docx`). 모두 `.gitignore`에 들어 있다.
- 줄바꿈은 LF로 통일한다(`.gitattributes`). Windows에서 작업해도 자동으로 맞춰진다.
- **공개 저장소**이므로 실제 어르신 정보, 실제 비밀번호, API 키는 절대 커밋하지 않는다. 테스트에는 가상 데이터만 쓴다.

---

## 알려진 문제와 주의사항

- **`fastapi dev`가 코드 변경을 반영하지 않는 문제 (Windows)**
  - 원인: 자동 재시작이 멈추면서, 이전 서버 프로세스가 8000 포트를 잡은 채로 남는다. 그래서 새 서버를 켜도 **옛 코드가 응답한다.**
  - 확인: `netstat -ano | findstr :8000`에서 LISTENING이 2줄 나온다.
  - 해결: 두 PID를 모두 종료한 뒤 서버를 다시 실행한다. PowerShell에서는 `Stop-Process -Id <PID> -Force`로 종료한다. PID가 이미 없다고 나오면, 그 PID를 부모로 둔 자식 python 프로세스를 종료한다.
- **Git Bash에서 curl로 한글 JSON을 보내면 400 에러가 난다.** 한글이 UTF-8로 전달되지 않기 때문이다. 한글이 들어간 API 테스트는 `/docs` 화면이나 Python 스크립트로 한다.
- **모델을 바꾸면 DB를 초기화해야 한다** (위의 [DB 초기화](#db-초기화) 참고). `create_all`은 이미 있는 테이블의 컬럼을 바꾸지 않는다.
  - 데이터를 지우기 싫으면 컬럼만 직접 추가한다. 2026-09-30에 추가된 컬럼 예:
    `docker exec lifeguard-db psql -U lifeguard -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;"`
- **`SECRET_KEY`**: 기본값은 개발용이다. 운영(`APP_ENV=production`)에서는 32자 이상 랜덤 문자열이 아니면 서버가 시작하지 않는다.
- **TypeScript는 6.0으로 고정**했다. TypeScript 7이 나왔지만 ESLint용 `typescript-eslint`가 아직 6.0까지만 지원한다. 지원이 되면 올린다.
- **요청 제한(로그인 잠금 등)은 서버 메모리에 저장**된다. 서버를 재시작하면 초기화되고, 서버를 여러 대로 늘리면 각자 따로 센다. 그때는 Redis로 옮겨야 한다.
- 본문 크기 제한은 `Content-Length` 헤더 기준이다. 헤더 없이 조각(chunked)으로 보내는 요청은 운영 환경의 nginx(`client_max_body_size`)에서 막는다.
- **SQLite 파일 DB 모드**(`sqlite:///./dev.db`)에서 동시 요청이 엉키는 버그가 있었다. 연결 하나를 여러 스레드가 같이 쓴 탓이었고, 2026-09-30에 수정했다(`database.py`). 메모리 DB만 연결을 공유한다.
- seed의 가상 기록은 **seed를 실행한 날 기준 어제까지** 만들어진다. 며칠 지나면 목록에 "N일 전"과 "최근 기록 없음"이 뜨는 것은 정상이다. 최신으로 맞추려면 DB를 초기화하고 seed를 다시 실행한다.
- 나이는 `올해 - 출생연도`로 계산한다. 생일이 지나기 전이면 만 나이보다 1살 많게 보일 수 있다.

---

