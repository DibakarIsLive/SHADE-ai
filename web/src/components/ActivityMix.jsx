import Icon from "./Icon";
import { clamp } from "../utils/formatters";

const colors = {
  mint: "#6ce5c1",
  blue: "#77a9ff",
  violet: "#ad8cff",
  slate: "#71829b",
};

export default function ActivityMix({ data }) {
  if (!data.length) {
    return (
      <div className="empty-state empty-state--mix">
        <span className="empty-state__icon"><Icon name="activity" size={20} /></span>
        <strong>No activity data yet</strong>
        <span>Statistics use saved event records only. The standalone video-file worker is separate from dashboard controls and its development-null provider generates no events.</span>
      </div>
    );
  }

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
        <div className="activity-donut" style={{ background: `conic-gradient(${gradient})` }} aria-label={`${Math.round(total)} percent of the displayed event mix`}>
          <div className="activity-donut__center">
            <strong>{Math.round(total)}%</strong>
            <span>share shown</span>
          </div>
        </div>
      </div>
      <div className="activity-mix__legend">
        {data.map((item) => (
          <div className="activity-legend-row" key={item.label}>
            <div className="activity-legend-row__label">
              <span className={`legend-dot legend-dot--${item.color}`} aria-hidden="true" />
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
