import Icon from "./Icon";

export default function MetricCard({ label, value, detail, icon, tone = "mint", trend }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__topline">
        <span className="metric-card__label">{label}</span>
        <span className="metric-card__icon"><Icon name={icon} size={17} /></span>
      </div>
      <div className="metric-card__value-row">
        <strong>{value}</strong>
        {trend && <span className="metric-card__trend"><Icon name="arrowUp" size={13} /> {trend}</span>}
      </div>
      <span className="metric-card__detail">{detail}</span>
    </article>
  );
}
