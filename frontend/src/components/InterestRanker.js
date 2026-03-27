import { useRef, useState } from "react";
import { c, f } from "../styles";

export default function InterestRanker({ ranked, available, onAdd, onRemove, onMove }) {
  const dragIdx     = useRef(null);
  const dragOverIdx = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleDragEnd = () => {
    const from = dragIdx.current;
    const to   = dragOverIdx.current;
    if (from !== null && to !== null && from !== to) {
      const steps = to > from ? 1 : -1;
      let cur = from;
      while (cur !== to) { onMove(cur, steps); cur += steps; }
    }
    dragIdx.current     = null;
    dragOverIdx.current = null;
    setDragging(false);
  };

  return (
    <div style={{ marginBottom: "20px" }}>
      <p style={{ fontSize: "10px", fontFamily: f.mono, letterSpacing: "0.12em", color: c.stoneFaint, marginBottom: "10px" }}>
        INTERESTS — click to add, drag to prioritise
      </p>

      {ranked.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginBottom: "12px" }}>
          {ranked.map((interest, idx) => (
            <div
              key={interest}
              draggable
              onDragStart={() => { dragIdx.current = idx; setDragging(true); }}
              onDragEnter={() => { dragOverIdx.current = idx; }}
              onDragEnd={handleDragEnd}
              onDragOver={e => e.preventDefault()}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                backgroundColor: c.tealLight, border: `1px solid ${c.tealBorder}`,
                borderRadius: "8px", padding: "7px 10px", userSelect: "none",
                cursor: dragging && dragIdx.current === idx ? "grabbing" : "grab",
                opacity: dragging && dragIdx.current === idx ? 0.4 : 1,
                transition: "opacity 0.15s",
              }}
            >
              <svg width="10" height="14" viewBox="0 0 10 14" fill="none" style={{ flexShrink: 0, opacity: 0.4 }}>
                <circle cx="3" cy="2.5"  r="1.2" fill={c.teal}/><circle cx="7" cy="2.5"  r="1.2" fill={c.teal}/>
                <circle cx="3" cy="7"    r="1.2" fill={c.teal}/><circle cx="7" cy="7"    r="1.2" fill={c.teal}/>
                <circle cx="3" cy="11.5" r="1.2" fill={c.teal}/><circle cx="7" cy="11.5" r="1.2" fill={c.teal}/>
              </svg>
              <span style={{ fontSize: "10px", color: c.teal, fontFamily: f.mono, fontWeight: 500, minWidth: "18px" }}>#{idx + 1}</span>
              <span style={{ fontSize: "13px", color: c.teal, fontFamily: f.sans, flex: 1 }}>{interest}</span>
              <button
                onClick={() => onRemove(interest)}
                style={{ background: "none", border: "none", cursor: "pointer", color: c.stoneFaint, fontSize: "14px", lineHeight: 1, padding: "0 2px" }}
                onMouseEnter={e => e.currentTarget.style.color = c.errorRed}
                onMouseLeave={e => e.currentTarget.style.color = c.stoneFaint}
              >×</button>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {available.map(interest => (
          <button
            key={interest}
            onClick={() => onAdd(interest)}
            style={{ backgroundColor: c.sandMid, border: `1px solid ${c.sandBorder}`, borderRadius: "20px", color: c.stoneLight, padding: "4px 11px", fontSize: "12px", cursor: "pointer", fontFamily: f.sans }}
            onMouseEnter={e => { e.currentTarget.style.backgroundColor = c.tealLight; e.currentTarget.style.borderColor = c.tealBorder; e.currentTarget.style.color = c.teal; }}
            onMouseLeave={e => { e.currentTarget.style.backgroundColor = c.sandMid; e.currentTarget.style.borderColor = c.sandBorder; e.currentTarget.style.color = c.stoneLight; }}
          >{interest}</button>
        ))}
      </div>
    </div>
  );
}