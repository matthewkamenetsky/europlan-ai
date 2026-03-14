import pandas as pd

cols = [
    "geonameid", "name", "asciiname", "alternatenames",
    "lat", "lon", "feature_class", "feature_code",
    "country_code", "cc2", "admin1", "admin2", "admin3", "admin4",
    "population", "elevation", "dem", "timezone", "modified"
]

schengen_codes = {
    "DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "CZ",
    "DK", "SE", "FI", "LU", "SI", "SK", "HU", "HR", "NO",
    "CH", "IS", "LI", "MT", "EE", "LV", "LT", "BG", "RO",
    "GR", "PT", "MC", "VA"
}

df = pd.read_csv(
    "data/cities15000.txt",
    sep="\t",
    header=None,
    names=cols,
    low_memory=False
)

df = df[df["country_code"].isin(schengen_codes)]
df = df[df["population"] > 30000]
df = df[["name", "asciiname", "alternatenames", "country_code", "population", "lat", "lon"]]

manual = pd.DataFrame([
    {"name": "Vatican City", "asciiname": "Vatican City", "alternatenames": "Holy See,Vatican", "country_code": "VA", "population": 800,  "lat": 41.9029, "lon": 12.4534},
])

combined = pd.concat([df, manual])
combined = combined.drop_duplicates(subset=["name", "country_code"])
combined = combined.sort_values("population", ascending=False)
combined.to_csv("data/cities.csv", index=False)

print(f"Total cities: {len(combined)}")