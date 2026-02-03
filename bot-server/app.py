from flask import Flask, request, jsonify
import requests
import json
import re
import os

app = Flask(__name__)

# Ollama API endpoint
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Diğer servislerin adresleri
SCHEMA_SERVICE_URL = os.getenv("SCHEMA_SERVICE_URL", "http://schema-service:5001")
VALUES_SERVICE_URL = os.getenv("VALUES_SERVICE_URL", "http://values-service:5002")
 
def call_ollama(prompt, model="llama3.2:3b"):
    """
    Ollama API'yi çağırır ve yanıt alır
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        print(f"Ollama API error: {e}")
        return None

def extract_json_from_text(text):
    """
    Metinden JSON çıkarır (AI bazen açıklama ekler)
    """
    # JSON objesi bul
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Direkt parse dene
    try:
        return json.loads(text)
    except:
        pass
    
    return None

def identify_app_name_jk(user_input):
    """
    Kullanıcı inputundan uygulama adını belirler
    NOT: _jk suffix - LLM kullanıldığını göstermek için
    """
    # Önce basit anahtar kelime eşleştirme dene (hızlı)
    user_input_lower = user_input.lower()
    if "tournament" in user_input_lower:
        return "tournament"
    elif "matchmaking" in user_input_lower:
        return "matchmaking"
    elif "chat" in user_input_lower:
        return "chat"
    
    # AI ile dene
    prompt = f"""Identify which application is being referenced. Available: chat, matchmaking, tournament

User: "{user_input}"

Respond with ONLY the application name (one word):"""

    response = call_ollama(prompt)
    if response:
        response_clean = response.strip().lower()
        if "tournament" in response_clean:
            return "tournament"
        elif "matchmaking" in response_clean:
            return "matchmaking"
        elif "chat" in response_clean:
            return "chat"
    
    return None

def apply_simple_update_jk(user_input, current_values):
    """
    Basit regex ile güncelleme yap (AI fallback)
    NOT: _jk suffix
    """
    user_lower = user_input.lower()
    
    # Memory güncelleme
    memory_match = re.search(r'memory.*?(\d+)\s*mb', user_lower)
    if memory_match:
        memory_value = int(memory_match.group(1))
        # tournament.value.json yapısı
        if "workloads" in current_values:
            for deployment_type in current_values.get("workloads", {}).values():
                for deployment in deployment_type.values():
                    if isinstance(deployment, dict) and "containers" in deployment:
                        for container in deployment["containers"].values():
                            if "resources" in container and "memory" in container["resources"]:
                                container["resources"]["memory"]["limitMiB"] = memory_value
                                print(f"Updated memory to {memory_value}MiB")
        return current_values
    
    # CPU güncelleme (yüzde olarak)
    cpu_match = re.search(r'cpu.*?(\d+)\s*%', user_lower)
    if cpu_match:
        cpu_percent = int(cpu_match.group(1)) / 100
        if "workloads" in current_values:
            for deployment_type in current_values.get("workloads", {}).values():
                for deployment in deployment_type.values():
                    if isinstance(deployment, dict) and "containers" in deployment:
                        for container in deployment["containers"].values():
                            if "resources" in container and "cpu" in container["resources"]:
                                current_limit = container["resources"]["cpu"].get("limitMilliCPU", 1000)
                                new_limit = int(current_limit * cpu_percent)
                                container["resources"]["cpu"]["limitMilliCPU"] = new_limit
                                print(f"Updated CPU to {new_limit}m ({cpu_percent*100}%)")
        return current_values
    
    # ENV variable
    env_match = re.search(r'set\s+(\w+)\s+env.*?to\s+(\w+)', user_lower)
    if env_match:
        env_name = env_match.group(1).upper()
        env_value = env_match.group(2)
        if "workloads" in current_values:
            for deployment_type in current_values.get("workloads", {}).values():
                for deployment in deployment_type.values():
                    if isinstance(deployment, dict) and "containers" in deployment:
                        for container in deployment["containers"].values():
                            if "envs" not in container:
                                container["envs"] = {}
                            container["envs"][env_name] = env_value
                            print(f"Set {env_name}={env_value}")
        return current_values
    
    return None

@app.route('/message', methods=['POST'])
def handle_message():
    """
    Kullanıcı mesajını işler ve güncellenmiş values JSON döndürür
    """
    try:
        data = request.get_json()
        user_input = data.get('input', '')
        
        if not user_input:
            return jsonify({"error": "No input provided"}), 400
        
        print(f"\n=== New Request ===")
        print(f"Input: {user_input}")
        
        # 1. Hangi uygulama olduğunu belirle
        app_name = identify_app_name_jk(user_input)
        if not app_name:
            return jsonify({"error": "Could not identify application"}), 400
        
        print(f"Identified app: {app_name}")
        
        # 2. Mevcut values'ı al
        values_response = requests.get(f"{VALUES_SERVICE_URL}/{app_name}")
        if values_response.status_code != 200:
            return jsonify({"error": f"Values not found for {app_name}"}), 404
        current_values = values_response.json()
        
        # 3. Basit regex ile güncelle (hızlı ve garantili)
        updated_values = apply_simple_update_jk(user_input, current_values.copy())
        
        if updated_values:
            print("Update successful with regex")
            return jsonify(updated_values), 200
        
        # 4. AI ile dene (fallback)
        print("Trying AI update...")
        schema_response = requests.get(f"{SCHEMA_SERVICE_URL}/{app_name}")
        if schema_response.status_code != 200:
            return jsonify({"error": f"Schema not found for {app_name}"}), 404
        schema = schema_response.json()
        
        prompt = f"""Update this JSON configuration based on user request.

User: "{user_input}"

Current JSON:
{json.dumps(current_values, indent=2)}

Return ONLY the complete updated JSON (no explanations):"""

        ai_response = call_ollama(prompt)
        if ai_response:
            updated_values = extract_json_from_text(ai_response)
            if updated_values:
                print("Update successful with AI")
                return jsonify(updated_values), 200
        
        return jsonify({"error": "Could not update values"}), 500
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    port = int(os.getenv("LISTEN_PORT", "5003"))
    app.run(host=host, port=port)