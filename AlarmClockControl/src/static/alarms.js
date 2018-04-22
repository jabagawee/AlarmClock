const crontabClassName = "crontabInput";
const buzzerClassName = "buzzerInput";

const defaultCrontab = "* * * * *";
const defaultBuzzer = false;

var numAlarmsDisplay = 10;

window.onload = function() {
    document.getElementById("append_alarm").addEventListener("click", appendRow);
    document.getElementById("save_alarms").addEventListener("click", saveAlarms);
    document.getElementById("more_alarms").addEventListener("click", moreAlarms);
    loadData({});
}

function saveAlarms(event) {
    var ulAlarms = document.getElementById("alarms");
    var alarms = [];
    
    var crontabs = ulAlarms.getElementsByClassName(crontabClassName);
    for (var i = 0; i < crontabs.length; i++) {
        var crontab = crontabs[i];
        var buzzer = crontab.parentNode.getElementsByClassName(buzzerClassName)[0];
        alarms.push({"crontab": crontab.value, "buzzer": buzzer.checked});
    }
    loadData({"new_alarms": alarms});
}

function loadData(data) {
    var url = "/data";
    data["num_alarms_display"] = numAlarmsDisplay;

    console.log("Sending data:", data);
    fetch(url, {
      method: "POST",
      body: JSON.stringify(data),
      headers: new Headers({
        "Content-Type": "application/json"
      })
    }).then(res => res.json())
    .catch(error => console.error("Error loading data:", error))
    .then(data => updateData(data));
}

function updateData(data) {
    console.log("Loaded data:", data);

    var ulAlarms = document.getElementById("alarms");

    // Remove any existing rows.
    while (ulAlarms.firstChild) {
        ulAlarms.removeChild(ulAlarms.firstChild);
    }

    var alarms = data["alarms"];
    for (var i = 0; i < alarms.length; i++) {
        var alarm = alarms[i]
        ulAlarms.appendChild(createRow(alarm["crontab"], alarm["buzzer"]));
    }
    
    var currentTime = document.getElementById("current_time");
    currentTime.innerHTML = data["now"]
    
    var numAlarmsDisplay = document.getElementById("num_alarms_display");
    numAlarmsDisplay.innerHTML = data["num_alarms_display"]

    var ulNextAlarms = document.getElementById("next_alarms");
    while (ulNextAlarms.firstChild) {
        ulNextAlarms.removeChild(ulNextAlarms.firstChild);
    }
    var nextAlarms = data["next_alarms"];
    for (var i = 0; i < nextAlarms.length; i++) {
        var li = document.createElement("li");
        li.innerHTML = nextAlarms[i];
        ulNextAlarms.appendChild(li);
    }
}

function appendRow(event) {
    var ul = document.getElementById("alarms");
    ul.appendChild(createRow(defaultCrontab, defaultBuzzer));
}

function createRow(crontab, buzzer) {
    var li = document.createElement("li");
    
    var text = document.createElement("input");
    text.classList.add(crontabClassName);
    text.type = "text";
    text.value = crontab;
    li.appendChild(text);
    
    var checkbox = document.createElement("input");
    checkbox.classList.add(buzzerClassName);
    checkbox.type = "checkbox";
    li.appendChild(checkbox);
    checkbox.checked = buzzer;

    var button = document.createElement("input");
    button.type = "button";
    button.value = "Delete";
    button.addEventListener("click", deleteRow);
    li.appendChild(button);
    
    return li;
}

function deleteRow(event) {
    var li = event.currentTarget;
    while (li.parentNode) {
        li = li.parentNode;
        if (li.tagName === "LI")
            break;
    }
    li.parentNode.removeChild(li);
}

function moreAlarms(event) {
    numAlarmsDisplay += 10;
    loadData({});
    event.currentTarget.scrollIntoView();
}
