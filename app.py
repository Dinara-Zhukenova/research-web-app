from csv import writer
from datetime import datetime
from io import StringIO
import json
import os
import random
import sqlite3
import threading
import time

from flask import Flask, Response, jsonify, render_template
import paho.mqtt.client as mqtt


app = Flask(__name__)

DATABASE = "lighting.db"
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = "lighting/sensor/data"

lighting_on = True
control_mode = "conventional"
latest_mqtt_data = None
latest_mqtt_time = 0
mqtt_lock = threading.Lock()
mqtt_client = None


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
    connection.execute("""
        CREATE TABLE IF NOT EXISTS research_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL,
            control_mode TEXT NOT NULL,
            voltage REAL NOT NULL,
            current REAL NOT NULL,
            power REAL NOT NULL,
            lighting_on INTEGER NOT NULL
        )
    """)
    connection.commit()
    connection.close()


def save_event(event_type):
    connection = get_database()
    connection.execute(
        """
        INSERT INTO events (created_at, event_type, lighting_on)
        VALUES (?, ?, ?)
        """,
        (datetime.now().isoformat(timespec="seconds"), event_type, int(lighting_on)),
    )
    connection.commit()
    connection.close()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"MQTT connected: {MQTT_HOST}:{MQTT_PORT}", flush=True)
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"MQTT connection failed: {reason_code}", flush=True)


def on_message(client, userdata, message):
    global latest_mqtt_data, latest_mqtt_time
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        data = {
            "voltage": round(float(payload["voltage"]), 1),
            "current": round(float(payload["current"]), 2),
            "power": round(float(payload["power"]), 1),
            "lux": round(float(payload.get("lux", 0)), 1),
        }
        with mqtt_lock:
            latest_mqtt_data = data
            latest_mqtt_time = time.time()
        print(f"MQTT data received: {data}", flush=True)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"Invalid MQTT message: {error}", flush=True)


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


def publish_mqtt_command(topic, value):
    if mqtt_client is not None:
        mqtt_client.publish(topic, value, qos=1, retain=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    with mqtt_lock:
        mqtt_data = dict(latest_mqtt_data) if latest_mqtt_data else None
        mqtt_age = time.time() - latest_mqtt_time if latest_mqtt_time else None

    if mqtt_data and mqtt_age is not None and mqtt_age < 30:
        voltage = mqtt_data["voltage"]
        current = mqtt_data["current"] if lighting_on else 0
        power = mqtt_data["power"] if lighting_on else 0
        lux = mqtt_data["lux"]
        data_source = "mqtt"
    else:
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
        lux = round(random.uniform(20, 70), 1)
        data_source = "simulation"

    conventional_power = round(voltage * 3.2, 1)
    savings = 0
    if lighting_on and control_mode == "adaptive" and conventional_power > 0:
        savings = round((conventional_power - power) / conventional_power * 100, 1)

    measured_at = datetime.now().isoformat(timespec="seconds")
    connection = get_database()
    connection.execute(
        """
        INSERT INTO measurements
        (measured_at, voltage, current, power, lighting_on)
        VALUES (?, ?, ?, ?, ?)
        """,
        (measured_at, voltage, current, power, int(lighting_on)),
    )
    connection.execute(
        """
        INSERT INTO research_measurements
        (measured_at, control_mode, voltage, current, power, lighting_on)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (measured_at, control_mode, voltage, current, power, int(lighting_on)),
    )
    connection.commit()
    connection.close()

    return jsonify({
        "measured_at": measured_at,
        "voltage": voltage,
        "current": current,
        "power": power,
        "lux": lux,
        "lighting_on": lighting_on,
        "control_mode": control_mode,
        "savings": savings,
        "data_source": data_source,
        "device_online": mqtt_age is not None and mqtt_age < 15,
        "last_message_seconds": (
            round(mqtt_age, 1) if mqtt_age is not None else None
        ),
    })


@app.route("/api/light/on", methods=["POST"])
def turn_on():
    global lighting_on
    lighting_on = True
    publish_mqtt_command("lighting/control/light", "on")
    save_event("Команда включения")
    return jsonify({"lighting_on": lighting_on})


@app.route("/api/light/off", methods=["POST"])
def turn_off():
    global lighting_on
    lighting_on = False
    publish_mqtt_command("lighting/control/light", "off")
    save_event("Команда выключения")
    return jsonify({"lighting_on": lighting_on})


@app.route("/api/mode/<mode>", methods=["POST"])
def change_mode(mode):
    global control_mode
    if mode not in ("conventional", "adaptive"):
        return jsonify({"error": "Неизвестный режим"}), 400
    control_mode = mode
    publish_mqtt_command("lighting/control/mode", mode)
    if mode == "adaptive":
        save_event("Включён адаптивный IoT-режим")
    else:
        save_event("Включён обычный режим")
    return jsonify({"control_mode": control_mode})


@app.route("/api/history")
def history():
    connection = get_database()
    rows = connection.execute(
        """
        SELECT measured_at, voltage, current, power, lighting_on
        FROM measurements ORDER BY id DESC LIMIT 30
        """
    ).fetchall()
    connection.close()
    return jsonify([dict(row) for row in reversed(rows)])


@app.route("/api/comparison")
def comparison():
    connection = get_database()
    rows = connection.execute(
        """
        SELECT control_mode, COUNT(*) AS sample_count,
               AVG(power) AS average_power
        FROM research_measurements
        WHERE lighting_on = 1
        GROUP BY control_mode
        """
    ).fetchall()
    connection.close()
    result = {
        "conventional": {"sample_count": 0, "average_power": 0},
        "adaptive": {"sample_count": 0, "average_power": 0},
        "savings_percent": 0,
    }
    for row in rows:
        result[row["control_mode"]] = {
            "sample_count": row["sample_count"],
            "average_power": round(row["average_power"], 1),
        }
    conventional = result["conventional"]["average_power"]
    adaptive = result["adaptive"]["average_power"]
    if conventional > 0 and adaptive > 0:
        result["savings_percent"] = round(
            (conventional - adaptive) / conventional * 100, 1
        )
    return jsonify(result)


@app.route("/api/export")
def export_measurements():
    connection = get_database()
    rows = connection.execute(
        """
        SELECT measured_at, control_mode, voltage, current, power, lighting_on
        FROM research_measurements ORDER BY id
        """
    ).fetchall()
    connection.close()
    output = StringIO()
    output.write("\ufeff")
    csv_writer = writer(output)
    csv_writer.writerow([
        "Дата и время", "Режим", "Напряжение, В", "Ток, А",
        "Мощность, Вт", "Освещение включено",
    ])
    for row in rows:
        mode_name = (
            "Адаптивный IoT"
            if row["control_mode"] == "adaptive"
            else "Таймер / фотореле"
        )
        csv_writer.writerow([
            row["measured_at"], mode_name, row["voltage"], row["current"],
            row["power"], "Да" if row["lighting_on"] else "Нет",
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=lighting_measurements.csv"},
    )


create_database()


if __name__ == "__main__":
    mqtt_client = start_mqtt()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
