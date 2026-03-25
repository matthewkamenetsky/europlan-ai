import { useState } from "react";
import InterestRanker from "./InterestRanker";
import { c, f } from "../styles";

const ALL_INTERESTS = [
  "history", "architecture", "art", "museums", "religion",
  "nature", "beaches", "hiking", "skiing", "food",
  "nightlife", "amusements", "sport", "thermal baths",
  "shopping", "viewpoints", "gardens",
];

const blankInput = {
  border: "none",
  borderBottom: `2px solid ${c.tealBorder}`,
  background: "transparent",
  color: c.teal,
  fontSize: "19px",
  fontFamily: f.display,
  fontWeight: 700,
  outline: "none",
  padding: "2px 4px",
  minWidth: "70px",
};

export default function NewTripModal({ onClose, onCreate }) {
  const [cities, setCities] = useState([""]);
  const [tripLength, setTripLength] = useState(7);
  const [ranked, setRanked] = useState([]);
  const [error, setError] = useState("");

  const available = ALL_INTERESTS.filter(i => !ranked.includes(i));

  const updateCities = (fn) => setCities(fn);
  const addInterest = (i) => setRanked(p => [...p, i]);
  const removeInterest = (i) => setRanked(p => p.filter(x => x !== i));
  const moveInterest = (idx, dir) => {
    const next = [...ranked];
    const swapIdx = idx + dir;
    if (swapIdx < 0 || swapIdx >= next.length) return;
    [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
    setRanked(next);
  };

  const handleCreate = () => {
    const validCities = cities.map(c => c.trim()).filter(Boolean);
    if (validCities.length === 0) return setError("Please enter at least one city.");
    if (ranked.length === 0) return setError("Please select at least one interest.");
    setError("");
    onCreate({ cities: validCities, tripLength, interests: ranked });
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        backgroundColor: "rgba(28,30,30,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 100, padding: "20px",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          backgroundColor: c.white, borderRadius: "16px",
          padding: "36px 40px", width: "100%", maxWidth: "560px",
          maxHeight: "90vh", overflowY: "auto",
          boxShadow: "0 24px 64px rgba(0,0,0,0.15)",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
          <div>
            <h2 style={{ fontFamily: f.display, fontSize: "26px", fontWeight: 700, color: c.stone, margin: "0 0 4px", letterSpacing: "0.01em" }}>
              Plan a new trip
            </h2>
            <p style={{ fontFamily: f.body, fontSize: "15px", color: c.stoneLight, margin: 0 }}>
              Fill in the details and we'll build your itinerary.
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: c.stoneFaint, fontSize: "20px", cursor: "pointer", lineHeight: 1, padding: "4px" }}>×</button>
        </div>

        {/* Fill-in-the-blanks */}
        <div style={{
          fontFamily: f.display, fontSize: "19px", color: c.stone,
          lineHeight: 2.4, display: "flex", flexWrap: "wrap",
          alignItems: "baseline", gap: "6px", marginBottom: "28px",
          padding: "20px 22px", backgroundColor: c.tealLight,
          borderRadius: "10px", border: `1px solid ${c.tealBorder}`,
        }}>
          <span>I want to visit</span>
          {cities.map((city, i) => (
            <span key={i} style={{ display: "inline-flex", alignItems: "baseline", gap: "4px" }}>
              {i > 0 && <span style={{ color: c.stoneFaint }}>and</span>}
              <input
                style={{ ...blankInput, width: `${Math.max((city.length || 6) + 2, 8)}ch` }}
                value={city}
                onChange={e => updateCities(p => p.map((v, idx) => idx === i ? e.target.value : v))}
                onKeyDown={e => e.key === "Enter" && updateCities(p => [...p, ""])}
                placeholder="city"
              />
              {cities.length > 1 && (
                <button onClick={() => updateCities(p => p.filter((_, idx) => idx !== i))} style={{ background: "none", border: "none", color: c.stoneFaint, cursor: "pointer", fontSize: "14px", padding: "0 1px", lineHeight: 1 }}>×</button>
              )}
            </span>
          ))}
          <button onClick={() => updateCities(p => [...p, ""])} style={{ background: "none", border: `1px dashed ${c.tealBorder}`, borderRadius: "5px", color: c.teal, cursor: "pointer", fontSize: "11px", padding: "2px 8px", fontFamily: f.sans }}>+ city</button>
          <span>for</span>
          <input
            style={{ ...blankInput, width: "44px", textAlign: "center" }}
            type="number" min={1} max={30} value={tripLength}
            onChange={e => setTripLength(Number(e.target.value))}
          />
          <span>{tripLength === 1 ? "day." : "days."}</span>
        </div>

        <div style={{ borderTop: `1px solid ${c.sandDark}`, marginBottom: "24px" }} />

        <InterestRanker
          ranked={ranked}
          available={available}
          onAdd={addInterest}
          onRemove={removeInterest}
          onMove={moveInterest}
        />

        {error && (
          <p style={{ color: c.errorRed, fontSize: "12px", fontFamily: f.mono, margin: "0 0 14px", padding: "8px 12px", backgroundColor: c.errorBg, borderRadius: "6px" }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleCreate} style={{ flex: 1, padding: "12px", borderRadius: "9px", border: "none", backgroundColor: c.teal, color: c.white, fontSize: "14px", fontWeight: 600, fontFamily: f.sans, cursor: "pointer" }}>
            Plan my trip →
          </button>
          <button onClick={onClose} style={{ padding: "12px 20px", borderRadius: "9px", border: `1px solid ${c.sandBorder}`, backgroundColor: "transparent", color: c.stoneLight, fontSize: "14px", fontFamily: f.sans, cursor: "pointer" }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}