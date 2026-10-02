from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)

lighting_on = True


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

    return jsonify({
        "voltage": voltage,
        "current": current,
        "power": power,
        "lighting_on": lighting_on
    })


@app.route("/api/light/on", methods=["POST"])
def turn_on():
    global lighting_on
    lighting_on = True
    return jsonify({"lighting_on": lighting_on})


@app.route("/api/light/off", methods=["POST"])
def turn_off():
    global lighting_on
    lighting_on = False
    return jsonify({"lighting_on": lighting_on})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)