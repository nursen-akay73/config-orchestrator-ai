from flask import Flask, jsonify
import os
import json

app = Flask(__name__)

SCHEMA_DIR = os.getenv("SCHEMA_DIR", "/app/data/schemas")  # 👈 BURASI DEĞİŞTİ

@app.route('/<app_name>', methods=['GET'])
def get_schema(app_name):
    schema_file = os.path.join(SCHEMA_DIR, f"{app_name}.schema.json")
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    return jsonify({"error": "Schema not found"}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)