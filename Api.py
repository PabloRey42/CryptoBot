from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)
SAVE_DIR = "saves"

@app.before_request
def log_request_info():
    print(f"Requête reçue : {request.method} {request.url}")

@app.route('/saves', methods=['GET'])
def list_saves():
    """Liste toutes les sauvegardes disponibles."""
    saves = [f.replace('.json', '') for f in os.listdir(SAVE_DIR) if f.endswith('.json')]
    return jsonify({"saves": saves})

@app.route('/save/<string:name>', methods=['GET'])
def get_save(name):
    """Récupère une sauvegarde spécifique."""
    filename = os.path.join(SAVE_DIR, f"{name}.json")
    if not os.path.exists(filename):
        return jsonify({"error": "Sauvegarde introuvable"}), 404
    with open(filename, "r") as file:
        data = json.load(file)
    return jsonify(data)

@app.route('/save', methods=['POST'])
def create_save():
    """Crée une nouvelle sauvegarde."""
    content = request.json
    name = content.get("name")
    portfolio = content.get("portfolio")
    if not name or not portfolio:
        return jsonify({"error": "Nom ou portefeuille manquant"}), 400
    filename = os.path.join(SAVE_DIR, f"{name}.json")
    with open(filename, "w") as file:
        json.dump(portfolio, file, indent=4)
    return jsonify({"message": f"Sauvegarde {name} créée avec succès."})
