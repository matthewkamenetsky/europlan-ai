import { c, f } from "../styles";

export default function InterestRanker({ ranked, available, onAdd, onRemove, onMove }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <p style={{ fontSize: "10px", fontFamily: f.mono, letterSpacing: "0.12em", color: c.stoneFaint, marginBottom: "10px" }}>
        INTERESTS — click to add, arrows to prioritise
      </p>

      {ranked.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "12px" }}>
          {ranked.map((interest, idx) => (
            <div key={interest} style={{
              display: "inline-flex", alignItems: "center", gap: "5px",
              backgroundColor: c.tealLight,
              border: `1px solid ${c.tealBorder}`,
              borderRadius: "20px", padding: "4px 10px",
            }}>
              <span style={{ fontSize: "10px", color: c.teal, fontFamily: f.mono, fontWeight: 500 }}>#{idx + 1}</span>
              <span style={{ fontSize: "12px", color: c.teal, fontFamily: f.sans }}>{interest}</span>
              <div style={{ display: "flex", gap: "1px", marginLeft: "2px" }}>
                <button onClick={() => onMove(idx, -1)} disabled={idx === 0} style={{ background: "none", border: "none", cursor: idx === 0 ? "default" : "pointer", color: idx === 0 ? c.tealBorder : c.teal, fontSize: "10px", padding: "0 2px", lineHeight: 1 }}>↑</button>
                <button onClick={() => onMove(idx, 1)} disabled={idx === ranked.length - 1} style={{ background: "none", border: "none", cursor: idx === ranked.length - 1 ? "default" : "pointer", color: idx === ranked.length - 1 ? c.tealBorder : c.teal, fontSize: "10px", padding: "0 2px", lineHeight: 1 }}>↓</button>
                <button onClick={() => onRemove(interest)} style={{ background: "none", border: "none", cursor: "pointer", color: c.stoneFaint, fontSize: "12px", padding: "0 1px", lineHeight: 1 }}>×</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {available.map(interest => (
          <button
            key={interest}
            onClick={() => onAdd(interest)}
            style={{
              backgroundColor: c.sandMid,
              border: `1px solid ${c.sandBorder}`,
              borderRadius: "20px",
              color: c.stoneLight,
              padding: "4px 11px",
              fontSize: "12px",
              cursor: "pointer",
              fontFamily: f.sans,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = c.tealLight;
              e.currentTarget.style.borderColor = c.tealBorder;
              e.currentTarget.style.color = c.teal;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = c.sandMid;
              e.currentTarget.style.borderColor = c.sandBorder;
              e.currentTarget.style.color = c.stoneLight;
            }}
          >{interest}</button>
        ))}
      </div>
    </div>
  );
}