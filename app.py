import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Speichert die Daten im Format: {"Gerätename": {"lat": 50.1, "lon": 8.6}}
geraete_daten = {}

@app.route('/', methods=['GET'])
def index():
    global geraete_daten
    
    # Wir wandeln die Python-Daten in JSON für das JavaScript auf der Webseite um
    json_daten = json.dumps(geraete_daten)

    return f"""
    <html>
        <head>
            <title>Live GPS Tracker</title>
            <meta http-equiv="refresh" content="5"> 
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                #map {{ height: 500px; width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .btn {{ display: inline-block; background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-bottom: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Steuerung & Download</h2>
                <a href="/download" class="btn">📥 APK Herunterladen</a>
            </div>

            <div class="container">
                <h1>Live-Standorte aller Geräte</h1>
                <div id="map"></div>
            </div>

            <script>
                // Die Daten aus Python in JavaScript laden
                const geraete = {json_daten};
                
                // Standard-Mittelpunkt der Karte (Deutschland), falls noch keine Daten da sind
                let centerLat = 51.1657;
                let centerLon = 10.4515;
                let zoomLevel = 5;

                // REPARIERT: Richtiger JavaScript-Kommentar verwendet
                const keys = Object.keys(geraete);
                if (keys.length > 0) {{
                    centerLat = geraete[keys[0]].lat;
                    centerLon = geraete[keys[0]].lon;
                    zoomLevel = 13;
                }}

                // Karte initialisieren
                const map = L.map('map').setView([centerLat, centerLon], zoomLevel);

                // OpenStreetMap Karten-Kacheln laden
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap-Mitwirkende'
                }}).addTo(map);

                // Für jedes Gerät einen Marker (Stecknadel) auf der Karte setzen
                for (const name in geraete) {{
                    const info = geraete[name];
                    L.marker([info.lat, info.lon])
                     .addTo(map)
                     .bindPopup("<b>" + name + "</b><br>Breitengrad: " + info.lat + "<br>Längengrad: " + info.lon)
                     .openPopup();
                }}
            </script>
        </body>
    </html>
    """

@app.route('/download', methods=['GET'])
def download_apk():
    return send_from_directory(directory='static', path='app-debug.apk', as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload():
    global geraete_daten
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
        
    data = request.get_json()
    geraete_name = data.get("name", "Unbekanntes Gerät")
    lat = data.get("lat")
    lon = data.get("lon")
    
    if lat is not None and lon is not None:
        geraete_daten[geraete_name] = {"lat": lat, "lon": lon}
        print(f"Position erhalten von {geraete_name}: {lat}, {lon}", flush=True)
        return jsonify({"status": "success"}), 200
    
    return jsonify({"error": "Ungültige Koordinaten"}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
