import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.secret_key = os.environ.get("SECRET_KEY", "ein_zufaelliger_geheimer_schluessel_123")
GEHEIMES_PASSWORT = "192837465"

# Speichert die Live-Daten der Geräte inklusive Historie
geraete_daten = {}

@app.route('/', methods=['GET'])
def index():
    global geraete_daten
    ist_eingeloggt = session.get('eingeloggt', False)
    
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
    
    karte_html = ""
    javascript_html = ""
    if ist_eingeloggt:
        json_daten = json.dumps(geraete_daten)
        karte_html = """
        <div class="container animate-fade">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <h1>🗺️ Live-Standorte & Routen aller Geräte</h1>
                <a href="/logout" style="color: #dc3545; text-decoration: none; font-weight: bold;">Abmelden 🚪</a>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; background: #e9ecef; padding: 10px; border-radius: 6px; font-size: 14px; font-weight: bold; color: #495057;">
                <div style="display: flex; gap: 20px;">
                    <div id="zeit-seit-update">⏱️ Letzter Webseiten-Abruf: Gerade eben</div>
                    <div id="zeit-bis-update">🔄 Nächstes Webseiten-Update in: 00:05</div>
                </div>
                <button onclick="datenVomServerHolen()" style="background-color: #007bff; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">Jetzt manuell aktualisieren ⚡</button>
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
            let linienMap = {{}};

            function updateUI(daten) {{
                geraete = daten;
                
                for (const name in daten) {{
                    const info = daten[name];
                    const popupText = "<b>" + name + "</b><br>🔋 Akku: " + info.akku + "%<br>🚀 Tempo: " + info.speed + " km/h<br>🌐 Netz: " + info.netzwerk;
                    
                    if (markerMap[name]) {{
                        markerMap[name].setLatLng([info.lat, info.lon]);
                        markerMap[name].getPopup().setContent(popupText);
                    }} else {{
                        const marker = L.marker([info.lat, info.lon])
                                         .addTo(map)
                                         .bindPopup(popupText);
                        markerMap[name] = marker;
                        map.setView([info.lat, info.lon], 14);
                    }}

                    if (info.historie && info.historie.length > 1) {{
                        if (linienMap[name]) {{
                            map.removeLayer(linienMap[name]);
                        }}
                        const linie = L.polyline(info.historie, {{color: '#007bff', weight: 4, opacity: 0.7}}).addTo(map);
                        linienMap[name] = linie;
                    }}
                }}
                
                for (const name in markerMap) {{
                    if (!daten[name]) {{
                        map.removeLayer(markerMap[name]);
                        delete markerMap[name];
                        if (linienMap[name]) {{
                            map.removeLayer(linienMap[name]);
                            delete linienMap[name];
                        }}
                    }}
                }}

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
                    
                    let akkuFarbe = "#28a745"; 
                    if (info.akku <= 20) akkuFarbe = "#dc3545";
                    else if (info.akku <= 50) akkuFarbe = "#ffc107";
                    
                    // Umgeschrieben auf klassische String-Verknüpfung, um geschwungene Klammern im HTML zu vermeiden
                    html += '<li style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px;">' +
                            '<div>' +
                            '<b style="color: #007bff;">🟢 ' + name + '</b> ' +
                            '<span style="margin-left: 15px; color: ' + akkuFarbe + '; font-weight: bold;">🔋 ' + info.akku + '% Akku</span>' +
                            '<span style="margin-left: 15px; color: #17a2b8; font-weight: bold;">🚀 ' + info.speed + ' km/h</span>' +
                            '<span style="margin-left: 15px; color: #6f42c1; font-weight: bold;">🌐 ' + info.netzwerk + '</span>' +
                            '<span style="color: #6c757d; margin-left: 15px;">📡 Letzter Funkspruch: <b>' + handyZeitText + '</b></span>' +
                            '</div>' +
                            '<a href="/delete/' + encodeURIComponent(name) + '" ' +
                            'style="background-color: #dc3545; color: white; text-decoration: none; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;" ' +
                            'onclick="return confirm(\'Möchtest du das Gerät ' + name + ' wirklich löschen?\');">' +
                            'Gerät löschen 🗑️' +
                            '</a>' +
                            '</li>';
                }
                html += '</ul>';
                container.innerHTML = html;
            }}

            updateUI(geraete);

            if (!localStorage.getItem('letzterAbrufZeitstempel')) {{
                localStorage.setItem('letzterAbrufZeitstempel', Math.floor(Date.now() / 1000));
            }}

            setInterval(function() {{
                const JETZT = Math.floor(Date.now() / 1000);
                let letzterAbruf = parseInt(localStorage.getItem('letzterAbrufZeitstempel'));
                
                let sekundenSeitUpdate = JETZT - letzterAbruf;
                let sekundenBisUpdate = 5 - sekundenSeitUpdate;

                if (sekundenBisUpdate <= 0) {{
                    datenVomServerHolen();
                    return;
                }}

                let seitText = sekundenSeitUpdate + " Sek.";
                document.getElementById('zeit-seit-update').innerHTML = "⏱️ Letzter Webseiten-Abruf: vor " + seitText;
                document.getElementById('zeit-bis-update').innerHTML = "🔄 Nächstes Webseiten-Update in: 00:0" + sekundenBisUpdate;

                updateUI(geraete);
            }}, 1000);

            function datenVomServerHolen() {{
                fetch('/api/data')
                    .then(response => {{
                        if (response.status === 401) {{
                            window.location.reload();
                        }}
                        return response.json();
                    }})
                    .then(neueDaten => {{
                        updateUI(neueDaten);
                        localStorage.setItem('letzterAbrufZeitstempel', Math.floor(Date.now() / 1000));
                        document.getElementById('zeit-seit-update').innerHTML = "⏱️ Letzter Webseiten-Abruf: Gerade eben";
                    }})
                    .catch(err => {{
                        console.error("Fehler beim Live-Update:", err);
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

@app.route('/api/data', methods=['GET'])
def get_live_data():
    if not session.get('eingeloggt', False):
        return jsonify({}), 401
    return jsonify(geraete_daten)

@app.route('/login', methods=['POST'])
def login():
    eingegebenes_passwort = request.form.get('passwort')
    if eingegebenes_passwort == GEHEIMES_PASSWORT:
        session['eingeloggt'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('eingeloggt', None)
    return redirect(url_for('index'))

@app.route('/download', methods=['GET'])
def download_apk():
    return send_from_directory(directory='static', path='app.apk', as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload():
    global geraete_daten
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
        
    data = request.get_json()
    geraete_name = data.get("name", "Unbekanntes Gerät")
    lat = data.get("lat")
    lon = data.get("lon")
    akku = data.get("akku", "??")
    netzwerk = data.get("netzwerk", "Unbekannt")
    speed = data.get("speed", 0)
    
    if lat is not None and lon is not None:
        if geraete_name not in geraete_daten:
            historie = []
        else:
            historie = geraete_daten[geraete_name].get("historie", [])

        historie.append([lat, lon])

        if len(historie) > 10:
            historie.pop(0)

        geraete_daten[geraete_name] = {
            "lat": lat, 
            "lon": lon, 
            "akku": akku,
            "netzwerk": netzwerk,
            "speed": speed,
            "historie": historie,
            "zeitstempel": int(time.time())
        }
        return jsonify({"status": "success"}), 200
    
    return jsonify({"error": "Ungültige Koordinaten"}), 400

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
