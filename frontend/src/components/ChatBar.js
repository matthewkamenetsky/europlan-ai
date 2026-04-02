import { c, f } from "../styles";

export default function ChatBar({ inputRef, value, onChange, onKeyDown, onSend, onCritique, onRegenerate, referencedDay, onClearRef, loading, critiqueLoading, globalLoading, hasTripId }) {
  const canSend   = value.trim() && !loading;
  const anyLoading = loading || critiqueLoading || globalLoading;

  return (
    <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 20, backgroundColor: c.white, borderTop: `1px solid ${c.sandBorder}`, padding: "12px 24px" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto" }}>

        {referencedDay && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px", backgroundColor: c.tealLight, border: `1px solid ${c.tealBorder}`, borderRadius: "6px", padding: "4px 10px", width: "fit-content" }}>
            <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
              <path d="M2 2h10a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5l-3 2V3a1 1 0 0 1 1-1z" stroke={c.teal} strokeWidth="1.2" fill="none"/>
            </svg>
            <span style={{ fontSize: "11px", fontFamily: f.mono, color: c.teal, letterSpacing: "0.08em" }}>DAY {referencedDay}</span>
            <button onClick={onClearRef} style={{ background: "none", border: "none", cursor: "pointer", color: c.stoneFaint, fontSize: "13px", lineHeight: 1, padding: "0 0 0 2px" }}>×</button>
          </div>
        )}

        <div style={{ display: "flex", gap: "8px", alignItems: "flex-end" }}>
          <textarea
            ref={inputRef} value={value} onChange={onChange} onKeyDown={onKeyDown}
            placeholder="Ask about your itinerary, request changes…"
            rows={1}
            style={{ flex: 1, resize: "none", border: `1px solid ${c.sandBorder}`, borderRadius: "10px", padding: "10px 14px", fontFamily: f.body, fontSize: "14px", color: c.stoneMid, outline: "none", lineHeight: 1.6, backgroundColor: c.sand, maxHeight: "120px", overflowY: "auto" }}
            onInput={e => { e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
          />

          <button onClick={onSend} disabled={!canSend} style={{ padding: "10px 16px", borderRadius: "10px", border: "none", backgroundColor: canSend ? c.teal : c.sandDark, color: canSend ? c.white : c.stoneFaint, fontFamily: f.sans, fontSize: "13px", fontWeight: 600, cursor: canSend ? "pointer" : "default", flexShrink: 0, transition: "background-color 0.15s" }}>
            {loading ? "…" : "Send"}
          </button>

          <div style={{ width: "1px", height: "32px", backgroundColor: c.sandBorder, flexShrink: 0, alignSelf: "center" }} />

          <button onClick={onCritique} disabled={!hasTripId || anyLoading} title={!hasTripId ? "Save your trip first" : "Critique itinerary"} style={{ display: "flex", alignItems: "center", gap: "5px", padding: "10px 12px", borderRadius: "10px", border: `1px solid ${c.sandBorder}`, backgroundColor: c.white, color: (!hasTripId || anyLoading) ? c.stoneFaint : c.stoneMid, fontFamily: f.sans, fontSize: "12px", cursor: (!hasTripId || anyLoading) ? "not-allowed" : "pointer", flexShrink: 0, whiteSpace: "nowrap" }}>
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M7 4.5v3l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {critiqueLoading ? "…" : "Critique"}
          </button>

          <button onClick={onRegenerate} disabled={anyLoading} title="Regenerate full itinerary" style={{ display: "flex", alignItems: "center", gap: "5px", padding: "10px 12px", borderRadius: "10px", border: `1px solid ${c.sandBorder}`, backgroundColor: c.white, color: anyLoading ? c.stoneFaint : c.stoneMid, fontFamily: f.sans, fontSize: "12px", cursor: anyLoading ? "not-allowed" : "pointer", flexShrink: 0, whiteSpace: "nowrap" }}>
            <svg width="12" height="12" viewBox="0 0 13 13" fill="none">
              <path d="M11 2.5A5 5 0 1 0 11.5 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              <path d="M9 2L11.5 2.5L11 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Regen
          </button>
        </div>
      </div>
    </div>
  );
}