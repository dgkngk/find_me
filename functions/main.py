import re
import os
import requests
import folium
import pytz

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from xyzservices import TileProvider
from firebase_functions import https_fn


app = Flask(__name__)
CORS(app)
plate = ""
latest_map_html = ""  # In-memory map HTML
map_mode = "light"  # default mode


def fetch_bus_data(plate_number: str):
    url = "https://d3rh8btizouuof.cloudfront.net/yolcumneredeajax.php"
    params = {
        "islem": "yolcum-nerede-sefer-kor",
        "plaka": plate_number
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.pamukkale.com.tr/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
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

def generate_map_html(current_plate, current_mode):
    if not current_plate or current_plate.strip() == "":
        return "<h3>Please enter a plate number.</h3>"
    
    if not is_valid_plate(current_plate):
        return "<h3>Invalid plate number. Please enter a valid plate number.</h3>"
    
    data = fetch_bus_data(current_plate)
    if not data:
        return "<h3>Error fetching bus data.</h3>"

    lat, lng, loc, spd, voy, dt, dkm, lpt = extract_key_values(data)
    
    bus_time = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=3)
    current_time = datetime.now(tz=pytz.timezone("Europe/Istanbul"))
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return "<h3>Invalid coordinates.</h3>"

    m = folium.Map(location=[lat, lng], zoom_start=13, width="100%", height="90%")

    if current_mode == "light":
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

    return m.get_root().render()


@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>Pamukkale Bus Location Tracker</title>
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
            function getCookie(name) {
                let value = "; " + document.cookie;
                let parts = value.split("; " + name + "=");
                if (parts.length == 2) return parts.pop().split(";").shift();
            }

            function refreshMap() {
                document.getElementById('mapFrame').src = '/map?ts=' + new Date().getTime();
            }
            function toggleMode() {
                let mode = getCookie("map_mode") || "light";
                let newMode = mode === "light" ? "dark" : "light";
                document.cookie = "map_mode=" + newMode + "; path=/";
                refreshMap();
            }
            function setPlate() {
                const plate = document.getElementById("plateInput").value;
                document.cookie = "bus_plate=" + encodeURIComponent(plate) + "; path=/";
                refreshMap();
            }
            let autoRefreshTimer = null;

            function toggleAutoRefresh() {
                const isChecked = document.getElementById("autoRefresh").checked;

                if (isChecked) {
                    autoRefreshTimer = setInterval(() => {
                        loadBusList();
                        refreshMap();
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
                }).finally(() => {
                // Stop spin
                refreshBtn.classList.remove("spin");
                });
            }

            // Call on initial page load
            window.onload = function () {
            loadBusList();
            const savedPlate = getCookie("bus_plate");
            if (savedPlate) {
                document.getElementById("plateInput").value = decodeURIComponent(savedPlate);
            }
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
    saved_plate = request.cookies.get("bus_plate")
    current_mode = request.cookies.get("map_mode", "light")
    
    html = generate_map_html(saved_plate, current_mode)
    return Response(html, mimetype='text/html')

def fetch_buses(from_point, to_point, label_suffix):
    url = f"https://d3rh8btizouuof.cloudfront.net/ajax.php?islem=yolcum-nerede-sefer&Kalkis={from_point}&Varis={to_point}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.pamukkale.com.tr/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    html = resp.text

    pattern = r"<option value='(.*?)'>(.*?)</option>"
    matches = re.findall(pattern, html)

    # Append route info to label
    return [
        {"value": plate_val, "label": f"{label} ({label_suffix})"}
        for plate_val, label in matches
    ]

@app.route('/bus-list')
def bus_list():
    try:
        milas_to_izmir = fetch_buses(4829, 3500, "Milas → İzmir")
        izmir_to_milas = fetch_buses(3500, 4829, "İzmir → Milas")

        return jsonify(milas_to_izmir + izmir_to_milas)
    except Exception as e:
        print(f"Error in bus_list: {e}")
        return jsonify({"error": str(e)}), 500

@https_fn.on_request(region="europe-west1")
def find_me(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return app.full_dispatch_request()