import ReactMarkdown from "react-markdown";
import { c, f } from "../styles";

const mdComponents = {
  h2: ({ children }) => (
    <h2 style={{ fontFamily: f.display, fontSize: "22px", fontWeight: 700, color: c.stone, margin: "0 0 14px", letterSpacing: "0.01em" }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ fontFamily: f.sans, fontSize: "10px", fontWeight: 600, color: c.teal, textTransform: "uppercase", letterSpacing: "0.12em", margin: "20px 0 6px" }}>{children}</h3>
  ),
  strong: ({ children }) => (
    <strong style={{ color: c.stoneMid, fontWeight: 600 }}>{children}</strong>
  ),
  p: ({ children }) => (
    <p style={{ fontFamily: f.body, fontSize: "16px", lineHeight: 1.8, color: c.stoneMid, margin: "0 0 10px" }}>{children}</p>
  ),
  li: ({ children }) => (
    <li style={{ fontFamily: f.body, fontSize: "16px", lineHeight: 1.8, color: c.stoneMid, marginBottom: "5px" }}>{children}</li>
  ),
  ul: ({ children }) => (
    <ul style={{ paddingLeft: "18px", margin: "0 0 12px" }}>{children}</ul>
  ),
};

export default function DayCard({ dayNumber, data, onRegenerate, onReply }) {
  const loading = data?.loading;
  const content = data?.content || "";

  return (
    <div style={{ backgroundColor: c.white, border: `1px solid ${c.sandBorder}`, borderRadius: "12px", overflow: "hidden", borderTop: `3px solid ${c.tealBright}` }}>

      {/* Card header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: `1px solid ${c.sandMid}` }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span style={{ fontFamily: f.mono, fontSize: "10px", color: c.teal, letterSpacing: "0.14em", fontWeight: 500 }}>DAY</span>
          <span style={{ fontFamily: f.display, fontSize: "32px", fontWeight: 700, color: c.stone, lineHeight: 1, letterSpacing: "-0.01em" }}>{dayNumber}</span>
        </div>
        <button
          onClick={onRegenerate} disabled={loading}
          style={{ display: "flex", alignItems: "center", gap: "5px", padding: "6px 12px", borderRadius: "7px", border: `1px solid ${c.sandBorder}`, backgroundColor: "transparent", color: loading ? c.stoneFaint : c.stoneLight, fontSize: "11px", fontFamily: f.sans, cursor: loading ? "not-allowed" : "pointer" }}
        >
          <svg width="11" height="11" viewBox="0 0 13 13" fill="none">
            <path d="M11 2.5A5 5 0 1 0 11.5 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            <path d="M9 2L11.5 2.5L11 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Regenerate
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: "24px 28px", minHeight: "120px" }}>
        {loading && !content && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: c.stoneFaint, fontFamily: f.sans, fontSize: "13px" }}>
            <div style={{ width: "7px", height: "7px", borderRadius: "50%", backgroundColor: c.teal, animation: "ep-pulse 1s infinite" }} />
            Planning day {dayNumber}…
          </div>
        )}
        {content && <ReactMarkdown components={mdComponents}>{content}</ReactMarkdown>}
      </div>

      {/* Card footer */}
      <div style={{ padding: "10px 24px", borderTop: `1px solid ${c.sandMid}`, display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={onReply}
          style={{ display: "flex", alignItems: "center", gap: "5px", background: "none", border: `1px solid ${c.sandBorder}`, borderRadius: "7px", padding: "5px 12px", color: c.stoneLight, fontSize: "11px", fontFamily: f.sans, cursor: "pointer" }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = c.tealBorder; e.currentTarget.style.color = c.teal; e.currentTarget.style.backgroundColor = c.tealLight; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = c.sandBorder; e.currentTarget.style.color = c.stoneLight; e.currentTarget.style.backgroundColor = "transparent"; }}
        >
          <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
            <path d="M2 2h10a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5l-3 2V3a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.2" fill="none"/>
          </svg>
          Reply
        </button>
      </div>

    </div>
  );
}