import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, type DailyRecord, type Senior, type User } from "../api";
import { useAuth } from "../auth";
import HourlyBars from "../components/HourlyBars";
import RecordForm from "../components/RecordForm";
import SeniorForm from "../components/SeniorForm";
import { age, daysAgo, hhmm, num, SOURCE_LABEL } from "../format";

const RANGE_DAYS = 28;

export default function SeniorDetailPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const isAdmin = user!.role === "admin";
  const navigate = useNavigate();

  const [senior, setSenior] = useState<Senior | null>(null);
  const [guardians, setGuardians] = useState<User[]>([]);
  const [records, setRecords] = useState<DailyRecord[]>([]);
  const [error, setError] = useState("");
  const [editingInfo, setEditingInfo] = useState(false);
  // null: 폼 닫힘, "new": 새 기록, DailyRecord: 해당 기록 수정
  const [recordForm, setRecordForm] = useState<null | "new" | DailyRecord>(null);

  const loadRecords = () =>
    api.listRecords(id, daysAgo(RANGE_DAYS - 1)).then((rs) => setRecords(rs.reverse())); // 최신이 위로

  useEffect(() => {
    Promise.all([api.getSenior(id), api.listGuardians(id), loadRecords()])
      .then(([s, g]) => {
        setSenior(s);
        setGuardians(g);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <>
        <p className="error">{error}</p>
        <Link to="/">← 목록으로</Link>
      </>
    );
  }
  if (!senior) return <p className="muted">불러오는 중…</p>;

  const maxHourly = Math.max(0, ...records.flatMap((r) => r.hourly_activity ?? []));

  async function remove() {
    if (!confirm(`${senior!.name} 님의 정보와 모든 생활 기록을 삭제할까요? 되돌릴 수 없습니다.`)) return;
    try {
      await api.deleteSenior(id);
      navigate("/");
    } catch (e) {
      alert((e as Error).message);
    }
  }

  async function removeRecord(date: string) {
    if (!confirm(`${date} 기록을 삭제할까요?`)) return;
    try {
      await api.deleteRecord(id, date);
      await loadRecords();
    } catch (e) {
      alert((e as Error).message);
    }
  }

  return (
    <>
      <Link to="/" className="back">
        ← 목록으로
      </Link>
      <div className="page-head">
        <h1>
          {senior.name} <span className="muted">{age(senior.birth_year)}</span>
        </h1>
        {!editingInfo && (
          <div className="actions">
            <button onClick={() => setEditingInfo(true)}>정보 수정</button>
            {isAdmin && (
              <button className="danger" onClick={remove}>
                삭제
              </button>
            )}
          </div>
        )}
      </div>

      {editingInfo ? (
        <SeniorForm
          initial={senior}
          submitLabel="저장"
          onCancel={() => setEditingInfo(false)}
          onSubmit={async (data) => {
            setSenior(await api.updateSenior(id, data));
            setEditingInfo(false);
          }}
        />
      ) : (
        <div className="grid-2">
          <div className="card">
            <h2>기본 정보</h2>
            <dl className="info">
              <dt>출생연도</dt>
              <dd>{senior.birth_year ?? "-"}</dd>
              <dt>연락처</dt>
              <dd>{senior.phone ?? "-"}</dd>
              <dt>주소</dt>
              <dd>{senior.address ?? "-"}</dd>
              <dt>메모</dt>
              <dd className="pre">{senior.notes ?? "-"}</dd>
            </dl>
          </div>
          <GuardianCard seniorId={id} guardians={guardians} canLink={isAdmin} onChange={setGuardians} />
        </div>
      )}

      <div className="page-head section">
        <h2>
          생활 기록 <span className="muted">최근 {RANGE_DAYS}일 · {records.length}건</span>
        </h2>
        {!recordForm && (
          <button className="primary" onClick={() => setRecordForm("new")}>
            + 기록 입력
          </button>
        )}
      </div>

      {recordForm && (
        <RecordForm
          key={recordForm === "new" ? "new" : recordForm.date}
          seniorId={id}
          initial={recordForm === "new" ? undefined : recordForm}
          existingDates={new Set(records.map((r) => r.date))}
          onCancel={() => setRecordForm(null)}
          onSaved={async () => {
            setRecordForm(null);
            await loadRecords();
          }}
        />
      )}

      {records.length === 0 ? (
        <div className="card empty">최근 {RANGE_DAYS}일 동안의 기록이 없습니다.</div>
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>날짜</th>
                <th>기상</th>
                <th>취침</th>
                <th className="num">활동량</th>
                <th>시간대별 활동 (0~23시)</th>
                <th>식사</th>
                <th className="num">외출</th>
                <th className="num">기기</th>
                <th>입력</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="nowrap">{r.date}</td>
                  <td>{hhmm(r.wake_time)}</td>
                  <td>{hhmm(r.sleep_time)}</td>
                  <td className="num">{num(r.activity_level)}</td>
                  <td>
                    <HourlyBars values={r.hourly_activity} max={maxHourly} />
                  </td>
                  <td className="nowrap" title={r.meal_times?.map(hhmm).join(", ")}>
                    {r.meal_count !== null ? `${r.meal_count}회` : "-"}
                  </td>
                  <td className="num">{num(r.outing_minutes, "분")}</td>
                  <td className="num">{num(r.appliance_usage, "회")}</td>
                  <td>
                    <span className={`chip ${r.source}`}>{SOURCE_LABEL[r.source]}</span>
                  </td>
                  <td className="nowrap">
                    <button className="link" onClick={() => setRecordForm(r)}>
                      수정
                    </button>
                    <button className="link danger" onClick={() => removeRecord(r.date)}>
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function GuardianCard({
  seniorId,
  guardians,
  canLink,
  onChange,
}: {
  seniorId: number;
  guardians: User[];
  canLink: boolean;
  onChange: (g: User[]) => void;
}) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  async function link(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      onChange(await api.linkGuardian(seniorId, email));
      setEmail("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="card">
      <h2>보호자</h2>
      {guardians.length === 0 ? (
        <p className="warn-text">연결된 보호자가 없습니다</p>
      ) : (
        <ul className="plain">
          {guardians.map((g) => (
            <li key={g.id}>
              <b>{g.name}</b> <span className="muted">{g.email}</span>
              {g.phone && <span className="muted"> · {g.phone}</span>}
            </li>
          ))}
        </ul>
      )}
      {canLink && (
        <form className="inline-form" onSubmit={link}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="가입된 보호자 이메일"
            required
          />
          <button>연결</button>
        </form>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
