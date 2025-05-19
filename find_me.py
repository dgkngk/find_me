import re
import os
import threading
import requests
import folium
import webview
import pytz

from flask import Flask, Response, jsonify, request
from datetime import datetime, timedelta
from xyzservices import TileProvider
from bs4 import BeautifulSoup

url = "https://www.pamukkale.com.tr/yolcum-nerede"
resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

select = soup.find("select", {"id": "kalkis-durak-list-nerede"})
options = select.find_all("option")


app = Flask(__name__)
plate = ""
latest_map_html = ""  # In-memory map HTML
map_mode = "light"  # default mode


def fetch_bus_data(plate_number: str):
    url = "https://d3rh8btizouuof.cloudfront.net/yolcumneredeajax.php"
    params = {
        "islem": "yolcum-nerede-sefer-kor",
        "plaka": plate_number
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching data:", e)
        return None
    
def is_valid_plate(plate_str):
    pattern = r"^\d{2}\s?[A-Z]{1,3}\s?\d{2,4}$"
    return re.match(pattern, plate_str.replace(" ", "").upper()) is not None

def extract_key_values(data):
    lat = data.get("Latitude", "")
    lng = data.get("Longtitude", "")
    loc = data.get("Location", "")
    spd = data.get("Speed", "")
    voy = data.get("SeferAdi", "")
    dt  = data.get("DeviceDate", "")
    dkm = data.get("DailyKm", "")
    lpt = data.get("DeviceLicensePlate", "")
    return lat, lng, loc, spd, voy, dt, dkm, lpt

def generate_map_html():
    global latest_map_html, map_mode, plate
    if not plate or plate.strip() == "":
        latest_map_html = "<h3>Please enter a plate number.</h3>"
        return
    
    if not is_valid_plate(plate):
        latest_map_html = "<h3>Invalid plate number. Please enter a valid plate number.</h3>"
        return
    
    data = fetch_bus_data(plate)
    if not data:
        latest_map_html = "<h3>Error fetching bus data.</h3>"
        return

    lat, lng, loc, spd, voy, dt, dkm, lpt = extract_key_values(data)
    
    bus_time = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=3)
    current_time = datetime.now(tz=pytz.timezone("Europe/Istanbul"))
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        latest_map_html = "<h3>Invalid coordinates.</h3>"
        return

    m = folium.Map(location=[lat, lng], zoom_start=13, width="100%", height="90%")

    if map_mode == "light":
        folium.TileLayer(
            TileProvider(
                url="https://tile.jawg.io/jawg-streets/{z}/{x}/{y}{r}.png?access-token=63BA10a3rgKUqfuP6MQcwnMFU82YntFQ22T8VFlVfkugiNB6q5OwnTFpC6bLMQJX",
                name="Jawg Streets",
                attribution="© JAWG, © dgkngk"
            )
        ).add_to(m)
    else:
        folium.TileLayer(
            TileProvider(
                url="https://tile.jawg.io/jawg-matrix/{z}/{x}/{y}{r}.png?access-token=63BA10a3rgKUqfuP6MQcwnMFU82YntFQ22T8VFlVfkugiNB6q5OwnTFpC6bLMQJX",
                name="Jawg Dark",
                attribution="© JAWG, © dgkngk"
            )
        ).add_to(m)


    popup_text = f"""
    <b>Plate Number:<b/> {lpt}<br>
    <b>Location:</b> {loc}<br>
    <b>Route:</b> {voy}<br>
    <b>Speed:</b> {spd} km/h<br>
    <b>Bus Time:</b> {bus_time.strftime("%Y-%m-%d %H:%M:%S")}<br>
    <b>Refresh Time</b> {current_time.strftime("%Y-%m-%d %H:%M:%S")}<br>
    <b>Daily Km:</b> {dkm}
    """

    folium.Marker(
        [lat, lng],
        popup=folium.Popup(popup_text, max_width=300),
        tooltip="Bus Location",
        icon=folium.Icon(color="red", icon="bus", prefix="fa")
    ).add_to(m)

    latest_map_html = m.get_root().render()


@app.route('/')
def index():
    global plate
    saved_plate = request.cookies.get("bus_plate")

    if saved_plate and is_valid_plate(saved_plate):
        plate = saved_plate.upper()
    else:
        saved_plate = plate  # use default if none
    
    return """
    <html>
    <head>
        <title>Bus Live Map</title>
        <style>
            html, body {
                margin: 0;
                padding: 0;
                height: 100%;
                width: 100%;
                font-family: sans-serif;
            }
            #header {
                background: #f0f0f0;
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }
            #header button {
                margin-right: 10px;
                padding: 6px 10px;
            }
            #header input {
                margin-right: 5px;
                padding: 6px 6px;
            }
            #mapFrame {
                width: 100%;
                height: calc(100% - 50px);
                border: none;
            }
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .spin {
                animation: spin 1s linear infinite; 
            }
        </style>
    </head>
    <body>
        <div id="header">
            <button onclick="refreshMap()">🔄 Refresh</button>
            <button onclick="toggleMode()">🌓 Toggle Light/Dark Mode</button>
            <br>
            <input type="text" id="plateInput" placeholder="Enter Plate (e.g., 34 IST 34)" />
            <button onclick="setPlate()">✅ Set Plate</button>
            <select id="busSelect" onchange="onBusSelect()">
                <option value="">🔽 Select Bus</option>
            </select>
            <button id="refreshBtn" onclick="loadBusList()" title="Refresh bus list" style="font-size: 10px; padding: 2px 4px; width: 25px; height: 25px;border-radius: 50%;">🔁</button>
            <br>
            <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()"> 🔁 Auto Refresh (30s)
        </div>
        <div><iframe id="mapFrame" src="/map"></iframe></div>
        <script>
            function refreshMap() {
                fetch('/refresh').then(() => {
                    document.getElementById('mapFrame').src = '/map?ts=' + new Date().getTime();
                });
            }
            function toggleMode() {
                fetch('/toggle-mode').then(() => {
                    document.getElementById('mapFrame').src = '/map?ts=' + new Date().getTime();
                });
            }
            function setPlate() {
                const plate = document.getElementById("plateInput").value;
                fetch('/set-plate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'plate=' + encodeURIComponent(plate)
                }).then((response) => {
                    if (response.ok) {
                        document.cookie = "bus_plate=" + encodeURIComponent(plate) + "; path=/";
                        document.getElementById('mapFrame').src = '/map?ts=' + new Date().getTime();
                    }
                    else {
                        alert("Invalid plate. Please try again.")
                    }
                })
                ;
            }
            let autoRefreshTimer = null;

            function toggleAutoRefresh() {
                const isChecked = document.getElementById("autoRefresh").checked;

                if (isChecked) {
                    autoRefreshTimer = setInterval(() => {
                        loadBusList();
                        document.getElementById('mapFrame').src = '/map?ts=' + new Date().getTime();
                    }, 30000); // 30 seconds
                } else {
                    clearInterval(autoRefreshTimer);
                    autoRefreshTimer = null;
                }
            }
            function loadBusList() {
            const dropdown = document.getElementById("busSelect");
              const refreshBtn = document.getElementById("refreshBtn");

            // Start spin
            refreshBtn.classList.add("spin");

            // Clear old options (except first)
            dropdown.options.length = 1;

            fetch("/bus-list")
                .then(res => res.json())
                .then(data => {
                data.forEach(bus => {
                    const option = document.createElement("option");
                    option.value = bus.value;
                    option.textContent = bus.label;
                    dropdown.appendChild(option);
                });
                })
                .catch(err => {
                console.error("Failed to load bus list:", err);
                alert("Could not refresh bus list.");
                }).finally(() => {
                // Stop spin
                refreshBtn.classList.remove("spin");
                });
            }

            // Call on initial page load
            window.onload = function () {
            loadBusList();
            };
            
            function onBusSelect() {
                const selected = document.getElementById("busSelect").value;
                if (selected) {
                    document.getElementById("plateInput").value = selected;
                    setPlate(); // Automatically fetch and show
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/map')
def map_view():
    generate_map_html()
    return Response(latest_map_html, mimetype='text/html')

def fetch_buses(from_point, to_point, label_suffix):
    url = f"https://www.pamukkale.com.tr/ajax.php?islem=yolcum-nerede-sefer&Kalkis={from_point}&Varis={to_point}"
    resp = requests.get(url)
    html = resp.text

    pattern = r"<option value='(.*?)'>(.*?)</option>"
    matches = re.findall(pattern, html)

    # Append route info to label
    return [
        {"value": plate, "label": f"{label} ({label_suffix})"}
        for plate, label in matches
    ]

@app.route('/bus-list')
def bus_list():
    try:
        milas_to_izmir = fetch_buses(4829, 3500, "Milas → İzmir")
        izmir_to_milas = fetch_buses(3500, 4829, "İzmir → Milas")

        return jsonify(milas_to_izmir + izmir_to_milas)
    except Exception as e:
        return jsonify([]), 500

@app.route('/refresh')
def refresh():
    threading.Thread(target=generate_map_html).start()
    return "OK"

@app.route('/toggle-mode')
def toggle_mode():
    global map_mode
    map_mode = "dark" if map_mode == "light" else "light"
    generate_map_html()
    return "OK"

@app.route('/set-plate', methods=['POST'])
def set_plate():
    global plate
    plate = request.form.get("plate", "").strip().upper()
    if plate.strip() == "":
        print("Plate cannot be empty")
        return
    
    print("Plate set to:", plate)
    generate_map_html()
    return "OK"

def start_flask():
    generate_map_html()  # Initial map
    app.run(host="127.0.0.1", port=5000, threaded=True)

def start_gui():
    webview.create_window("Pamukkale Bus Location Tracker", "http://127.0.0.1:5000", width=900, height=700)
    webview.start()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    if os.getenv("ON_SERVER") != True:
        start_gui()
