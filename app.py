import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Ein zufälliger Schlüssel, den Flask braucht, um Passwörter im Browser sicher zu merken
app.secret_key = os.environ.get("SECRET_KEY", "ein_zufaelliger_geheimer_schluessel_123")

# LEGE HIER DEIN PASSWORT FEST:
GEHEIMES_PASSWORT = "192837465"

# Speichert die Live-Daten der Geräte inklusive Zeitstempel
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
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <h1>🗺️ Live-Standorte aller Geräte</h1>
                <a href="/logout" style="color: #dc3545; text-decoration: none; font-weight: bold;">Abmelden 🚪</a>
            </div>
            
            <div style="display: flex; gap: 20px; margin-bottom: 15px; background: #e9ecef; padding: 10px; border-radius: 6px; font-size: 14px; font-weight: bold; color: #495057;">
                <div id="zeit-seit-update">⏱️ Letzter Webseiten-Abruf: Gerade eben</div>
                <div id="zeit-bis-update">🔄 Nächstes Webseiten-Update in: 05:00</div>
            </div>

            <div style="background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px; margin-bottom: 15px;">
                <h3 style="margin-top: 0; margin-bottom: 10px; font-size: 16px; color: #495057;">📱 Aktive Geräte & Status:</h3>
                <div id="geraete-liste-container"><i>Keine Geräte aktiv</i></div>
            </div>
            
            <div id="map"></div>
        </div>
        """
        javascript_html = f"""
        <script>
            let geraete = {json_daten};
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

            let markerMap = {{}};

            // Aktualisiert die Marker und die Geräteliste mit Lösch-Knöpfen
            function updateUI(daten) {{
                geraete = daten; // Global updaten
                
                // 1. MARKER AKTUALISIEREN
                for (const name in daten) {{
                    const info = daten[name];
                    
                    if (markerMap[name]) {{
                        markerMap[name].setLatLng([info.lat, info.lon]);
                        markerMap[name].getPopup().setContent("<b>" + name + "</b><br>Lat: " + info.lat + "<br>Lon: " + info.lon);
                    }} else {{
                        const marker = L.marker([info.lat, info.lon])
                                         .addTo(map)
                                         .bindPopup("<b>" + name + "</b><br>Lat: " + info.lat + "<br>Lon: " + info.lon);
                        markerMap[name] = marker;
                    }}
                }}
                
                for (const name in markerMap) {{
                    if (!daten[name]) {{
                        map.removeLayer(markerMap[name]);
                        delete markerMap[name];
                    }}
                }}

                // 2. GERÄTELISTE MIT LÖSCH-KNÖPFEN UND HANDY-STATUS NEU ZEICHNEN
                const container = document.getElementById('geraete-liste-container');
                const gerateKeys = Object.keys(daten);
                
                if (gerateKeys.length === 0) {{
                    container.innerHTML = "<i>Keine Geräte aktiv</i>";
                    return;
                }}
                
                let html = '<ul style="list-style: none; padding: 0; margin: 0;">';
                const jetzt = Math.floor(Date.now() / 1000);
                
                for (const name in daten) {{
                    const info = daten[name];
                    const diffSekunden = jetzt - info.zeitstempel;
                    
                    let handyZeitText = "";
                    if (diffSekunden < 60) {{
                        handyZeitText = "vor " + diffSekunden + " Sek.";
                    }} else {{
                        let min = Math.floor(diffSekunden / 60);
                        let sek = diffSekunden % 60;
                        handyZeitText = "vor " + min + " Min. " + sek + " Sek.";
                    }}
                    
                    html += `
                    <li style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px;">
                        <div>
                            <b style="color: #007bff;">🟢 ${{name}}</b> 
                            <span style="color: #6c757d; margin-left: 15px;">📡 Letzter Handy-Funkspruch: <b>${{handyZeitText}}</b></span>
                        </div>
                        <a href="/delete/${{encodeURIComponent(name)}}" 
                           style="background-color: #dc3545; color: white; text-decoration: none; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;"
                           onclick="return confirm('Möchtest du das Gerät ${{name}} wirklich löschen?');">
                           Gerät löschen 🗑️
                        </a>
                    </li>`;
                }}
                html += '</ul>';
                container.innerHTML = html;
            }}

            // Initiales Zeichnen beim Laden der Seite
            updateUI(geraete);

            // --- LIVE-TIMING FÜR DIE TEXTE ---
            let sekundenSeitUpdate = 0;
            let sekundenBisUpdate = 300; 

            setInterval(function() {{
                sekundenSeitUpdate++;
                sekundenBisUpdate--;

                // Webseiten-Update-Text
                let seitText = "";
                if (sekundenSeitUpdate < 60) {{
                    seitText = sekundenSeitUpdate + " Sek.";
                }} else {{
                    let min = Math.floor(sekundenSeitUpdate / 60);
                    let sek = sekundenSeitUpdate % 60;
                    seitText = min + " Min. " + (sek < 10 ? "0" : "") + sek + " Sek.";
                }}
                document.getElementById('zeit-seit-update').innerHTML = "⏱️ Letzter Webseiten-Abruf: vor " + seitText;

                // Countdown-Text
                let bisMin = Math.floor(sekundenBisUpdate / 60);
                let bisSek = sekundenBisUpdate % 60;
                document.getElementById('zeit-bis-update').innerHTML = "🔄 Nächstes Webseiten-Update in: " + (bisMin < 10 ? "0" : "") + bisMin + ":" + (bisSek < 10 ? "0" : "") + bisSek;

                // Jede Sekunde auch die Handy-Zeitstempel-Texte neu berechnen (damit sie flüssig hochzählen)
                updateUI(geraete);

                if (sekundenBisUpdate <= 0) {{
                    datenVomServerHolen();
                }}
            }, 1000);

            function datenVomServerHolen() {{
                fetch('/api/data')
                    .then(response => {{
                        if (response.status === 401) {{
                            window.location.reload();
                        }}
                        return response.json();
                    }})
                    .then(neueDaten => {{
                        console.log("Hintergrund-Update durchgeführt:", neueDaten);
                        updateUI(neueDaten);
                        sekundenSeitUpdate = 0;
                        sekundenBisUpdate = 300; 
                        document.getElementById('zeit-seit-update').innerHTML = "⏱️ Letzter Webseiten-Abruf: Gerade eben";
                    }})
                    .catch(err => {{
                        console.error("Fehler beim Live-Update:", err);
                        sekundenBisUpdate = 5; 
                    }});
            }}
        </script>
        """

    return f"""
    <html>
        <head>
            <title>App Management Dashboard</title>
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

# EXTRA ROUTE FÜR DAS JAVASCRIPT-UPDATE
@app.route('/api/data', methods=['GET'])
def get_live_data():
    if not session.get('eingeloggt', False):
        return jsonify({}), 401
    return jsonify(geraete_daten)

# 2. ROUTE FÜR DIE PASSWORT-VERARBEITUNG
@app.route('/login', methods=['POST'])
def login():
    eingegebenes_passwort = request.form.get('passwort')
    if eingegebenes_passwort == GEHEIMES_PASSWORT:
        session['eingeloggt'] = True
    return redirect(url_for('index'))

# 3. ROUTE ZUM ABMELDEN
@app.route('/logout')
def logout():
    session.pop('eingeloggt', None)
    return redirect(url_for('index'))

# 4. ROUTE FÜR DEN APK-DOWNLOAD
@app.route('/download', methods=['GET'])
def download_apk():
    return send_from_directory(directory='static', path='app.apk', as_attachment=True)

# 5. ROUTE FÜR DIE ANDROID-APP (Empfängt Daten & speichert aktuellen Zeitstempel)
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
        # time.time() speichert die exakte aktuelle Uhrzeit als Sekunden-Zahl
        geraete_daten[geraete_name] = {"lat": lat, "lon": lon, "zeitstempel": int(time.time())}
        return jsonify({"status": "success"}), 200
    
    return jsonify({"error": "Ungültige Koordinaten"}), 400

# ROUTE ZUM LÖSCHEN EINES GERÄTS (Direkt über den Knopf aufrufbar)
@app.route('/delete/<name>', methods=['GET', 'POST'])
def delete_device(name):
    global geraete_daten
    if not session.get('eingeloggt', False):
        return redirect(url_for('index'))
        
    if name in geraete_daten:
        del geraete_daten[name]
        print(f"Gerät {name} wurde gelöscht.", flush=True)
        
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
