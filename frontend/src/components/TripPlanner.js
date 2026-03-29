import { useEffect, useRef, useState, useCallback } from "react";
import DayCard from "./DayCard";
import { parseDays } from "../utils/parseDays";
import { c, f } from "../styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function streamResponse(response, onChunk) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let done = false;
  while (!done) {
    const result = await reader.read();
    done = result.done;
    if (!done) onChunk(decoder.decode(result.value, { stream: true }));
  }
}

function TripNav({ label, totalDays, loading, onBack, onRegenerate }) {
  return (
    <nav style={{ position: "sticky", top: 0, zIndex: 10, backgroundColor: c.white, borderBottom: `1px solid ${c.sandBorder}`, padding: "0 40px", height: "56px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
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
      <button onClick={onRegenerate} disabled={loading} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 14px", borderRadius: "7px", border: `1px solid ${c.sandBorder}`, backgroundColor: c.white, color: loading ? c.stoneFaint : c.stoneMid, fontSize: "12px", fontFamily: f.sans, cursor: loading ? "not-allowed" : "pointer" }}>
        <svg width="12" height="12" viewBox="0 0 13 13" fill="none">
          <path d="M11 2.5A5 5 0 1 0 11.5 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          <path d="M9 2L11.5 2.5L11 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Regenerate all
      </button>
    </nav>
  );
}

function ChatBar({ inputRef, value, onChange, onKeyDown, onSend, referencedDay, onClearRef }) {
  const canSend = value.trim();
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
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
          <textarea
            ref={inputRef} value={value} onChange={onChange} onKeyDown={onKeyDown}
            placeholder="Ask about your itinerary, request changes…"
            rows={1}
            style={{ flex: 1, resize: "none", border: `1px solid ${c.sandBorder}`, borderRadius: "10px", padding: "10px 14px", fontFamily: f.body, fontSize: "14px", color: c.stoneMid, outline: "none", lineHeight: 1.6, backgroundColor: c.sand, maxHeight: "120px", overflowY: "auto" }}
            onInput={e => { e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
          />
          <button onClick={onSend} disabled={!canSend} style={{ padding: "10px 16px", borderRadius: "10px", border: "none", backgroundColor: canSend ? c.teal : c.sandDark, color: canSend ? c.white : c.stoneFaint, fontFamily: f.sans, fontSize: "13px", fontWeight: 600, cursor: canSend ? "pointer" : "default", flexShrink: 0, transition: "background-color 0.15s" }}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TripPlanner({ trip, onBack, onUpdate }) {
  const [globalLoading, setGlobalLoading] = useState(false);
  const [error, setError] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [referencedDay, setReferencedDay] = useState(null);
  const [messages, setMessages] = useState([]);
  const hasGenerated = useRef(false);
  const chatInputRef = useRef(null);
  const totalDays = trip.params.tripLength;

  const generateAll = useCallback(async () => {
    setError("");
    setGlobalLoading(true);
    onUpdate(t => ({ ...t, days: [], loading: true }));
    try {
      const response = await fetch(`${API_BASE}/plan-trip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cities: trip.params.cities, trip_length: trip.params.tripLength, interests: trip.params.interests }),
      });
      if (!response.ok) { setError((await response.json()).detail || "Something went wrong."); return; }
      const tripId = response.headers.get("X-Trip-Id");
      if (tripId) onUpdate(t => ({ ...t, tripId: parseInt(tripId) }));
      let fullText = "";
      await streamResponse(response, chunk => {
        fullText += chunk;
        onUpdate(t => ({ ...t, days: parseDays(fullText, trip.params.tripLength) }));
      });
    } catch { setError("Could not connect to the backend."); }
    finally { setGlobalLoading(false); onUpdate(t => ({ ...t, loading: false })); }
  }, [trip.params, onUpdate]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!hasGenerated.current && trip.days.length === 0) { hasGenerated.current = true; generateAll(); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const regenerateDay = async (dayNumber) => {
    setError("");
    const setDay = (patch) => onUpdate(t => ({ ...t, days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, ...patch } : d) }));
    setDay({ loading: true, content: "" });
    try {
      const response = await fetch(`${API_BASE}/regen-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trip_id: trip.tripId, day_number: dayNumber }),
      });
      if (!response.ok) { setError("Regeneration failed."); setDay({ loading: false }); return; }
      let newContent = "";
      await streamResponse(response, chunk => { newContent += chunk; setDay({ content: newContent }); });
      onUpdate(t => {
        const updatedDays = t.days.map(d => d.dayNumber === dayNumber ? { ...d, content: newContent, loading: false } : d);
        if (t.tripId) {
          const itinerary = updatedDays.slice().sort((a, b) => a.dayNumber - b.dayNumber).map(d => d.content).join("\n\n");
          fetch(`${API_BASE}/trips/${t.tripId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ itinerary }) }).catch(() => {});
        }
        return { ...t, days: updatedDays };
      });
    } catch { setError("Could not connect to the backend."); }
    finally { setDay({ loading: false }); }
  };

  const handleSend = () => {
    const text = chatInput.trim();
    if (!text) return;
    setMessages(prev => [...prev, { role: "user", text, dayRef: referencedDay }]);
    setChatInput("");
    setReferencedDay(null);
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: c.sand, display: "flex", flexDirection: "column" }}>
      <style>{`@keyframes ep-pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }`}</style>

      <TripNav label={trip.label} totalDays={totalDays} loading={globalLoading} onBack={onBack} onRegenerate={generateAll} />

      <div style={{ flex: 1, maxWidth: "720px", width: "100%", margin: "0 auto", padding: "36px 32px 160px" }}>
        {error && <div style={{ color: c.errorRed, fontSize: "12px", fontFamily: f.mono, padding: "10px 14px", backgroundColor: c.errorBg, borderRadius: "7px", marginBottom: "20px" }}>{error}</div>}

        {globalLoading && trip.days.length === 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: c.stoneFaint, fontFamily: f.sans, fontSize: "14px", padding: "40px 0" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: c.teal, animation: "ep-pulse 1s infinite" }} />
            Building your itinerary…
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {Array.from({ length: totalDays }, (_, i) => i + 1).map(n => {
            const data = trip.days.find(d => d.dayNumber === n);
            if (!data && !globalLoading) return null;
            return <DayCard key={n} dayNumber={n} data={data} onRegenerate={() => regenerateDay(n)} onReply={() => { setReferencedDay(n); chatInputRef.current?.focus(); }} />;
          })}
        </div>

        {messages.length > 0 && (
          <div style={{ marginTop: "32px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ alignSelf: "flex-end", maxWidth: "80%" }}>
                {msg.dayRef && <div style={{ fontSize: "10px", fontFamily: f.mono, color: c.teal, marginBottom: "4px", letterSpacing: "0.08em" }}>RE: DAY {msg.dayRef}</div>}
                <div style={{ backgroundColor: c.teal, color: c.white, borderRadius: "12px 12px 2px 12px", padding: "10px 14px", fontFamily: f.body, fontSize: "14px", lineHeight: 1.6 }}>{msg.text}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ChatBar
        inputRef={chatInputRef} value={chatInput}
        onChange={e => setChatInput(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
        onSend={handleSend}
        referencedDay={referencedDay} onClearRef={() => setReferencedDay(null)}
      />
    </div>
  );
}