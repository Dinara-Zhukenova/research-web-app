from flask import Flask, render_template, jsonify, Response
from datetime import datetime
import random
import sqlite3
import csv
import io
app = Flask(__name__)

DATABASE = "lighting.db"
lighting_on = True
control_mode = "conventional"


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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    voltage = round(random.uniform(218, 223), 1)

    if lighting_on:
        if control_mode == "adaptive":
            current = round(random.uniform(1.8, 2.6), 2)
        else:
            current = round(random.uniform(3.0, 3.4), 2)

        power = round(voltage * current, 1)
    else:
        current = 0
        power = 0

    conventional_power = round(voltage * 3.2, 1)
    savings = 0

    if lighting_on and control_mode == "adaptive":
        savings = round(
            (conventional_power - power)
            / conventional_power
            * 100,
            1
        )

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
        "lighting_on": lighting_on,
        "control_mode": control_mode,
        "savings": savings
    })


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


@app.route("/api/mode/<mode>", methods=["POST"])
def change_mode(mode):
    global control_mode

    if mode not in ("conventional", "adaptive"):
        return jsonify({
            "error": "Неизвестный режим"
        }), 400

    control_mode = mode

    if mode == "adaptive":
        save_event("Включён адаптивный IoT-режим")
    else:
        save_event("Включён обычный режим")

    return jsonify({
        "control_mode": control_mode
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

@app.route("/api/export")
def export_measurements():
    connection = get_database()

    rows = connection.execute(
        """
        SELECT measured_at, voltage, current, power, lighting_on
        FROM measurements
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    output = io.StringIO()
    output.write("\ufeff")

    writer = csv.writer(output)

    writer.writerow([
        "Дата и время",
        "Напряжение, В",
        "Ток, А",
        "Мощность, Вт",
        "Освещение включено"
    ])

    for row in rows:
        writer.writerow([
            row["measured_at"],
            row["voltage"],
            row["current"],
            row["power"],
            "Да" if row["lighting_on"] else "Нет"
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=lighting_measurements.csv"
        }
    )
create_database()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )