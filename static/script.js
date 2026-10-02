const powerHistory = [];


async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        const history = await response.json();

        powerHistory.length = 0;

        history.forEach((measurement) => {
            powerHistory.push(measurement.power);
        });

        drawPowerChart();
    } catch (error) {
        console.error("Не удалось загрузить историю", error);
    }

    await updateData();
}


async function updateData() {
    try {
        const response = await fetch("/api/data");
        const data = await response.json();

        document.getElementById("voltage").textContent =
            data.voltage;

        document.getElementById("current").textContent =
            data.current;

        document.getElementById("power").textContent =
            data.power;

        document.getElementById("savings").textContent =
            data.savings;

        const status = document.getElementById("status");
        const mode = document.getElementById("controlMode");

        if (data.lighting_on) {
            status.textContent = "Освещение включено";
            status.className = "value status status-on";
        } else {
            status.textContent = "Освещение выключено";
            status.className = "value status status-off";
        }

        if (data.control_mode === "adaptive") {
            mode.textContent = "Адаптивный IoT";
            mode.className = "mode-adaptive";
        } else {
            mode.textContent = "Таймер / фотореле";
            mode.className = "mode-conventional";
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

        addEvent(action);
        await updateData();
    } catch (error) {
        alert("Не удалось выполнить команду");
    }
}


async function changeMode(mode) {
    try {
        const response = await fetch(`/api/mode/${mode}`, {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error("Ошибка изменения режима");
        }

        if (mode === "adaptive") {
            addModeEvent(
                "Адаптивный IoT-режим",
                "Включён"
            );
        } else {
            addModeEvent(
                "Таймер / фотореле",
                "Включён"
            );
        }

        await updateData();
    } catch (error) {
        alert("Не удалось изменить режим");
    }
}


function addEvent(action) {
    const eventLog = document.getElementById("eventLog");
    const time = new Date().toLocaleTimeString("ru-RU");

    removeInitialRow(eventLog);

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
    limitEventRows(eventLog);
}


function addModeEvent(eventName, state) {
    const eventLog = document.getElementById("eventLog");
    const time = new Date().toLocaleTimeString("ru-RU");

    removeInitialRow(eventLog);

    const row = document.createElement("tr");

    row.innerHTML = `
        <td>${time}</td>
        <td>${eventName}</td>
        <td class="event-on">${state}</td>
    `;

    eventLog.prepend(row);
    limitEventRows(eventLog);
}


function removeInitialRow(eventLog) {
    const initialRow = eventLog.querySelector("tr");

    if (
        initialRow &&
        initialRow.textContent.includes("Система запущена")
    ) {
        initialRow.remove();
    }
}


function limitEventRows(eventLog) {
    while (eventLog.rows.length > 10) {
        eventLog.deleteRow(10);
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

    const graphWidth =
        width - paddingLeft - paddingRight;

    const graphHeight =
        height - paddingTop - paddingBottom;

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


loadHistory();

setInterval(updateData, 2000);