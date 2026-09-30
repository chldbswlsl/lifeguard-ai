import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { api, type SeniorListItem } from "../api";
import { useAuth } from "../auth";
import SeniorForm from "../components/SeniorForm";
import { age, daysSince, num } from "../format";

export default function SeniorListPage() {
  const { user } = useAuth();
  const isAdmin = user!.role === "admin";
  const navigate = useNavigate();
  const [seniors, setSeniors] = useState<SeniorListItem[] | null>(null);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  const load = () =>
    api
      .listSeniors()
      .then(setSeniors)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!seniors) return <p className="muted">불러오는 중…</p>;

  const stale = seniors.filter((s) => !s.last_record_date || daysSince(s.last_record_date) > 1).length;
  const noGuardian = seniors.filter((s) => s.guardian_count === 0).length;

  return (
    <>
      <div className="page-head">
        <h1>{isAdmin ? "전체 어르신 관리" : "담당 어르신"}</h1>
        {!adding && (
          <button className="primary" onClick={() => setAdding(true)}>
            + 어르신 등록
          </button>
        )}
      </div>

      {isAdmin && (
        <div className="stats">
          <Stat label="등록된 어르신" value={`${seniors.length}명`} />
          <Stat label="최근 기록 없음 (2일 이상)" value={`${stale}명`} warn={stale > 0} />
          <Stat label="보호자 미연결" value={`${noGuardian}명`} warn={noGuardian > 0} />
        </div>
      )}

      {adding && (
        <SeniorForm
          submitLabel="등록"
          onCancel={() => setAdding(false)}
          onSubmit={async (data) => {
            const created = await api.createSenior(data);
            navigate(`/seniors/${created.id}`);
          }}
        />
      )}

      {seniors.length === 0 ? (
        <div className="card empty">
          등록된 어르신이 없습니다. <b>+ 어르신 등록</b>으로 시작하세요.
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="table clickable">
            <thead>
              <tr>
                <th>이름</th>
                <th>나이</th>
                <th>위험도</th>
                <th>최근 기록</th>
                <th className="num">최근 활동량</th>
                {isAdmin && <th className="num">보호자</th>}
              </tr>
            </thead>
            <tbody>
              {seniors.map((s) => (
                <tr key={s.id} onClick={() => navigate(`/seniors/${s.id}`)}>
                  <td>
                    <b>{s.name}</b>
                  </td>
                  <td>{age(s.birth_year)}</td>
                  <td>
                    {/* 10월 AI 위험도 분석이 붙으면 안전/주의/위험으로 바뀐다 */}
                    <span className="chip pending">분석 준비 중</span>
                  </td>
                  <td>
                    <LastRecord date={s.last_record_date} />
                  </td>
                  <td className="num">{num(s.last_activity_level)}</td>
                  {isAdmin && (
                    <td className={`num ${s.guardian_count === 0 ? "warn-text" : ""}`}>{s.guardian_count}명</td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Stat({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`card stat ${warn ? "warn" : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function LastRecord({ date }: { date: string | null }) {
  if (!date) return <span className="warn-text">기록 없음</span>;
  const d = daysSince(date);
  const text = d <= 0 ? "오늘" : d === 1 ? "어제" : `${d}일 전`;
  return <span className={d > 1 ? "warn-text" : undefined}>{text}</span>;
}
