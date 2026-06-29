import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def home():
    return """
    <a href="/upload" style="color:white;">weiter</a>
    """

@app.route('/upload', methods=['POST'])
def upload():
    # Überprüfen, ob Daten im JSON-Format gesendet wurden
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
        
    data = request.get_json()
    received_text = data.get("text", "")
    
    # Ausgabe in den Server-Logs von Render
    print(f"Empfangener Text: {received_text}", flush=True)
    
    return jsonify({"status": "success", "message": "Daten erfolgreich empfangen"}), 200

if __name__ == '__main__':
    # Render weist dynamisch einen Port über Umgebungsvariablen zu
    port = int(os.environ.get("PORT", 5000))
    # Der Server muss auf 0.0.0.0 laufen, um extern erreichbar zu sein
    app.run(host='0.0.0.0', port=port)
