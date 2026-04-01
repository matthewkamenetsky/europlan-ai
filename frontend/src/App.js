import { useState, useEffect, useRef } from "react";
import TripsOverview from "./components/TripsOverview";
import TripPlanner from "./components/TripPlanner";
import { parseDays } from "./utils/parseDays";
import { c, f } from "./styles";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

function tryParseJsonArray(s) {
  try {
    const v = JSON.parse(s);
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function idsMatch(a, b) {
  if (a === b) return true;
  if (a == null || b == null) return false;
  return Number(a) === Number(b);
}

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
    conversation: Array.isArray(raw.conversation) ? raw.conversation : [],
  };
}

export default function App() {
  const [view, setView] = useState("overview");
  const [trips, setTrips] = useState(null);
  const [activeTripId, setActiveTripId] = useState(null);
  const [activeTrip, setActiveTrip] = useState(null);
  const activeTripIdRef = useRef(null);
  activeTripIdRef.current = activeTripId;

  const refreshTrips = () => {
    fetch(`${API_BASE}/trips`)
      .then(r => r.json())
      .then(data => setTrips(data.map(normaliseTrip)))
      .catch(() => setTrips([]));
  };

  useEffect(() => {
    if (view !== "overview") return;
    refreshTrips();
  }, [view]);

  const createTrip = (params) => {
    const tempId = Date.now();
    const newTrip = {
      id: tempId,
      tripId: null,
      label: params.cities.join(" · "),
      params,
      days: [],
      loading: false,
      conversation: [],
    };
    setTrips(prev => [...(prev || []), newTrip]);
    setActiveTrip(newTrip);
    setActiveTripId(tempId);
    setView("planner");
    return tempId;
  };

  const updateTripForActive = (updater) => {
    const key = activeTripIdRef.current;
    setTrips(prev => (prev || []).map(t => (t.id === key ? updater(t) : t)));
    setActiveTrip(prev => (prev && prev.id === key ? updater(prev) : prev));
  };

  const resolveTripServerId = (serverId, clientId) => {
    setTrips(prev =>
      (prev || []).map(t =>
        t.id === clientId ? { ...t, id: serverId, tripId: serverId } : t,
      ),
    );
    setActiveTrip(prev =>
      prev && prev.id === clientId ? { ...prev, id: serverId, tripId: serverId } : prev,
    );
    setActiveTripId(prev => (prev === clientId ? serverId : prev));
  };

  const openTrip = async (id) => {
    const idNum = typeof id === "string" ? parseInt(id, 10) : id;
    const list = trips || [];
    const local = list.find(
      t => idsMatch(t.id, id) || idsMatch(t.id, idNum) || idsMatch(t.tripId, id) || idsMatch(t.tripId, idNum),
    );
    let fetchId = Number.isNaN(idNum) ? id : idNum;
    if (local?.tripId != null && !idsMatch(local.id, local.tripId) && (idsMatch(local.id, id) || idsMatch(local.id, idNum))) {
      fetchId = local.tripId;
    }

    try {
      let r = await fetch(`${API_BASE}/trips/${fetchId}`);
      if (!r.ok && local?.tripId != null && !idsMatch(fetchId, local.tripId)) {
        r = await fetch(`${API_BASE}/trips/${local.tripId}`);
      }
      if (!r.ok) {
        refreshTrips();
        const base = local || null;
        setActiveTrip(base);
        setActiveTripId(id);
        setView("planner");
        return;
      }
      const data = await r.json();
      const serverId = data.id;

      const rawConv = data.conversation;
      let conversation = [];
      if (Array.isArray(rawConv)) {
        conversation = rawConv;
      } else if (typeof rawConv === "string") {
        conversation = tryParseJsonArray(rawConv);
      }

      const trip = {
        id: serverId,
        tripId: serverId,
        label: data.name,
        params: {
          cities: data.cities,
          tripLength: data.trip_length,
          interests: data.interests,
        },
        days: [],
        loading: false,
        conversation,
      };
      if (data.itinerary) {
        trip.days = parseDays(data.itinerary, data.trip_length);
      }

      setTrips(prev => {
        const p = prev || [];
        const idx = p.findIndex(
          t => idsMatch(t.id, id) || idsMatch(t.id, serverId) || idsMatch(t.tripId, serverId),
        );
        if (idx === -1) {
          return [...p, trip];
        }
        return p.map((t, i) => (i === idx ? trip : t));
      });
      setActiveTrip(trip);
      setActiveTripId(serverId);
      setView("planner");
      return;
    } catch {
      const base = list.find(t => idsMatch(t.id, id)) || null;
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
          onUpdate={updateTripForActive}
          onTripServerIdResolved={resolveTripServerId}
        />
      )}
    </div>
  );
}