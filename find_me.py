import threading
import requests
import folium
from flask import Flask, Response
import webview

app = Flask(__name__)
plate = "06 ESA 493"
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

def extract_key_values(data):
    lat = data.get("Latitude", "")
    lng = data.get("Longtitude", "")
    loc = data.get("Location", "")
    spd = data.get("Speed", "")
    voy = data.get("SeferAdi", "")
    dt  = data.get("DeviceDate", "")
    dkm = data.get("DailyKm", "")
    return lat, lng, loc, spd, voy, dt, dkm

def generate_map_html():
    global latest_map_html, map_mode
    data = fetch_bus_data(plate)
    if not data:
        latest_map_html = "<h3>Error fetching bus data.</h3>"
        return

    lat, lng, loc, spd, voy, dt, dkm = extract_key_values(data)
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        latest_map_html = "<h3>Invalid coordinates.</h3>"
        return

    tile_style = "CartoDB positron" if map_mode == "light" else "CartoDB dark_matter"

    m = folium.Map(location=[lat, lng], zoom_start=13, tiles=tile_style)

    popup_text = f"""
    <b>Location:</b> {loc}<br>
    <b>Route:</b> {voy}<br>
    <b>Speed:</b> {spd} km/h<br>
    <b>Time:</b> {dt}<br>
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
            #mapFrame {
                width: 100%;
                height: calc(100% - 50px);
                border: none;
            }
        </style>
    </head>
    <body>
        <div id="header">
            <button onclick="refreshMap()">🔄 Refresh</button>
            <button onclick="toggleMode()">🌓 Toggle Light/Dark Mode</button>
        </div>
        <iframe id="mapFrame" src="/map"></iframe>
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
        </script>
    </body>
    </html>
    """



@app.route('/map')
def map_view():
    return Response(latest_map_html, mimetype='text/html')

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


def start_flask():
    generate_map_html()  # Initial map
    app.run(host="127.0.0.1", port=5000, threaded=True)

def start_gui():
    webview.create_window("Bus Location Tracker", "http://127.0.0.1:5000", width=900, height=700)
    webview.start()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    start_gui()
