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
    } catch (error) {
        alert("Не удалось выполнить команду");
    }
}


updateData();

setInterval(updateData, 2000);