import os
import json
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Ein zufälliger Schlüssel, den Flask braucht, um Passwörter im Browser sicher zu merken
app.secret_key = os.environ.get("SECRET_KEY", "ein_zufaelliger_geheimer_schluessel_123")

# LEGE HIER DEIN PASSWORT FEST:
GEHEIMES_PASSWORT = "MeinSicheresPasswort123"

# Speichert die Live-Daten der Geräte
geraete_daten = {}

# 1. HAUPTSEITE (Download für alle, Karte nur mit Passwort)
@app.route('/', methods=['GET'])
def index():
    global geraete_daten
    
    # Prüfen, ob der Nutzer bereits eingeloggt ist
    ist_eingeloggt = session.get('eingeloggt', False)
    
    # HTML-Teil für das Login-Formular (falls nicht eingeloggt)
    login_html = ""
    if not ist_eingeloggt:
        login_html = """
        <div class="container animate-fade">
            <h2>🔒 Interner Bereich (Nur für ausgewählte Personen)</h2>
            <p>Bitte gib das Passwort ein, um die Live-Karte zu sehen:</p>
            <form action="/login" method="POST" style="display: flex; gap: 10px; max-width: 400px;">
                <input type="password" name="passwort" placeholder="Passwort eingeben..." required 
                       style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                <button type="submit" style="background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">Anmelden</button>
            </form>
        </div>
        """
    
    # HTML-Teil für die Karte (wird nur geladen, wenn eingeloggt)
    karte_html = ""
    javascript_html = ""
    if ist_eingeloggt:
        json_daten = json.dumps(geraete_daten)
        karte_html = """
        <div class="container animate-fade">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h1>🗺️ Live-Standorte aller Geräte</h1>
                <a href="/logout" style="color: #dc3545; text-decoration: none; font-weight: bold;">Abmelden 🚪</a>
            </div>
            <div id="map"></div>
        </div>
        """
        javascript_html = f"""
        <script>
            const geraete = {json_daten};
            let centerLat = 51.1657;
            let centerLon = 10.4515;
            let zoomLevel = 5;

            const keys = Object.keys(geraete);
            if (keys.length > 0) {{
                centerLat = geraete[keys[0]].lat;
                centerLon = geraete[keys[0]].lon;
                zoomLevel = 13;
            }}

            const map = L.map('map').setView([centerLat, centerLon], zoomLevel);

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap'
            }}).addTo(map);

            for (const name in geraete) {{
                const info = geraete[name];
                L.marker([info.lat, info.lon])
                 .addTo(map)
                 .bindPopup("<b>" + name + "</b><br>Lat: " + info.lat + "<br>Lon: " + info.lon)
                 .openPopup();
            }}
        </script>
        """

    # Das gesamte Layout der Webseite (wird an jeden geschickt)
    return f"""
    <html>
        <head>
            <title>App Management Dashboard</title>
            {"<meta http-equiv='refresh' content='5'>" if ist_eingeloggt else ""}
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                #map {{ height: 500px; width: 100%; border-radius: 8px; }}
                .btn {{ display: inline-block; background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .btn:hover {{ background-color: #218838; }}
                .animate-fade {{ animation: fadeIn 0.5s ease-in; }}
                @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📲 Öffentlicher App-Download</h2>
                <p>Hier kann jeder die aktuelle Version der App auf sein Android-Smartphone laden:</p>
                <a href="/download" class="btn">📥 APK Herunterladen</a>
            </div>

            {login_html}
            {karte_html}
            {javascript_html}
        </body>
    </html>
    """

# 2. ROUTE FÜR DIE PASSWORT-VERARBEITUNG
@app.route('/login', methods=['POST'])
def login():
    
    eingegebenes_passwort = request.form.get('passwort')
    if eingegebenes_passwort == "192837465":
        session['eingeloggt'] = True  # Setzt das "Erlaubnis-Flag" im Browser
    return redirect(url_for('index'))

# 3. ROUTE ZUM ABMELDEN
@app.route('/logout')
def logout():
    session.pop('eingeloggt', None)  # Löscht die Erlaubnis
    return redirect(url_for('index'))

# 4. ROUTE FÜR DEN APK-DOWNLOAD (Öffentlich)
@app.route('/download', methods=['GET'])
def download_apk():
    return send_from_directory(directory='static', path='app.apk', as_attachment=True)

# 5. ROUTE FÜR DIE ANDROID-APP (Empfängt die Live-Daten im Hintergrund)
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
        return jsonify({"status": "success"}), 200
    
    return jsonify({"error": "Ungültige Koordinaten"}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
