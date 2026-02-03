from flask import Flask, jsonify, send_file
import os

app = Flask(__name__)

# Şema dosyalarının olduğu klasör
SCHEMA_DIR = os.getenv("SCHEMA_DIR", "/data/schemas")

@app.route('/<app_name>', methods=['GET'])
def get_schema(app_name):
    """
    Uygulama adına göre JSON şemasını döndürür
    Örnek: GET /chat → chat.schema.json
    """
    schema_file = os.path.join(SCHEMA_DIR, f"{app_name}.schema.json")
    
    if os.path.exists(schema_file):
        return send_file(schema_file, mimetype='application/json')
    else:
        return jsonify({"error": "Schema not found"}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    port = int(os.getenv("LISTEN_PORT", "5001"))
    app.run(host=host, port=port)