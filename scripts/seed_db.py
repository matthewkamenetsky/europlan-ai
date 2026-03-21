import sqlite3
import pandas as pd

DB_PATH = "backend/data/europlan.db"
CITIES_CSV = "backend/data/cities.csv"

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

    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cities TEXT NOT NULL,
        trip_length INTEGER NOT NULL,
        interests TEXT NOT NULL,
        itinerary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
print("Tables created.")

df = pd.read_csv(CITIES_CSV)
df.to_sql("cities", conn, if_exists="replace", index=False)
print(f"Inserted {len(df)} cities.")

conn.close()
print("Database seeded successfully.")