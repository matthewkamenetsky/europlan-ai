from math import radians, sin, cos, sqrt, atan2

TRAIN_KMH = 120

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def format_travel_time(dist_km: float) -> str:
    total_minutes = round(dist_km / TRAIN_KMH * 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes}min"
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}min"