import { useState } from "react";
import NewTripModal from "./NewTripModal";
import { c, f } from "../styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function TripsOverview({ trips, onCreate, onOpen, onDelete }) {
  const [showModal, setShowModal] = useState(false);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: c.sand }}>

      <nav style={{
        borderBottom: `1px solid ${c.sandBorder}`, padding: "0 48px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: "60px", backgroundColor: c.white,
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
          <span style={{ fontFamily: f.display, fontSize: "22px", fontWeight: 700, color: c.teal, letterSpacing: "0.01em" }}>Europlan</span>
          <span style={{ fontFamily: f.mono, fontSize: "10px", color: c.stoneFaint, letterSpacing: "0.1em" }}>AI TRAVEL PLANNER</span>
        </div>
        <button
          onClick={() => setShowModal(true)}
          style={{ display: "flex", alignItems: "center", gap: "7px", padding: "8px 18px", borderRadius: "8px", border: "none", backgroundColor: c.teal, color: c.white, fontSize: "13px", fontWeight: 600, fontFamily: f.sans, cursor: "pointer" }}
        >
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
            <line x1="6" y1="1" x2="6" y2="11" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="1" y1="6" x2="11" y2="6" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          Plan new trip
        </button>
      </nav>

      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "52px 32px" }}>
        <h1 style={{ fontFamily: f.display, fontSize: "46px", fontWeight: 700, color: c.stone, margin: "0 0 10px", letterSpacing: "-0.01em", lineHeight: 1.1 }}>Your trips</h1>
        <p style={{ fontFamily: f.body, fontSize: "17px", color: c.stoneLight, margin: "0 0 44px", lineHeight: 1.6 }}>
          {trips.length === 0 ? "No trips yet — start planning your European adventure." : `${trips.length} trip${trips.length !== 1 ? "s" : ""} planned.`}
        </p>

        {trips.length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "20px" }}>
            {trips.map(trip => <TripCard key={trip.id} trip={trip} onOpen={onOpen} onDelete={onDelete} />)}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "72px 0", gap: "20px" }}>
            <div style={{ width: "72px", height: "72px", borderRadius: "50%", backgroundColor: c.tealLight, border: `1px solid ${c.tealBorder}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                <circle cx="15" cy="15" r="11" stroke={c.teal} strokeWidth="1.5" fill="none"/>
                <circle cx="15" cy="15" r="2" fill={c.teal}/>
                <path d="M15 4v3M15 23v3M4 15h3M23 15h3" stroke={c.teal} strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M11 11l2.5 4 4-2.5-2.5-4L11 11z" fill={c.teal} opacity="0.5"/>
              </svg>
            </div>
            <p style={{ fontFamily: f.body, fontSize: "17px", color: c.stoneFaint, margin: 0, textAlign: "center" }}>Ready to explore Europe?</p>
            <button
              onClick={() => setShowModal(true)}
              style={{ padding: "10px 22px", borderRadius: "8px", border: `1px solid ${c.tealBorder}`, backgroundColor: c.tealLight, color: c.teal, fontSize: "13px", fontWeight: 600, fontFamily: f.sans, cursor: "pointer" }}
            >Plan my first trip →</button>
          </div>
        )}
      </div>

      {showModal && (
        <NewTripModal
          onClose={() => setShowModal(false)}
          onCreate={(params) => { setShowModal(false); onCreate(params); }}
        />
      )}
    </div>
  );
}

function TripCard({ trip, onOpen, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete "${trip.label}"?`)) return;
    setDeleting(true);
    try {
      await fetch(`${API_BASE}/trips/${trip.id}`, { method: "DELETE" });
      onDelete(trip.id);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => onOpen(trip.id)}
        style={{ textAlign: "left", backgroundColor: c.white, border: `1px solid ${c.sandBorder}`, borderRadius: "12px", padding: "22px 24px", cursor: "pointer", fontFamily: f.sans, width: "100%", transition: "box-shadow 0.15s, transform 0.15s" }}
        onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 4px 20px rgba(26,107,107,0.1)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
        onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
      >
        <div style={{ height: "3px", borderRadius: "2px", backgroundColor: c.tealBright, marginBottom: "16px", width: "36px" }} />
        <p style={{ fontFamily: f.display, fontSize: "18px", fontWeight: 700, color: c.stone, margin: "0 0 5px", letterSpacing: "0.01em" }}>{trip.label}</p>
        <p style={{ fontSize: "11px", color: c.stoneFaint, margin: "0 0 14px", fontFamily: f.mono }}>
          {trip.params.tripLength} days
          {trip.params.interests.length > 0 && ` · ${trip.params.interests.slice(0, 2).join(", ")}`}
          {trip.params.interests.length > 2 && ` +${trip.params.interests.length - 2}`}
        </p>
        <span style={{ fontSize: "12px", color: c.teal, fontWeight: 600, fontFamily: f.sans }}>View itinerary →</span>
      </button>

      <button
        onClick={handleDelete}
        disabled={deleting}
        title="Delete trip"
        style={{ position: "absolute", top: "12px", right: "12px", width: "26px", height: "26px", borderRadius: "6px", border: `1px solid ${c.sandBorder}`, backgroundColor: c.white, color: c.stoneLight, display: "flex", alignItems: "center", justifyContent: "center", cursor: deleting ? "not-allowed" : "pointer", opacity: deleting ? 0.4 : 1, padding: 0 }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "#e57373"; e.currentTarget.style.color = "#e57373"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = c.sandBorder; e.currentTarget.style.color = c.stoneLight; }}
      >
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
          <path d="M2 3h8M5 3V2h2v1M4.5 3v6.5h3V3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  );
}