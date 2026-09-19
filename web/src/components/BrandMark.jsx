import Icon from "./Icon";

export default function BrandMark() {
  return (
    <div className="brand-mark">
      <span className="brand-mark__glyph"><Icon name="pulse" size={22} strokeWidth={2.2} /></span>
      <span>
        <strong>SHADE</strong>
        <small>activity intelligence</small>
      </span>
    </div>
  );
}
