# LifeGuard AI

AI를 활용한 독거노인 생활 안전 관리 서비스.
어르신의 평소 생활 패턴을 기록·분석하고, 평소와 다른 변화가 보이면 보호자에게 먼저 알려준다.
사고가 난 뒤에 대응하는 방식이 아니라, 위험 가능성을 미리 감지하는 것이 목표다.

- 기획 문서: `LifeGuard_AI_프로젝트_계획_보고서.docx`는 목표, 기능, 월별 일정의 원본이다. **저장소에는 올리지 않았으니** 필요하면 담당자에게 받는다. 이 README의 일정과 다음 작업은 보고서 내용을 기준으로 정리했다.
- 저장소: https://github.com/chldbswlsl/lifeguard-ai (공개)
- **이 README는 인수인계 문서다.** 작업을 하면 반드시 [작업 로그](#작업-로그)와 [다음 작업](#다음-작업)을 갱신한다.

---

## 목차

1. [현재 상태 한눈에 보기](#현재-상태-한눈에-보기)
2. [일정](#일정)
3. [처음 세팅하기](#처음-세팅하기)
4. [매일 개발 시작하기](#매일-개발-시작하기)
5. [폴더 구조](#폴더-구조)
6. [데이터 모델](#데이터-모델)
7. [API](#api)
8. [프론트엔드 구조](#프론트엔드-구조)
9. [설계 결정과 이유](#설계-결정과-이유)
10. [테스트](#테스트)
11. [다음 작업](#다음-작업)
12. [Git 작업 규칙](#git-작업-규칙)
13. [알려진 문제와 주의사항](#알려진-문제와-주의사항)
14. [작업 로그](#작업-로그)

---

## 현재 상태 한눈에 보기

> 마지막 갱신: 2026-09-30

| 영역 | 상태 |
|---|---|
| 백엔드 (FastAPI + PostgreSQL) | ✅ 회원가입·로그인, 내 정보 관리, 어르신 CRUD, 보호자 연결, 생활 기록 저장·조회 |
| 가상 데이터 | ✅ 평소 하루 생성기, seed 스크립트 (어르신 3명 × 28일) — ⬜ 이상 상황 시나리오는 아직 |
| 웹 (React) | ✅ 로그인·회원가입, 관리자 페이지(어르신 목록·현황), 어르신 상세·생활 기록 입력, 내 정보 |
| AI 분석 | ⬜ 시작 전 (10월 작업) |
| 알림 | ⬜ 시작 전 (11월 작업) |
| 테스트 | ✅ 백엔드 pytest 20개 통과 / 프론트엔드는 타입 검사·빌드만 통과 (자동 테스트 없음) |

---

## 일정

원래 계획은 8월 설계, 9월 기본 개발이었지만 **일정이 바뀌어 2026-09-30에 개발을 시작했다.**
최종 마감은 **12월 그대로**라서 10월에는 AI 기능을 곧바로 시작해야 한다.

| 월 | 계획서 내용 | 상태 |
|---|---|---|
| 8월 | 아이디어 구체화, 기초 설계 | ✅ (계획서) |
| 9월 | 회원가입·로그인, 사용자 정보 관리, 생활 데이터 입력, DB 연결, 기본 관리자 페이지 | ✅ 9/30 하루에 완료 |
| 10월 | 생활 패턴 분석, 평균 패턴 계산, 이상 행동 탐지, 위험도 계산, 테스트 데이터 생성·검증 | ⬜ 다음 |
| 11월 | 보호자 화면·위험도 화면, 알림 연결, 생활 패턴 그래프, 관리자 페이지 개선, 전체 테스트 | ⬜ |
| 12월 | 오류 수정, AI 결과 검증, 발표 자료, 시연 시나리오 | ⬜ |

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
├── backend/                   # FastAPI 서버
│   ├── pyproject.toml         # 의존성 (uv)
│   ├── .env.example           # 환경변수 예시 → .env로 복사해서 사용 (.env는 git 제외)
│   ├── app/
│   │   ├── main.py            # 앱 생성, CORS, 라우터 등록, 시작 시 테이블 생성
│   │   ├── config.py          # 환경변수 (DATABASE_URL, SECRET_KEY, …)
│   │   ├── database.py        # SQLAlchemy 엔진·세션, get_db
│   │   ├── models.py          # DB 테이블 정의
│   │   ├── schemas.py         # 요청/응답 형식 (Pydantic) + 입력 검증
│   │   ├── security.py        # 비밀번호 해시(argon2), JWT 발급·검증
│   │   ├── deps.py            # 로그인 사용자, 관리자 확인, 어르신 접근 권한 확인
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth — 가입, 로그인, 내 정보, 비밀번호 변경
│   │   │   ├── seniors.py     # /seniors — 어르신 CRUD, 목록 요약, 보호자 연결
│   │   │   └── records.py     # /seniors/{id}/records — 생활 기록
│   │   ├── simulate.py        # 가상 생활 데이터 생성기 (LifeProfile → 하루 기록)
│   │   └── seed.py            # 개발용 초기 데이터
│   └── tests/                 # pytest (SQLite 메모리 DB 사용, Docker 불필요)
└── frontend/                  # React 웹 (Vite + TypeScript)
    ├── vite.config.ts         # /api → localhost:8000 프록시
    └── src/
        ├── main.tsx           # 진입점
        ├── App.tsx            # 라우팅, 로그인 필요 화면의 공통 레이아웃(상단 메뉴)
        ├── api.ts             # 백엔드 호출 함수 + 응답 타입 (API가 바뀌면 여기부터 수정)
        ├── auth.tsx           # 로그인 상태 (토큰은 localStorage에 저장)
        ├── format.ts          # 날짜·시간·숫자 표시 도우미
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
            └── HourlyBars.tsx        # 시간대별 활동량 막대 24개
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
| POST | `/auth/me/password` | 로그인 | 비밀번호 변경 (현재 비밀번호 필요) |
| GET | `/seniors` | 로그인 | 어르신 목록 + 최근 기록 요약(`last_record_date`, `last_activity_level`, `guardian_count`). 보호자는 담당 어르신만 |
| POST | `/seniors` | 로그인 | 어르신 등록. 보호자가 등록하면 자동으로 본인과 연결 |
| GET | `/seniors/{id}` | 담당·관리자 | 어르신 조회 |
| PATCH | `/seniors/{id}` | 담당·관리자 | 어르신 수정 (보낸 필드만 바뀜) |
| DELETE | `/seniors/{id}` | 관리자 | 어르신과 모든 기록 삭제 |
| GET | `/seniors/{id}/guardians` | 담당·관리자 | 담당 보호자 목록 |
| POST | `/seniors/{id}/guardians` | 관리자 | 가입된 보호자를 이메일로 연결 |
| GET | `/seniors/{id}/records?start=&end=` | 담당·관리자 | 기간 조회 (양 끝 포함, 날짜 오름차순) |
| PUT | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 그날 기록 저장. 새로 만들면 201, 있으면 **전체 덮어쓰기** 후 200 |
| GET | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 하루 기록 |
| DELETE | `/seniors/{id}/records/{YYYY-MM-DD}` | 담당·관리자 | 하루 기록 삭제 |
| GET | `/health` | 누구나 | 서버 상태 확인 |

에러 응답은 FastAPI 기본 형식이다. `{"detail": "한글 메시지"}` 또는 입력 검증 실패 시 `{"detail": [{loc, msg}, …]}`(422)로 온다. 프론트엔드의 `api.ts`의 `errorMessage()`가 두 형식을 모두 처리한다.

---

## 프론트엔드 구조

| 경로 | 화면 | 누가 |
|---|---|---|
| `/login`, `/signup` | 로그인, 보호자 회원가입 | 누구나 |
| `/` | 어르신 목록. 관리자에게는 현황 카드(등록 수, 2일 이상 기록 없음, 보호자 미연결)가 보인다 | 로그인 |
| `/seniors/:id` | 기본 정보, 보호자(관리자는 연결 가능), 최근 28일 생활 기록 표, 기록 입력·수정·삭제 | 담당·관리자 |
| `/me` | 내 정보 수정, 비밀번호 변경 | 로그인 |

- **새 API를 쓰려면** `src/api.ts`에 타입과 함수를 추가하고, 화면에서는 `api.xxx()`로 호출한다. 화면 코드에서 fetch를 직접 쓰지 않는다.
- 로그인 토큰은 `localStorage`의 `lifeguard_token`에 저장된다. 만료 기간은 24시간이다(`ACCESS_TOKEN_EXPIRE_MINUTES`).
- 별도 UI 라이브러리 없이 `index.css` 하나로 스타일을 관리한다. 색은 `:root`의 변수로 정의되어 있다.
- 목록의 **위험도** 칸은 지금 "분석 준비 중"이라고만 표시한다. 10월 AI 작업이 끝나면 실제 값으로 바꾼다(`SeniorListPage.tsx`).

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

## 테스트

```bash
cd backend && uv run pytest          # 백엔드 (Docker 불필요, SQLite 메모리 DB)
cd frontend && npm run build         # 프론트엔드 타입 검사 + 빌드
```

- 테스트 파일: `tests/test_auth.py`, `tests/test_seniors.py`, `tests/test_records.py`
- 공통 fixture는 `tests/conftest.py`에 있다. `guardian`, `other_guardian`, `admin`은 각각 로그인된 헤더를 돌려준다. 테스트마다 DB를 새로 만든다.
- **새 API를 만들면 테스트도 같이 추가한다.** 권한 확인(다른 보호자가 접근하면 404가 나는지)을 꼭 넣는다.
- 프론트엔드 자동 테스트는 아직 없다. 화면을 바꾸면 브라우저에서 관리자·보호자 계정으로 각각 직접 확인한다.

---

## 다음 작업

### 10월 — AI 기능 (우선순위 순)

1. **이상 상황 시나리오 만들기** — `backend/app/simulate.py`
   - `generate_normal_day()` 옆에 이상한 하루를 만드는 함수를 추가한다. 계획서 4-3의 이상 징후 기준으로 만든다.
     - 활동량 감소 (예: 평소의 40~60%)
     - 식사 거름 (식사 시간대에 활동 없음, `meal_count` 감소)
     - 장시간 무활동 (낮 시간 연속 N시간 동안 `hourly_activity`가 0)
     - 여러 개가 동시에 발생
   - 시연용 시나리오를 seed에 추가한다. 예: "C 어르신은 최근 3일간 활동량이 점점 줄어듦"
2. **평소 패턴(baseline) 계산** — 새 파일 `backend/app/analysis.py`
   - 최근 7일(또는 14일) 기록으로 평균·표준편차를 구한다. 대상은 활동량, 기상 시각, 식사 횟수, 시간대별 활동, 외출 시간이다.
   - 기록이 너무 적으면(예: 3일 미만) "판단 불가"로 처리한다.
3. **이상 탐지 + 위험도 점수(0~100)**
   - 항목별로 평소와 얼마나 다른지 계산한다(z-score나 감소율).
   - 여러 징후가 겹치면 가중치를 올린다 (계획서 4-3).
   - 단계는 안전 / 주의 / 위험 3단계다. 경계값은 가상 데이터로 조정한다.
   - **이유 문장을 같이 반환한다.** 예: "최근 활동량이 평소보다 45% 감소했습니다" (계획서 4-4)
4. **분석 API** — 예: `GET /seniors/{id}/risk?date=`, `GET /seniors`에 최신 위험도 포함
   - 결과를 매번 계산할지, `risk_assessments` 테이블에 저장할지 정해야 한다. 알림 기록(11월)을 생각하면 저장하는 쪽을 추천한다.
5. **화면 연결** — 목록의 "분석 준비 중"을 실제 위험도로 바꾸고, 관리자 목록을 **위험도 높은 순**으로 정렬한다 (계획서 4-7)
6. **테스트** — 정상 데이터는 "안전", 시나리오 데이터는 "주의/위험"이 나오는지 pytest로 검증한다 (계획서 9장: 불필요한 알림 최소화)

### 11월 이후 (계획서 기준)
- 보호자용 화면: 위험도, 오늘 활동량, 평소 대비 그래프
- 알림 기능: 위험도가 기준을 넘으면 보호자에게 알림을 보낸다 (방식 미정: 웹 알림, 이메일, 카카오 알림톡 등). 알림 기록도 남긴다.
- 관리자 페이지 개선
- 12월 시연 시나리오: 정상 → 활동량 감소(주의) → 장시간 무활동 + 식사 없음(위험) → 보호자 알림

### 정리하면 좋은 것 (급하지 않음)
- GitHub Actions로 push할 때 pytest와 `npm run build` 자동 실행
- Alembic 마이그레이션 도입 (실제 데이터가 쌓이기 전에)
- 보호자 연결 해제 API (지금은 연결만 가능)
- 기록 목록 화면에 기간 선택 기능 (지금은 최근 28일 고정)

---

## Git 작업 규칙

- 기본 브랜치는 `main`이다. 기능 단위로 브랜치를 만든다(예: `feat/baseline`, `fix/record-form`). 작업이 끝나면 PR을 올리거나 main에 병합한다.
- 커밋하기 전에 `uv run pytest`와 `npm run build`가 통과하는지 확인한다.
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
- **`SECRET_KEY`**: 기본값은 개발용이다. 실제로 배포할 때는 `.env`에 긴 랜덤 문자열을 넣는다.
- seed의 가상 기록은 **seed를 실행한 날 기준 어제까지** 만들어진다. 며칠 지나면 목록에 "N일 전"과 "최근 기록 없음"이 뜨는 것은 정상이다. 최신으로 맞추려면 DB를 초기화하고 seed를 다시 실행한다.
- 나이는 `올해 - 출생연도`로 계산한다. 생일이 지나기 전이면 만 나이보다 1살 많게 보일 수 있다.

---

## 작업 로그

새 작업은 **맨 위에** 추가한다. 형식: 날짜 — 한 일 / 결정 / 남은 문제.

### 2026-09-30 — 개발 시작, 9월 분량 완료
- **환경**: FastAPI + SQLAlchemy 2 + PostgreSQL 17(Docker) / React 19 + Vite 8 + TypeScript 7 + react-router 8. Python 패키지는 uv로 관리한다.
- **백엔드**
  - 모델: users, seniors, guardian_senior, daily_records
  - 인증: 회원가입, 로그인(JWT), 내 정보 조회·수정, 비밀번호 변경
  - 어르신: CRUD, 보호자 연결(관리자), 목록에 최근 기록 요약 포함
  - 생활 기록: 날짜별 저장(upsert), 기간 조회, 삭제
  - 가상 데이터 생성기(`simulate.py`), seed 스크립트
  - pytest 20개 (인증, 권한, 기록 저장·검증, 가상 데이터 저장)
- **프론트엔드**: 로그인·회원가입, 어르신 목록(관리자 현황 카드), 어르신 상세(정보 수정, 보호자 연결, 28일 기록 표, 시간대별 활동 막대), 생활 기록 입력·수정·삭제, 내 정보
- **검증**: PostgreSQL에서 seed와 API 흐름(가입→로그인→등록→기록 입력·수정·삭제→내 정보 수정→비밀번호 변경)을 프록시 경유로 확인했다. 프론트엔드는 `npm run build`(타입 검사)를 통과했다. **브라우저에서 화면을 직접 눌러보는 확인은 아직 하지 않았다.**
- **결정**: 위의 [설계 결정과 이유](#설계-결정과-이유) 참고
- **GitHub**: 공개 저장소 `chldbswlsl/lifeguard-ai`를 만들고 첫 커밋을 올렸다. 계획 보고서(.docx)는 제외했다.
- **남은 문제**: 목록의 위험도 칸은 임시 표시다. 브라우저에서 화면을 직접 확인하지 않았다.
