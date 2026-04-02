import { useEffect, useRef, useState, useCallback } from "react";
import DayCard from "./DayCard";
import TripNav from "./TripNav";
import ChatBar from "./ChatBar";
import CritiqueBubble from "./CritiqueBubble";
import { parseDays } from "../utils/parseDays";
import { c, f } from "../styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";
const ITINERARY_MARKER = "UPDATED_ITINERARY:";

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

export default function TripPlanner({ trip, onBack, onUpdate, onTripServerIdResolved }) {
  const [globalLoading, setGlobalLoading]     = useState(false);
  const [chatLoading, setChatLoading]         = useState(false);
  const [critiqueLoading, setCritiqueLoading] = useState(false);
  const [error, setError]                     = useState("");
  const [chatInput, setChatInput]             = useState("");
  const [referencedDay, setReferencedDay]     = useState(null);
  const [messages, setMessages]               = useState(() => Array.isArray(trip.conversation) ? trip.conversation : []);

  const hasGenerated  = useRef(false);
  const chatInputRef  = useRef(null);
  const messagesEndRef = useRef(null);
  const totalDays = trip.params.tripLength;
  const conversationSig = JSON.stringify(trip.conversation ?? []);

  useEffect(() => {
    const conv = trip.conversation;
    setMessages(Array.isArray(conv) ? conv : []);
  }, [trip.id, trip.tripId, conversationSig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Helpers ────────────────────────────────────────────────────────────────

  const persistConversation = useCallback(async (conversation) => {
    if (!trip.tripId) return;
    try {
      await fetch(`${API_BASE}/trips/${trip.tripId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation }),
      });
    } catch { /* best-effort */ }
  }, [trip.tripId]);

  const pushMessage = useCallback((msg) => {
    setMessages(prev => {
      const next = [...prev, msg];
      onUpdate(t => ({ ...t, conversation: next }));
      persistConversation(next);
      return next;
    });
  }, [onUpdate, persistConversation]);

  // ── Actions ────────────────────────────────────────────────────────────────

  const generateAll = useCallback(async () => {
    setError("");
    setGlobalLoading(true);
    onUpdate(t => ({ ...t, days: [], loading: true }));
    try {
      const res = await fetch(`${API_BASE}/plan-trip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cities: trip.params.cities, trip_length: trip.params.tripLength, interests: trip.params.interests }),
      });
      if (!res.ok) { setError((await res.json()).detail || "Something went wrong."); return; }
      const sid = parseInt(res.headers.get("X-Trip-Id"), 10);
      if (!Number.isNaN(sid) && onTripServerIdResolved) onTripServerIdResolved(sid, trip.id);
      let fullText = "";
      await streamResponse(res, chunk => {
        fullText += chunk;
        onUpdate(t => ({ ...t, days: parseDays(fullText, trip.params.tripLength) }));
      });
    } catch { setError("Could not connect to the backend."); }
    finally { setGlobalLoading(false); onUpdate(t => ({ ...t, loading: false })); }
  }, [trip.params, trip.id, onUpdate, onTripServerIdResolved]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!hasGenerated.current && trip.days.length === 0) { hasGenerated.current = true; generateAll(); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const regenerateDay = async (dayNumber) => {
    setError("");
    const setDay = patch => onUpdate(t => ({ ...t, days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, ...patch } : d) }));
    setDay({ loading: true, content: "" });
    try {
      const res = await fetch(`${API_BASE}/regen-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trip_id: trip.tripId, day_number: dayNumber }),
      });
      if (!res.ok) { setError("Regeneration failed."); setDay({ loading: false }); return; }
      let newContent = "";
      await streamResponse(res, chunk => { newContent += chunk; setDay({ content: newContent }); });
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

  const handleSend = async () => {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    const dayRef = referencedDay;
    setMessages(prev => [...prev, { role: "user", content: text, dayRef }, { role: "assistant", content: "" }]);
    setChatInput("");
    setReferencedDay(null);
    setChatLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/chat/${trip.tripId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, day_ref: dayRef }),
      });
      if (!res.ok) { setError("Chat request failed."); return; }
      let fullResponse = "";
      await streamResponse(res, chunk => {
        fullResponse += chunk;
        const display = fullResponse.includes(ITINERARY_MARKER)
          ? fullResponse.split(ITINERARY_MARKER)[0].trim()
          : fullResponse;
        setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, content: display } : m));
      });
      if (fullResponse.includes(ITINERARY_MARKER)) {
        const updated = fullResponse.split(ITINERARY_MARKER)[1].trim();
        if (updated) onUpdate(t => ({ ...t, days: parseDays(updated, trip.params.tripLength) }));
      }
      setMessages(prev => { onUpdate(t => ({ ...t, conversation: prev })); persistConversation(prev); return prev; });
    } catch { setError("Could not connect to the backend."); }
    finally { setChatLoading(false); }
  };

  const handleCritique = async () => {
    if (!trip.tripId || critiqueLoading) return;
    setCritiqueLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/critique-trip/${trip.tripId}`, { method: "POST" });
      if (!res.ok) { setError((await res.json()).detail || "Critique failed."); return; }
      const critique = await res.json();
      const contextSummary = [
        `Critique scores — Realism: ${critique.realism_score}/10, Pacing: ${critique.pacing_score}/10, Preference: ${critique.preference_score}/10, Overall: ${critique.overall_score}/10.`,
        critique.issues?.length           ? `Issues: ${critique.issues.join(" ")}` : "",
        critique.recommendations?.length  ? `Recommendations: ${critique.recommendations.join(" ")}` : "",
      ].filter(Boolean).join(" ");
      pushMessage({ role: "assistant", content: contextSummary, critique });
    } catch { setError("Could not connect to the backend."); }
    finally { setCritiqueLoading(false); }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: "100vh", backgroundColor: c.sand, display: "flex", flexDirection: "column" }}>
      <style>{`@keyframes ep-pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }`}</style>

      <TripNav label={trip.label} totalDays={totalDays} onBack={onBack} />

      <div style={{ flex: 1, maxWidth: "720px", width: "100%", margin: "0 auto", padding: "36px 32px 160px" }}>

        {error && (
          <div style={{ color: c.errorRed, fontSize: "12px", fontFamily: f.mono, padding: "10px 14px", backgroundColor: c.errorBg, borderRadius: "7px", marginBottom: "20px" }}>
            {error}
          </div>
        )}

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
            return (
              <DayCard
                key={n} dayNumber={n} data={data}
                onRegenerate={() => regenerateDay(n)}
                onReply={() => { setReferencedDay(n); chatInputRef.current?.focus(); }}
              />
            );
          })}
        </div>

        {messages.length > 0 && (
          <div style={{ marginTop: "32px", display: "flex", flexDirection: "column", gap: "12px" }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ maxWidth: "85%" }}>
                  {msg.dayRef && (
                    <div style={{ fontSize: "10px", fontFamily: f.mono, color: c.teal, marginBottom: "4px", letterSpacing: "0.08em", textAlign: "right" }}>
                      RE: DAY {msg.dayRef}
                    </div>
                  )}
                  <div style={{
                    backgroundColor: msg.role === "user" ? c.teal : c.white,
                    color: msg.role === "user" ? c.white : c.stoneMid,
                    border: msg.role === "assistant" ? `1px solid ${c.sandBorder}` : "none",
                    borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                    padding: "12px 16px", fontFamily: f.body, fontSize: "14px", lineHeight: 1.6,
                  }}>
                    {msg.critique ? (
                      <CritiqueBubble critique={msg.critique} />
                    ) : msg.content ? msg.content : (
                      <span style={{ display: "flex", alignItems: "center", gap: "6px", color: c.stoneFaint }}>
                        <div style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: c.teal, animation: "ep-pulse 1s infinite" }} />
                        Thinking…
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <ChatBar
        inputRef={chatInputRef}
        value={chatInput}
        onChange={e => setChatInput(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
        onSend={handleSend}
        onCritique={handleCritique}
        onRegenerate={generateAll}
        referencedDay={referencedDay}
        onClearRef={() => setReferencedDay(null)}
        loading={chatLoading}
        critiqueLoading={critiqueLoading}
        globalLoading={globalLoading}
        hasTripId={!!trip.tripId}
      />
    </div>
  );
}