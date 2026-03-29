import sqlite3
conn = sqlite3.connect("backend/data/europlan.db")
conn.execute("ALTER TABLE trips ADD COLUMN conversation TEXT NULL;")
conn.commit()
conn.close()
print("Done.")