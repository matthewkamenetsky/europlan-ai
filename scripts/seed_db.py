import sqlite3
import pandas as pd
# import requests
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/europlan.db"
CITIES_CSV = "data/cities.csv"
OPENTRIPMAP_KEY = os.getenv("OPENTRIPMAP_KEY")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.executescript("""
    CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        asciiname TEXT,
        alternatenames TEXT,
        country_code TEXT NOT NULL,
        population INTEGER,
        lat REAL NOT NULL,
        lon REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS attractions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city_name TEXT NOT NULL,
        country_code TEXT NOT NULL,
        category TEXT,
        rating REAL,
        lat REAL,
        lon REAL
    );
""")

conn.commit()
print("Tables created.")

df = pd.read_csv(CITIES_CSV)
df.to_sql("cities", conn, if_exists="replace", index=False)
print(f"Inserted {len(df)} cities.")

# def get_attractions(city_name, lat, lon, country_code, radius=10000):
#     url = "https://api.opentripmap.com/0.1/en/places/radius"
#     params = {
#         "radius": radius,
#         "lon": lon,
#         "lat": lat,
#         "kinds": "cultural,historic,museums,architecture,natural",
#         "rate": "3",
#         "format": "json",
#         "limit": 20,
#         "apikey": OPENTRIPMAP_KEY
#     }
#     try:
#         response = requests.get(url, params=params, timeout=10)
#         data = response.json()
#         attractions = []
#         for place in data:
#             attractions.append({
#                 "name": place.get("name", "Unknown"),
#                 "city_name": city_name,
#                 "country_code": country_code,
#                 "category": place.get("kinds", "").split(",")[0],
#                 "rating": place.get("rate", 0),
#                 "lat": place.get("point", {}).get("lat"),
#                 "lon": place.get("point", {}).get("lon"),
#             })
#         return attractions
#     except Exception as e:
#         print(f"Failed to fetch attractions for {city_name}: {e}")
#         return []

# cities_df = pd.read_csv(CITIES_CSV)
# all_attractions = []

# for _, row in cities_df.iterrows():
#     print(f"Fetching attractions for {row['name']}...")
#     attractions = get_attractions(
#         row["name"], row["lat"], row["lon"], row["country_code"]
#     )
#     all_attractions.extend(attractions)

# if all_attractions:
#     attractions_df = pd.DataFrame(all_attractions)
#     attractions_df.to_sql("attractions", conn, if_exists="replace", index=False)
#     print(f"Inserted {len(all_attractions)} attractions.")

conn.close()
print("Database seeded successfully.")