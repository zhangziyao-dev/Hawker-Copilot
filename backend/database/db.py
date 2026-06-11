import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "data/hawker_copilot.db"


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id TEXT,
            item_name TEXT NOT NULL,
            forecast_date TEXT NOT NULL,
            predicted_quantity REAL,
            recommended_prep_quantity INTEGER,
            confidence_level TEXT,
            confidence_percentage REAL,
            waste_risk TEXT,
            shortage_risk TEXT,
            recommendation_text TEXT,
            historical_context TEXT,
            primary_factors TEXT,
            model_used TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id TEXT PRIMARY KEY,
            stall_name TEXT NOT NULL,
            hawker_centre TEXT,
            area_type TEXT,
            items TEXT,
            avg_price_sgd REAL,
            daily_capacity INTEGER,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            city TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            weather_condition TEXT,
            rain_probability REAL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


def save_recommendation(rec: dict):
    """Persist a recommendation to SQLite."""
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recommendations (
            vendor_id, item_name, forecast_date,
            predicted_quantity, recommended_prep_quantity,
            confidence_level, confidence_percentage,
            waste_risk, shortage_risk,
            recommendation_text, historical_context,
            primary_factors, model_used, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rec.get("vendor_id"),
        rec["item_name"],
        str(rec["forecast_date"]),
        rec["predicted_quantity"],
        rec["recommended_prep_quantity"],
        rec["confidence_level"],
        rec.get("confidence_percentage", 0),
        rec["waste_risk"],
        rec["shortage_risk"],
        rec["recommendation_text"],
        rec["historical_context"],
        json.dumps(rec["primary_factors"]),
        rec["model_used"],
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_recommendation_history(vendor_id: str = None, limit: int = 30) -> list:
    """Fetch past recommendations, optionally filtered by vendor."""
    import json
    conn = get_connection()
    cursor = conn.cursor()

    if vendor_id:
        cursor.execute("""
            SELECT * FROM recommendations
            WHERE vendor_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (vendor_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM recommendations
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        r = dict(row)
        r["primary_factors"] = json.loads(r["primary_factors"] or "[]")
        results.append(r)
    return results