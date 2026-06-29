import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # HINZUFÜGEN

app = Flask(__name__)
CORS(app)  # HINZUFÜGEN - Erlaubt Zugriffe von außen

@app.route('/upload', methods=['POST'])
def upload():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
        
    data = request.get_json()
    received_text = data.get("text", "")
    print(f"Empfangener Text: {received_text}", flush=True)
    
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
