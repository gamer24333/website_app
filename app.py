import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Eine globale Variable, die den jeweils neuesten Text im Arbeitsspeicher behält
letztes_update = "Noch keine Daten empfangen"

# 1. ROUTE FÜR DEN BROWSER (Wenn du die normale Website aufrufst)
@app.route('/', methods=['GET'])
def index():
    global letztes_update
    # Gibt den aktuellen Text als einfache HTML-Seite im Browser aus
    return f"""
    <html>
        <head>
            <title>Server Status</title>
            <meta http-equiv="refresh" content="5"> <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; }}
                .data {{ font-size: 1.2em; color: #0066cc; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Letztes empfangenes Update von der App:</h1>
                <p class="data">{letztes_update}</p>
                <p><small>Diese Seite aktualisiert sich automatisch alle 5 Sekunden.</small></p>
            </div>
        </body>
    </html>
    """

# 2. ROUTE FÜR DIE ANDROID-APP (Nimmt die POST-Daten entgegen)
@app.route('/upload', methods=['POST'])
def upload():
    global letztes_update
    
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
        
    data = request.get_json()
    received_text = data.get("text", "")
    
    # Aktualisiert die globale Variable mit den neuen Daten aus der App
    letztes_update = received_text
    
    # Weiterhin Ausgabe in den Render-Logs zur Kontrolle
    print(f"Empfangener Text aktualisiert: {received_text}", flush=True)
    
    return jsonify({"status": "success", "message": "Daten aktualisiert"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
