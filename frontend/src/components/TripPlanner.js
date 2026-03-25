import { useEffect, useRef, useState, useCallback } from "react";
import DayCard from "./DayCard";
import { parseDays } from "../utils/parseDays";
import { c, f } from "../styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Shared stream reader — calls onChunk with each decoded token until done
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

function DayStrip({ dayNumbers, days, activeDay, onSelect }) {
  return (
    <div style={{
      backgroundColor: c.white, borderBottom: `1px solid ${c.sandBorder}`,
      padding: "0 40px", display: "flex", alignItems: "center",
      gap: "4px", overflowX: "auto", flexShrink: 0, height: "48px",
    }}>
      {dayNumbers.map(n => {
        const dayData = days.find(d => d.dayNumber === n);
        const isActive = n === activeDay;
        const isDone = dayData?.content && !dayData?.loading;
        const isLoading = dayData?.loading;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            style={{
              padding: "5px 13px", borderRadius: "6px",
              border: isActive ? `1.5px solid ${c.teal}` : `1px solid ${c.sandBorder}`,
              backgroundColor: isActive ? c.tealLight : "transparent",
              color: isActive ? c.teal : c.stoneLight,
              fontSize: "12px", fontWeight: isActive ? 600 : 400,
              fontFamily: f.sans, cursor: "pointer", flexShrink: 0,
              display: "flex", alignItems: "center", gap: "5px",
              transition: "all 0.1s",
            }}
          >
            Day {n}
            {isLoading && <span style={{ width: "5px", height: "5px", borderRadius: "50%", backgroundColor: c.teal, display: "inline-block", animation: "ep-pulse 1s infinite" }} />}
            {isDone && !isLoading && <span style={{ width: "5px", height: "5px", borderRadius: "50%", backgroundColor: c.successGreen, display: "inline-block" }} />}
          </button>
        );
      })}
      <style>{`@keyframes ep-pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }`}</style>
    </div>
  );
}

export default function TripPlanner({ trip, onBack, onUpdate }) {
  const [activeDay, setActiveDay] = useState(1);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [error, setError] = useState("");
  const hasGenerated = useRef(false);

  const generateAll = useCallback(async () => {
    setError("");
    setGlobalLoading(true);
    onUpdate(t => ({ ...t, days: [], loading: true }));
    try {
      const response = await fetch(`${API_BASE}/plan-trip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cities: trip.params.cities,
          trip_length: trip.params.tripLength,
          interests: trip.params.interests,
        }),
      });
      if (!response.ok) {
        const err = await response.json();
        setError(err.detail || "Something went wrong.");
        return;
      }

      const tripId = response.headers.get("X-Trip-Id");
      if (tripId) onUpdate(t => ({ ...t, tripId: parseInt(tripId) }));

      let fullText = "";
      await streamResponse(response, chunk => {
        fullText += chunk;
        const parsed = parseDays(fullText, trip.params.tripLength);
        onUpdate(t => ({ ...t, days: parsed }));
      });
    } catch {
      setError("Could not connect to the backend.");
    } finally {
      setGlobalLoading(false);
      onUpdate(t => ({ ...t, loading: false }));
    }
  }, [trip.params, onUpdate]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!hasGenerated.current && trip.days.length === 0) {
      hasGenerated.current = true;
      generateAll();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const regenerateDay = async (dayNumber) => {
    setError("");
    onUpdate(t => ({
      ...t,
      days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, loading: true, content: "" } : d),
    }));
    try {
      const response = await fetch(`${API_BASE}/plan-trip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cities: trip.params.cities,
          trip_length: 1,
          interests: trip.params.interests,
          day_number: dayNumber,
        }),
      });
      if (!response.ok) {
        setError("Regeneration failed.");
        onUpdate(t => ({ ...t, days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, loading: false } : d) }));
        return;
      }

      let content = "";
      await streamResponse(response, chunk => {
        content += chunk;
        onUpdate(t => ({
          ...t,
          days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, content } : d),
        }));
      });
    } catch {
      setError("Could not connect to the backend.");
    } finally {
      onUpdate(t => ({
        ...t,
        days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, loading: false } : d),
      }));
    }
  };

  const updateComment = (dayNumber, comment) => {
    onUpdate(t => ({
      ...t,
      days: t.days.map(d => d.dayNumber === dayNumber ? { ...d, comment } : d),
    }));
  };

  const totalDays = trip.params.tripLength;
  const dayNumbers = Array.from({ length: totalDays }, (_, i) => i + 1);
  const activeData = trip.days.find(d => d.dayNumber === activeDay);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: c.sand, display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <nav style={{
        borderBottom: `1px solid ${c.sandBorder}`, padding: "0 40px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: "56px", backgroundColor: c.white, flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button onClick={onBack} style={{ display: "flex", alignItems: "center", gap: "5px", background: "none", border: "none", color: c.stoneLight, fontSize: "13px", fontFamily: f.sans, cursor: "pointer", padding: 0 }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M9 2L4 7L9 12" stroke={c.stoneLight} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            All trips
          </button>
          <span style={{ color: c.sandBorder }}>|</span>
          <span style={{ fontFamily: f.display, fontSize: "17px", fontWeight: 700, color: c.teal, letterSpacing: "0.01em" }}>{trip.label}</span>
          <span style={{ fontFamily: f.mono, fontSize: "11px", color: c.stoneFaint }}>{totalDays} days</span>
        </div>
        <button
          onClick={generateAll}
          disabled={globalLoading}
          style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 14px", borderRadius: "7px", border: `1px solid ${c.sandBorder}`, backgroundColor: c.white, color: globalLoading ? c.stoneFaint : c.stoneMid, fontSize: "12px", fontFamily: f.sans, cursor: globalLoading ? "not-allowed" : "pointer" }}
        >
          <svg width="12" height="12" viewBox="0 0 13 13" fill="none">
            <path d="M11 2.5A5 5 0 1 0 11.5 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            <path d="M9 2L11.5 2.5L11 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Regenerate all
        </button>
      </nav>

      <DayStrip dayNumbers={dayNumbers} days={trip.days} activeDay={activeDay} onSelect={setActiveDay} />

      {/* Content */}
      <div style={{ flex: 1, maxWidth: "720px", width: "100%", margin: "0 auto", padding: "36px 32px" }}>
        {error && (
          <div style={{ color: c.errorRed, fontSize: "12px", fontFamily: f.mono, padding: "10px 14px", backgroundColor: c.errorBg, borderRadius: "7px", marginBottom: "20px" }}>
            {error}
          </div>
        )}
        {globalLoading && !activeData && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: c.stoneFaint, fontFamily: f.sans, fontSize: "14px", padding: "40px 0" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: c.teal, animation: "ep-pulse 1s infinite" }} />
            Building your itinerary…
          </div>
        )}
        {(activeData || (globalLoading && trip.days.length > 0)) && (
          <DayCard
            dayNumber={activeDay}
            data={activeData}
            onRegenerate={() => regenerateDay(activeDay)}
            onCommentChange={(val) => updateComment(activeDay, val)}
          />
        )}
      </div>
    </div>
  );
}