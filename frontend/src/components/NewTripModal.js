import { useState, useRef, useEffect, useCallback } from "react";
import InterestRanker from "./InterestRanker";
import { c, f } from "../styles";

const ALL_INTERESTS = [
  "history", "architecture", "art", "museums", "religion",
  "nature", "beaches", "hiking", "skiing", "food",
  "nightlife", "amusements", "sport", "thermal baths",
  "shopping", "viewpoints", "gardens",
];

const S = {
  input: {
    border: "none", borderBottom: `2px solid ${c.tealBorder}`,
    background: "transparent", color: c.teal,
    fontSize: "19px", fontFamily: f.display, fontWeight: 700,
    outline: "none", padding: "2px 4px", minWidth: "70px",
  },
  iconBtn: {
    background: "none", border: "none",
    cursor: "pointer", lineHeight: 1, padding: "0 1px",
  },
  footerBtn: (primary) => ({
    padding: primary ? "12px" : "12px 20px",
    flex: primary ? 1 : undefined,
    borderRadius: "9px",
    border: primary ? "none" : `1px solid ${c.sandBorder}`,
    backgroundColor: primary ? c.teal : "transparent",
    color: primary ? c.white : c.stoneLight,
    fontSize: "14px", fontWeight: primary ? 600 : 400,
    fontFamily: f.sans, cursor: "pointer",
  }),
};

export default function NewTripModal({ onClose, onCreate }) {
  const [cities, setCities] = useState([""]);
  const [tripLengthStr, setTripLengthStr] = useState("7");
  const [ranked, setRanked] = useState([]);
  const [error, setError] = useState("");

  const cityRefs = useRef([]);
  const prevCount = useRef(1);

  // Auto-focus newest city input
  useEffect(() => {
    if (cities.length > prevCount.current) cityRefs.current[cities.length - 1]?.focus();
    prevCount.current = cities.length;
  }, [cities.length]);

  const addCity    = ()      => setCities(p => [...p, ""]);
  const removeCity = (i)     => setCities(p => p.filter((_, idx) => idx !== i));
  const updateCity = (i, val) => setCities(p => p.map((v, idx) => idx === i ? val : v));

  const addInterest    = (i)        => setRanked(p => [...p, i]);
  const removeInterest = (i)        => setRanked(p => p.filter(x => x !== i));
  const moveInterest   = (idx, dir) => {
    const next = [...ranked];
    const swap = idx + dir;
    if (swap < 0 || swap >= next.length) return;
    [next[idx], next[swap]] = [next[swap], next[idx]];
    setRanked(next);
  };

  const handleCityKeyDown = (e, i) => {
    if (e.key === "Enter" || e.key === "NumpadEnter") {
      e.preventDefault();
      if (!e.shiftKey) addCity();
      return;
    }
    if (e.key === "Backspace" && cities[i] === "" && cities.length > 1 && i > 0) {
      e.preventDefault();
      removeCity(i);
      setTimeout(() => cityRefs.current[i - 1]?.focus(), 0);
    }
  };

  const handleDaysChange = (e) => {
    if (e.target.value === "" || /^\d+$/.test(e.target.value)) setTripLengthStr(e.target.value);
  };
  const handleDaysBlur = () => {
    const n = parseInt(tripLengthStr, 10);
    setTripLengthStr(isNaN(n) || n < 1 ? "1" : n > 30 ? "30" : String(n));
  };

  const handleCreate = useCallback(() => {
    const validCities = cities.map(s => s.trim()).filter(Boolean);
    if (!validCities.length) return setError("Please enter at least one city.");
    if (!ranked.length)      return setError("Please select at least one interest.");
    const tripLength = parseInt(tripLengthStr, 10);
    if (isNaN(tripLength) || tripLength < 1) return setError("Please enter a valid number of days.");
    setError("");
    onCreate({ cities: validCities, tripLength, interests: ranked });
  }, [cities, ranked, tripLengthStr, onCreate]);

  // Global Shift+Enter to submit
  useEffect(() => {
    const onKey = (e) => {
      if ((e.key === "Enter" || e.key === "NumpadEnter") && e.shiftKey) {
        e.preventDefault();
        handleCreate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleCreate]);

  const displayDays = parseInt(tripLengthStr, 10);

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, backgroundColor: "rgba(28,30,30,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "20px" }}>
      <div onClick={e => e.stopPropagation()} style={{ backgroundColor: c.white, borderRadius: "16px", padding: "36px 40px", width: "100%", maxWidth: "560px", maxHeight: "90vh", overflowY: "auto", boxShadow: "0 24px 64px rgba(0,0,0,0.15)" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
          <div>
            <h2 style={{ fontFamily: f.display, fontSize: "26px", fontWeight: 700, color: c.stone, margin: "0 0 4px", letterSpacing: "0.01em" }}>Plan a new trip</h2>
            <p style={{ fontFamily: f.body, fontSize: "15px", color: c.stoneLight, margin: 0 }}>Fill in the details and we'll build your itinerary.</p>
          </div>
          <button onClick={onClose} style={{ ...S.iconBtn, color: c.stoneFaint, fontSize: "20px", padding: "4px" }}>×</button>
        </div>

        {/* Fill-in-the-blanks */}
        <div style={{ fontFamily: f.display, fontSize: "19px", color: c.stone, lineHeight: 2.4, display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: "6px", marginBottom: "28px", padding: "20px 22px", backgroundColor: c.tealLight, borderRadius: "10px", border: `1px solid ${c.tealBorder}` }}>
          <span>I want to visit</span>
          {cities.map((city, i) => (
            <span key={i} style={{ display: "inline-flex", alignItems: "baseline", gap: "4px" }}>
              {i > 0 && <span style={{ color: c.stoneFaint }}>and</span>}
              <input
                ref={el => cityRefs.current[i] = el}
                style={{ ...S.input, width: `${Math.max((city.length || 6) + 2, 8)}ch` }}
                value={city}
                onChange={e => updateCity(i, e.target.value)}
                onKeyDown={e => handleCityKeyDown(e, i)}
                placeholder="city"
              />
              {cities.length > 1 && (
                <button onClick={() => removeCity(i)} style={{ ...S.iconBtn, color: c.stoneFaint, fontSize: "14px" }}>×</button>
              )}
            </span>
          ))}
          <button onClick={addCity} style={{ background: "none", border: `1px dashed ${c.tealBorder}`, borderRadius: "5px", color: c.teal, cursor: "pointer", fontSize: "11px", padding: "2px 8px", fontFamily: f.sans }}>+ city</button>
          <span>for</span>
          <input
            style={{ ...S.input, width: "44px", textAlign: "center" }}
            type="text" inputMode="numeric"
            value={tripLengthStr}
            onChange={handleDaysChange}
            onBlur={handleDaysBlur}
          />
          <span>{isNaN(displayDays) || displayDays !== 1 ? "days." : "day."}</span>
        </div>

        <div style={{ borderTop: `1px solid ${c.sandDark}`, marginBottom: "24px" }} />

        <InterestRanker
          ranked={ranked} available={ALL_INTERESTS.filter(i => !ranked.includes(i))}
          onAdd={addInterest} onRemove={removeInterest} onMove={moveInterest}
        />

        {error && (
          <p style={{ color: c.errorRed, fontSize: "12px", fontFamily: f.mono, margin: "0 0 14px", padding: "8px 12px", backgroundColor: c.errorBg, borderRadius: "6px" }}>{error}</p>
        )}

        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleCreate} style={S.footerBtn(true)}>Plan my trip →</button>
          <button onClick={onClose} style={S.footerBtn(false)}>Cancel</button>
        </div>

      </div>
    </div>
  );
}