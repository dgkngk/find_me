# Bus Location Tracker

This is a **Flask**-based live bus location tracker that fetches real-time GPS data from a JSON API and displays it on an interactive Leaflet.js map embedded inside a Tkinter GUI. Users can manually enter a license plate number or select from a dropdown list of active buses retrieved from a separate endpoint. The map features day/night modes, and optional auto-refresh every 30 seconds.

The application provides a clean user interface where bus details like location, speed, date/time, and route are shown visually on the map. It also remembers the last selected bus using **cookies** and includes basic plate number **validation for user input**. All map data is served without writing to disk, using an in-memory bytes buffer and a Flask route.

This app only works for Pamukkale Turizm buses. Other bus API's may or may not be implemented in the future.

## 🚀 Getting Started

### 🔧 Dependencies
Install required packages:

```bash
pip install -r requirements.txt

### 📖 Running the Application

```bash
python find_me.py

