import sqlite3
import pandas as pd

# Step 1: Connect to SQLite database (or create it)
conn = sqlite3.connect("brick_timeseries.db")
cursor = conn.cursor()

# Step 2: Create tables for timeseries data and metadata
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS TimeseriesData (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    value REAL NOT NULL,
    fc1_flag INTEGER DEFAULT 0  -- Add this line to store fault condition 1 flags
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS TimeseriesReference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeseries_id TEXT NOT NULL,
    stored_at TEXT NOT NULL
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS DatabaseStorage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    connstring TEXT NOT NULL
)
"""
)

# Step 3: Insert database metadata (SQLite reference)
cursor.execute(
    """
INSERT INTO DatabaseStorage (label, connstring)
VALUES
    ('SQLite Timeseries Storage', 'sqlite:///brick_timeseries.db')
"""
)

# Step 4: Load the CSV data
csv_file = r"C:\Users\bbartling\Documents\WPCRC_Master.csv"
df = pd.read_csv(csv_file)
print("df.columns", df.columns)

print("Starting step 5")

# Step 5: Insert CSV data into the TimeseriesData table
for column in df.columns:
    for index, row in df.iterrows():
        cursor.execute(
            """
        INSERT INTO TimeseriesData (sensor_name, timestamp, value)
        VALUES (?, ?, ?)
        """,
            (column, index, row[column]),
        )
    print(f"Doing {column} in step 5")

conn.commit()

print("Starting step 6")

# Step 6: Insert timeseries references based on sensor names
for column in df.columns:
    cursor.execute(
        """
    INSERT INTO TimeseriesReference (timeseries_id, stored_at)
    VALUES (?, ?)
    """,
        (column, "SQLite Timeseries Storage"),
    )

    print(f"Doing {column} in step 6")

conn.commit()

print("Step 6 is done")

# Close the connection
conn.close()

print("SQLite database created and populated with CSV data.")