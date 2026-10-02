const powerHistory = [];


async function updateData() {
    try {
        const response = await fetch("/api/data");
        const data = await response.json();

        document.getElementById("voltage").textContent = data.voltage;
        document.getElementById("current").textContent = data.current;
        document.getElementById("power").textContent = data.power;

        const status = document.getElementById("status");

        if (data.lighting_on) {
            status.textContent = "Освещение включено";
            status.className = "value status status-on";
        } else {
            status.textContent = "Освещение выключено";
            status.className = "value status status-off";
        }

        powerHistory.push(data.power);

        if (powerHistory.length > 30) {
            powerHistory.shift();
        }

        drawPowerChart();
    } catch (error) {
        document.getElementById("status").textContent =
            "Нет соединения с сервером";
    }
}


async function turnLight(action) {
    try {
        await fetch(`/api/light/${action}`, {
            method: "POST"
        });

        await updateData();
        addEvent(action);
    } catch (error) {
        alert("Не удалось выполнить команду");
    }
}


function drawPowerChart() {
    const canvas = document.getElementById("powerChart");

    if (!canvas) {
        return;
    }

    const context = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    const paddingLeft = 60;
    const paddingRight = 25;
    const paddingTop = 25;
    const paddingBottom = 45;

    const graphWidth = width - paddingLeft - paddingRight;
    const graphHeight = height - paddingTop - paddingBottom;

    const maximumPower = 1000;

    context.clearRect(0, 0, width, height);

    context.strokeStyle = "#cbd5e1";
    context.lineWidth = 1;
    context.fillStyle = "#64748b";
    context.font = "13px Arial";

    for (let level = 0; level <= 1000; level += 250) {
        const y =
            paddingTop +
            graphHeight -
            (level / maximumPower) * graphHeight;

        context.beginPath();
        context.moveTo(paddingLeft, y);
        context.lineTo(width - paddingRight, y);
        context.stroke();

        context.fillText(`${level} Вт`, 5, y + 4);
    }

    if (powerHistory.length < 2) {
        return;
    }

    context.beginPath();
    context.strokeStyle = "#2563eb";
    context.lineWidth = 3;
    context.lineJoin = "round";

    powerHistory.forEach((power, index) => {
        const x =
            paddingLeft +
            (index / 29) * graphWidth;

        const y =
            paddingTop +
            graphHeight -
            (power / maximumPower) * graphHeight;

        if (index === 0) {
            context.moveTo(x, y);
        } else {
            context.lineTo(x, y);
        }
    });

    context.stroke();

    context.fillStyle = "#475569";
    context.fillText(
        "Последние показания мощности",
        paddingLeft,
        height - 12
    );
}

function addEvent(action) {
    const eventLog = document.getElementById("eventLog");
    const time = new Date().toLocaleTimeString("ru-RU");

    const initialRow = eventLog.querySelector("tr");

    if (
        initialRow &&
        initialRow.textContent.includes("Система запущена")
    ) {
        initialRow.remove();
    }

    const row = document.createElement("tr");

    if (action === "on") {
        row.innerHTML = `
            <td>${time}</td>
            <td>Команда включения</td>
            <td class="event-on">Включено</td>
        `;
    } else {
        row.innerHTML = `
            <td>${time}</td>
            <td>Команда выключения</td>
            <td class="event-off">Выключено</td>
        `;
    }

    eventLog.prepend(row);

    while (eventLog.rows.length > 10) {
        eventLog.deleteRow(10);
    }
}
updateData();

setInterval(updateData, 2000);