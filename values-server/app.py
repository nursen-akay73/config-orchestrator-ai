from flask import Flask, jsonify
import os
import json

app = Flask(__name__)

VALUES_DIR = os.getenv("VALUES_DIR", "/app/data/values")  # 👈 BURASI DEĞİŞTİ

@app.route('/<app_name>', methods=['GET'])
def get_values(app_name):
    values_file = os.path.join(VALUES_DIR, f"{app_name}.value.json")
    if os.path.exists(values_file):
        with open(values_file, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    return jsonify({"error": "Values not found"}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)