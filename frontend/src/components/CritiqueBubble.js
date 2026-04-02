import { c, f } from "../styles";

const scoreColour = (v) => v >= 7 ? c.teal : v >= 5 ? "#b07d10" : "#c0392b";
const scoreBg     = (v) => v >= 7 ? c.tealLight : v >= 5 ? "#fef6e4" : "#fff5f5";
const scoreBorder = (v) => v >= 7 ? c.tealBorder : v >= 5 ? "#f0d080" : "#fecaca";

export default function CritiqueBubble({ critique }) {
  const scores = [
    { label: "Realism",    value: critique.realism_score },
    { label: "Pacing",     value: critique.pacing_score },
    { label: "Preference", value: critique.preference_score },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontFamily: f.sans, fontSize: "11px", fontWeight: 600, color: c.stoneLight, letterSpacing: "0.07em", textTransform: "uppercase" }}>Critique</span>
        <span style={{ fontFamily: f.mono, fontSize: "20px", fontWeight: 700, color: scoreColour(critique.overall_score) }}>
          {critique.overall_score.toFixed(1)}
          <span style={{ fontSize: "11px", fontWeight: 400, color: c.stoneFaint }}>/10</span>
        </span>
      </div>

      <div style={{ display: "flex", gap: "7px", flexWrap: "wrap" }}>
        {scores.map(({ label, value }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "5px", padding: "3px 10px", borderRadius: "20px", backgroundColor: scoreBg(value), border: `1px solid ${scoreBorder(value)}` }}>
            <span style={{ fontFamily: f.sans, fontSize: "11px", color: c.stoneLight }}>{label}</span>
            <span style={{ fontFamily: f.mono, fontSize: "12px", fontWeight: 700, color: scoreColour(value) }}>{value}/10</span>
          </div>
        ))}
      </div>

      <div style={{ height: "1px", backgroundColor: c.sandBorder }} />

      {critique.issues?.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
          <span style={{ fontFamily: f.sans, fontSize: "11px", fontWeight: 600, color: c.stoneLight, letterSpacing: "0.07em", textTransform: "uppercase" }}>Issues</span>
          {critique.issues.map((issue, i) => (
            <div key={i} style={{ display: "flex", gap: "9px", alignItems: "flex-start" }}>
              <span style={{ marginTop: "6px", width: "5px", height: "5px", borderRadius: "50%", backgroundColor: "#e05252", flexShrink: 0 }} />
              <span style={{ fontFamily: f.body, fontSize: "13px", color: c.stoneMid, lineHeight: 1.55 }}>{issue}</span>
            </div>
          ))}
        </div>
      )}

      {critique.recommendations?.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
          <span style={{ fontFamily: f.sans, fontSize: "11px", fontWeight: 600, color: c.stoneLight, letterSpacing: "0.07em", textTransform: "uppercase" }}>Recommendations</span>
          {critique.recommendations.map((rec, i) => (
            <div key={i} style={{ display: "flex", gap: "9px", alignItems: "flex-start" }}>
              <span style={{ marginTop: "6px", width: "5px", height: "5px", borderRadius: "50%", backgroundColor: c.teal, flexShrink: 0 }} />
              <span style={{ fontFamily: f.body, fontSize: "13px", color: c.stoneMid, lineHeight: 1.55 }}>{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}