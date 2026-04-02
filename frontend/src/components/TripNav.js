import { c, f } from "../styles";

export default function TripNav({ label, totalDays, onBack }) {
  return (
    <nav style={{ position: "sticky", top: 0, zIndex: 10, backgroundColor: c.white, borderBottom: `1px solid ${c.sandBorder}`, padding: "0 40px", height: "56px", display: "flex", alignItems: "center", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <button onClick={onBack} style={{ display: "flex", alignItems: "center", gap: "5px", background: "none", border: "none", color: c.stoneLight, fontSize: "13px", fontFamily: f.sans, cursor: "pointer", padding: 0 }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M9 2L4 7L9 12" stroke={c.stoneLight} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          All trips
        </button>
        <span style={{ color: c.sandBorder }}>|</span>
        <span style={{ fontFamily: f.display, fontSize: "17px", fontWeight: 700, color: c.teal, letterSpacing: "0.01em" }}>{label}</span>
        <span style={{ fontFamily: f.mono, fontSize: "11px", color: c.stoneFaint }}>{totalDays} days</span>
      </div>
    </nav>
  );
}