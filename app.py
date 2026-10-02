from flask import Flask, render_template, jsonify
from datetime import datetime
import random
import sqlite3

app = Flask(__name__)

DATABASE = "lighting.db"
lighting_on = True


def get_database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_database()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL,
            voltage REAL NOT NULL,
            current REAL NOT NULL,
            power REAL NOT NULL,
            lighting_on INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            lighting_on INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    voltage = round(random.uniform(218, 223), 1)

    if lighting_on:
        current = round(random.uniform(3.0, 3.4), 2)
        power = round(voltage * current, 1)
    else:
        current = 0
        power = 0

    measured_at = datetime.now().isoformat(timespec="seconds")

    connection = get_database()

    connection.execute(
        """
        INSERT INTO measurements
        (measured_at, voltage, current, power, lighting_on)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            measured_at,
            voltage,
            current,
            power,
            int(lighting_on)
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "measured_at": measured_at,
        "voltage": voltage,
        "current": current,
        "power": power,
        "lighting_on": lighting_on
    })


def save_event(event_type):
    connection = get_database()

    connection.execute(
        """
        INSERT INTO events
        (created_at, event_type, lighting_on)
        VALUES (?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            event_type,
            int(lighting_on)
        )
    )

    connection.commit()
    connection.close()


@app.route("/api/light/on", methods=["POST"])
def turn_on():
    global lighting_on
    lighting_on = True
    save_event("Команда включения")

    return jsonify({
        "lighting_on": lighting_on
    })


@app.route("/api/light/off", methods=["POST"])
def turn_off():
    global lighting_on
    lighting_on = False
    save_event("Команда выключения")

    return jsonify({
        "lighting_on": lighting_on
    })


@app.route("/api/history")
def history():
    connection = get_database()

    rows = connection.execute(
        """
        SELECT measured_at, voltage, current, power, lighting_on
        FROM measurements
        ORDER BY id DESC
        LIMIT 30
        """
    ).fetchall()

    connection.close()

    return jsonify([
        dict(row) for row in reversed(rows)
    ])


create_database()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )