from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging

app = Flask(__name__)
CORS(app)

# Path to memory file
MEMORY_FILE = "foxie_memory.json"

# Load memory from file
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("Memory file not found or invalid, initializing fresh memory.")
        return {"blocked_words": [], "instructions": [], "remembered_users": []}

# Save memory to file
def save_memory(memory):
    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=4)
@app.route('/api/blocked-words', methods=['POST'])
def add_blocked_words():
    global memory
    # Ensure "blocked_words" exists in memory
    if "blocked_words" not in memory:
        memory["blocked_words"] = []
    
    # Get the incoming blocked words
    data = request.json
    words = data.get("words", [])
    
    # Update the blocked words list
    memory["blocked_words"] = list(set(memory["blocked_words"] + words))
    
    # Save updated memory back to JSON
    with open("foxie_memory.json", "w") as file:
        json.dump(memory, file, indent=4)
    
    return jsonify({"blockedWords": memory["blocked_words"]}), 200

@app.route('/api/blocked-words', methods=['GET'])
def get_blocked_words():
    global memory
    # Ensure "blocked_words" exists in memory
    if "blocked_words" not in memory:
        memory["blocked_words"] = []

    return jsonify({"blockedWords": memory["blocked_words"]}), 200


# Initialize memory
memory = load_memory()

# Route: Test server is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server is running!"}), 200
# Route: Add instructions
@app.route("/api/instructions", methods=["POST"])
def add_instructions():
    global memory
    data = request.get_json()
    instructions = data.get("instructions", [])
    
    # Avoid duplicates
    memory["instructions"] = list(set(memory["instructions"] + instructions))
    save_memory(memory)
    
    return jsonify({"message": "Instructions added", "instructions": memory["instructions"]}), 200

# Route: Add to memory
@app.route("/api/memory", methods=["POST"])
def add_memory():
    global memory
    data = request.get_json()
    remembered_user = data.get("rememberedUser", None)
    
    if remembered_user and remembered_user not in memory["remembered_users"]:
        memory["remembered_users"].append(remembered_user)
        save_memory(memory)
    
    return jsonify({"message": "Memory updated", "rememberedUsers": memory["remembered_users"]}), 200

# Route: Get all memory data
@app.route("/api/memory", methods=["GET"])
def get_memory():
    return jsonify(memory), 200

# Route: Delete blocked words
@app.route("/api/blocked-words", methods=["DELETE"])
def delete_blocked_words():
    global memory
    data = request.get_json()
    words_to_delete = data.get("words", [])
    memory["blocked_words"] = [word for word in memory["blocked_words"] if word not in words_to_delete]
    save_memory(memory)
    
    return jsonify({"message": "Blocked words deleted", "blockedWords": memory["blocked_words"]}), 200

# Route: Delete instructions
@app.route("/api/instructions", methods=["DELETE"])
def delete_instructions():
    global memory
    data = request.get_json()
    instructions_to_delete = data.get("instructions", [])
    memory["instructions"] = [inst for inst in memory["instructions"] if inst not in instructions_to_delete]
    save_memory(memory)
    
    return jsonify({"message": "Instructions deleted", "instructions": memory["instructions"]}), 200

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, use_reloader=False)

