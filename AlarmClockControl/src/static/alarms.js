var numAlarmsDisplay = 10;

window.onload = function() {
    document.getElementById('append_alarm').addEventListener('click', appendRow);
    document.getElementById('save_alarms').addEventListener('click', saveAlarms);
    document.getElementById('more_alarms').addEventListener('click', moreAlarms);
    loadData({});
}

function saveAlarms(event) {
    var ulAlarms = document.getElementById("alarms");
    var alarms = [];
    
    var inputs = ulAlarms.getElementsByClassName('alarmInput');
    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        alarms.push(input.value);
    }
    loadData({'new_alarms': alarms});
}

function loadData(data) {
    var url = '/data';
    data['num_alarms_display'] = numAlarmsDisplay;

    console.log('Sending data:', data);
    fetch(url, {
      method: 'POST',
      body: JSON.stringify(data),
      headers: new Headers({
        'Content-Type': 'application/json'
      })
    }).then(res => res.json())
    .catch(error => console.error('Error loading data:', error))
    .then(data => updateData(data));
}

function updateData(data) {
    console.log('Loaded data:', data);

    var ulAlarms = document.getElementById("alarms");

    // Remove any existing rows.
    while (ulAlarms.firstChild) {
        ulAlarms.removeChild(ulAlarms.firstChild);
    }

    var alarms = data['alarms'];
    for (var i = 0; i < alarms.length; i++) {
        var li = document.createElement("li");
    
        var input = document.createElement("input");
        input.classList.add("alarmInput");
        input.type = "text";
        input.value = alarms[i];
        li.appendChild(input);
    
        var button = document.createElement("input");
        button.type = "button";
        button.value = "Delete";
        button.addEventListener('click', deleteRow);
        li.appendChild(button);
    
        ulAlarms.appendChild(li);
    }
    
    var currentTime = document.getElementById("current_time");
    currentTime.innerHTML = data['now']
    
    var numAlarmsDisplay = document.getElementById("num_alarms_display");
    numAlarmsDisplay.innerHTML = data['num_alarms_display']

    var ulNextAlarms = document.getElementById("next_alarms");
    while (ulNextAlarms.firstChild) {
        ulNextAlarms.removeChild(ulNextAlarms.firstChild);
    }
    var nextAlarms = data['next_alarms'];
    for (var i = 0; i < nextAlarms.length; i++) {
        var li = document.createElement("li");
        li.innerHTML = nextAlarms[i];
        ulNextAlarms.appendChild(li);
    }
}

function appendRow(event) {
    var ul = document.getElementById("alarms");

    var li = document.createElement("li");

    var input = document.createElement("input");
    input.classList.add("alarmInput");
    input.type = "text";
    input.value = "* * * * *";
    li.appendChild(input);

    var button = document.createElement("input");
    button.type = "button";
    button.value = "Delete";
    button.addEventListener('click', deleteRow);
    li.appendChild(button);

    ul.appendChild(li);
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
