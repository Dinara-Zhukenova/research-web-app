import json
import random
import time

import paho.mqtt.client as mqtt


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

while True:
    try:
        client.connect("mqtt", 1883, 60)
        break
    except OSError:
        print("Ожидание MQTT-брокера...")
        time.sleep(3)

while True:
    voltage = round(random.uniform(218, 223), 1)
    current = round(random.uniform(1.8, 2.6), 2)
    power = round(voltage * current, 1)
    lux = round(random.uniform(20, 70), 1)

    data = {
        "voltage": voltage,
        "current": current,
        "power": power,
        "lux": lux,
    }

    client.publish(
        "lighting/sensor/data",
        json.dumps(data),
    )

    print(f"Отправлены данные: {data}", flush=True)
    time.sleep(5)