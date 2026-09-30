import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, errorMessage, type DailyRecord, type Senior, type User } from "../api";
import { useUser } from "../auth";
import { useDialog } from "../components/Dialog";
import HourlyBars from "../components/HourlyBars";
import RecordForm from "../components/RecordForm";
import SeniorForm from "../components/SeniorForm";
import { age, daysAgo, hhmm, num, SOURCE_LABEL } from "../format";

const RANGE_DAYS = 28;

/** 주소의 id가 바뀌면 key로 화면 상태를 통째로 새로 만든다 (이전 어르신 데이터가 잠깐 보이지 않게). */
export default function SeniorDetailRoute() {
  const raw = useParams().id ?? "";
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) {
    return (
      <div className="card empty">
        <p className="error">잘못된 주소입니다</p>
        <Link to="/">← 목록으로</Link>
      </div>
    );
  }
  return <SeniorDetailPage key={id} id={id} />;
}

function SeniorDetailPage({ id }: { id: number }) {
  const isAdmin = useUser().role === "admin";
  const navigate = useNavigate();
  const { confirmDialog, toast } = useDialog();

  const [senior, setSenior] = useState<Senior | null>(null);
  const [guardians, setGuardians] = useState<User[]>([]);
  const [records, setRecords] = useState<DailyRecord[]>([]);
  const [error, setError] = useState("");
  const [editingInfo, setEditingInfo] = useState(false);
  // null: 폼 닫힘, "new": 새 기록, DailyRecord: 해당 기록 수정
  const [recordForm, setRecordForm] = useState<null | "new" | DailyRecord>(null);

  const loadRecords = useCallback(
    () => api.listRecords(id, daysAgo(RANGE_DAYS - 1), daysAgo(-1)).then((rs) => rs.reverse()), // 최신이 위로
    [id],
  );

  useEffect(() => {
    let cancelled = false; // 화면을 떠난 뒤 도착한 응답은 무시한다
    Promise.all([api.getSenior(id), api.listGuardians(id), loadRecords()])
      .then(([s, g, rs]) => {
        if (cancelled) return;
        setSenior(s);
        setGuardians(g);
        setRecords(rs);
      })
      .catch((e) => !cancelled && setError(errorMessage(e)));
    return () => {
      cancelled = true;
    };
  }, [id, loadRecords]);

  async function reloadRecords() {
    try {
      setRecords(await loadRecords());
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  }

  if (error) {
    return (
      <div className="card empty">
        <p className="error">{error}</p>
        <Link to="/">← 목록으로</Link>
      </div>
    );
  }
  if (!senior) return <p className="muted">불러오는 중…</p>;

  const maxHourly = Math.max(0, ...records.flatMap((r) => r.hourly_activity ?? []));

  async function remove() {
    const ok = await confirmDialog({
      title: `${senior!.name} 님을 삭제할까요?`,
      message: "어르신 정보와 모든 생활 기록이 삭제되며 되돌릴 수 없습니다.",
      confirmText: "삭제",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteSenior(id);
      toast(`${senior!.name} 님을 삭제했습니다`);
      navigate("/");
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  }

  async function removeRecord(date: string) {
    const ok = await confirmDialog({ title: `${date} 기록을 삭제할까요?`, confirmText: "삭제", danger: true });
    if (!ok) return;
    try {
      await api.deleteRecord(id, date);
      toast(`${date} 기록을 삭제했습니다`);
      await reloadRecords();
    } catch (e) {
      toast(errorMessage(e), "error");
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
            toast("저장했습니다");
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
          <GuardianCard seniorId={id} guardians={guardians} canManage={isAdmin} onChange={setGuardians} />
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
          onSaved={() => {
            setRecordForm(null);
            reloadRecords();
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
                <th>
                  <span className="sr-only">관리</span>
                </th>
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
                    <button className="link" onClick={() => setRecordForm(r)} aria-label={`${r.date} 기록 수정`}>
                      수정
                    </button>
                    <button className="link danger" onClick={() => removeRecord(r.date)} aria-label={`${r.date} 기록 삭제`}>
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
  canManage,
  onChange,
}: {
  seniorId: number;
  guardians: User[];
  canManage: boolean;
  onChange: (g: User[]) => void;
}) {
  const { confirmDialog, toast } = useDialog();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function link(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      onChange(await api.linkGuardian(seniorId, email.trim()));
      setEmail("");
      toast("보호자를 연결했습니다");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function unlink(g: User) {
    const ok = await confirmDialog({
      title: `${g.name} 님의 연결을 해제할까요?`,
      message: "보호자 계정은 그대로 남고, 이 어르신의 정보만 볼 수 없게 됩니다.",
      confirmText: "연결 해제",
      danger: true,
    });
    if (!ok) return;
    try {
      onChange(await api.unlinkGuardian(seniorId, g.id));
      toast("연결을 해제했습니다");
    } catch (err) {
      toast(errorMessage(err), "error");
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
            <li key={g.id} className="guardian-row">
              <span>
                <b>{g.name}</b> <span className="muted">{g.email}</span>
                {g.phone && <span className="muted"> · {g.phone}</span>}
              </span>
              {canManage && (
                <button className="link danger" onClick={() => unlink(g)}>
                  해제
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canManage && (
        <form className="inline-form" onSubmit={link}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="가입된 보호자 이메일"
            aria-label="연결할 보호자 이메일"
            maxLength={255}
            required
          />
          <button disabled={busy}>연결</button>
        </form>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
