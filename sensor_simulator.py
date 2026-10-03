import json
import random
import time

import paho.mqtt.client as mqtt


DEVICE_ID = "ESP32-S3-URALS-001"
lighting_on = True
control_mode = "conventional"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("ESP32-S3 simulator connected to MQTT", flush=True)
        client.subscribe("lighting/control/#")
        client.publish("lighting/device/status", "online", retain=True)


def on_message(client, userdata, message):
    global lighting_on, control_mode
    value = message.payload.decode("utf-8")

    if message.topic == "lighting/control/light":
        lighting_on = value == "on"
        print(f"Light command received: {value}", flush=True)

    if message.topic == "lighting/control/mode" and value in (
        "conventional",
        "adaptive",
    ):
        control_mode = value
        print(f"Control mode received: {value}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        client.connect("mqtt", 1883, 60)
        break
    except OSError:
        print("Waiting for MQTT broker...", flush=True)
        time.sleep(3)

client.loop_start()

while True:
    voltage = round(random.uniform(218, 223), 1)
    lux = round(random.uniform(20, 70), 1)

    if not lighting_on:
        current = 0
    elif control_mode == "conventional":
        current = round(random.uniform(3.0, 3.4), 2)
    elif lux < 30:
        current = round(random.uniform(2.4, 2.6), 2)
    elif lux < 50:
        current = round(random.uniform(2.0, 2.3), 2)
    else:
        current = round(random.uniform(1.7, 1.9), 2)

    power = round(voltage * current, 1)
    data = {
        "device_id": DEVICE_ID,
        "voltage": voltage,
        "current": current,
        "power": power,
        "lux": lux,
        "lighting_on": lighting_on,
        "control_mode": control_mode,
    }
    client.publish("lighting/sensor/data", json.dumps(data), qos=1)
    print(f"ESP32-S3 telemetry: {data}", flush=True)
    time.sleep(5)
