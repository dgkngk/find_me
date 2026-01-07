# Bus Location Tracker (Find Me) 🚌

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Tkinter](https://img.shields.io/badge/Tkinter-GUI-gray?style=for-the-badge)
![Leaflet](https://img.shields.io/badge/Leaflet-Maps-green?style=for-the-badge&logo=leaflet)

**Find Me** is a specialized desktop utility that bridges the gap between desktop GUIs and web technologies. It allows operations staff to track specific bus fleets in real-time by embedding a dynamic **Leaflet.js** map within a native **Python Tkinter** window.

This project solves the problem of accessing a web-only map interface within a legacy desktop workflow by spinning up a lightweight, local Flask server to render the map tile logic and bridging it to the desktop frame.

## 💡 How It Works

1.  **Hybrid Architecture**: The app runs a background daemon thread hosting a **Flask** server.
2.  **Map Rendering**: A `webview` component within the Tkinter GUI points to `localhost`, rendering the interactive map.
3.  **Data Ingestion**: The backend polls the fleet management API (Pamukkale Turizm) to fetch GPS coordinates, speed, and route data.
4.  **State Persistence**: Uses a cookie-based mechanism to remember the last tracked vehicle across sessions.

## 🚀 Features

*   **Real-Time Tracking**: Auto-refreshing GPS coordinates (30s interval).
*   **Fleet Search**: Dropdown selection and license plate validation.
*   **Map Controls**: Day/Night mode toggles and interactive zoom.
*   **No-Disk-Write**: Map data serves from in-memory byte buffers for performance.

## 🛠️ Usage

1.  **Install Requirements**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Launch the Dashboard**:
    ```bash
    python find_me.py
    ```

*Note: This application requires access to the specific fleet management API endpoints defined in the configuration.*