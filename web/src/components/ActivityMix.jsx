import { clamp } from "../utils/formatters";

const colors = {
  mint: "#6ce5c1",
  blue: "#77a9ff",
  violet: "#ad8cff",
  slate: "#71829b",
};

export default function ActivityMix({ data }) {
  const total = data.reduce((sum, item) => sum + item.value, 0) || 1;
  const segments = data.reduce((result, item) => {
    const start = result.at(-1)?.end || 0;
    const end = start + (item.value / total) * 100;
    result.push({ ...item, start, end });
    return result;
  }, []);

  const gradient = segments
    .map((item) => `${colors[item.color] || colors.slate} ${item.start}% ${item.end}%`)
    .join(", ");

  return (
    <div className="activity-mix">
      <div className="activity-mix__visual">
        <div className="activity-donut" style={{ background: `conic-gradient(${gradient})` }}>
          <div className="activity-donut__center">
            <strong>{total}%</strong>
            <span>observed</span>
          </div>
        </div>
      </div>
      <div className="activity-mix__legend">
        {data.map((item) => (
          <div className="activity-legend-row" key={item.label}>
            <div className="activity-legend-row__label">
              <span className={`legend-dot legend-dot--${item.color}`} />
              <span>{item.label}</span>
            </div>
            <div className="activity-legend-row__value">
              <div className="activity-bar"><span style={{ width: `${clamp(item.value / 100, 0, 1) * 100}%` }} /></div>
              <strong>{item.value}%</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
