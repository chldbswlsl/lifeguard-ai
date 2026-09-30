/** 0~23시 시간대별 활동량을 작은 막대 24개로 보여준다. */
export default function HourlyBars({ values, max }: { values: number[] | null; max: number }) {
  if (!values) return <span className="muted">-</span>;
  return (
    <div className="hourly" role="img" aria-label={`0시~23시 움직임: ${values.join(", ")}`}>
      {values.map((v, h) => (
        <span
          key={h}
          title={`${h}시: ${v}`}
          style={{ height: `${Math.max(2, (v / Math.max(max, 1)) * 100)}%` }}
          className={v === 0 ? "zero" : undefined}
        />
      ))}
    </div>
  );
}
