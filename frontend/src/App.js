import { useState, useEffect } from "react";
import TripsOverview from "./components/TripsOverview";
import TripPlanner from "./components/TripPlanner";
import { parseDays } from "./utils/parseDays";
import { c, f } from "./styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

function normaliseTrip(raw) {
  return {
    id: raw.id,
    tripId: raw.id,
    label: raw.name,
    params: {
      cities: raw.cities,
      tripLength: raw.trip_length,
      interests: raw.interests,
    },
    days: [],
    loading: false,
  };
}

export default function App() {
  const [view, setView] = useState("overview");
  const [trips, setTrips] = useState(null);
  const [activeTripId, setActiveTripId] = useState(null);
  const [activeTrip, setActiveTrip] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/trips`)
      .then(r => r.json())
      .then(data => setTrips(data.map(normaliseTrip)))
      .catch(() => setTrips([]));
  }, []);

  const createTrip = (params) => {
    const tempId = Date.now();
    const newTrip = {
      id: tempId,
      tripId: null,
      label: params.cities.join(" · "),
      params,
      days: [],
      loading: false,
    };
    setTrips(prev => [...(prev || []), newTrip]);
    setActiveTrip(newTrip);
    setActiveTripId(tempId);
    setView("planner");
    return tempId;
  };

  const updateTrip = (id, updater) => {
    setTrips(prev => (prev || []).map(t => t.id === id ? updater(t) : t));
    setActiveTrip(prev => prev?.id === id ? updater(prev) : prev);
  };

  const openTrip = async (id) => {
    try {
      const r = await fetch(`${API_BASE}/trips/${id}`);
      const data = await r.json();
      const base = (trips || []).find(t => t.id === id) || normaliseTrip(data);
      const trip = { ...base };
      if (data.itinerary) {
        trip.days = parseDays(data.itinerary, data.trip_length);
      }
      setActiveTrip(trip);
    } catch {
      const base = (trips || []).find(t => t.id === id) || null;
      setActiveTrip(base);
    }
    setActiveTripId(id);
    setView("planner");
  };

  const deleteTrip = (id) => {
    setTrips(prev => (prev || []).filter(t => t.id !== id));
  };

  if (trips === null) {
    return (
      <div style={{
        minHeight: "100vh",
        backgroundColor: c.sand,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          color: c.stoneFaint, fontFamily: f.sans, fontSize: "14px",
        }}>
          <div style={{
            width: "7px", height: "7px", borderRadius: "50%",
            backgroundColor: c.teal, animation: "ep-pulse 1s infinite",
          }} />
          Loading your trips…
        </div>
        <style>{`@keyframes ep-pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }`}</style>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: c.paper,
      fontFamily: f.sans,
      color: c.ink,
    }}>
      {view === "overview" && (
        <TripsOverview
          trips={trips}
          onCreate={createTrip}
          onOpen={openTrip}
          onDelete={deleteTrip}
        />
      )}
      {view === "planner" && activeTrip && (
        <TripPlanner
          trip={activeTrip}
          onBack={() => { setView("overview"); setActiveTrip(null); }}
          onUpdate={(updater) => updateTrip(activeTripId, updater)}
        />
      )}
    </div>
  );
}