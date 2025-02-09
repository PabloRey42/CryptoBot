from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import psycopg2
import bcrypt
import jwt
import datetime

# Configuration Flask
app = Flask(__name__)
CORS(app)
SECRET_KEY = "super_secret_key"  # 🔐 Change cette clé pour une clé forte et sécurisée

# Chemin des fichiers de sauvegarde
SAVE_DIR = "saves"
RSI_FILE = os.path.join(SAVE_DIR, "rsi_data.json")

# Connexion PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname="crypto_users",
        user="crypto_admin",
        password="7102Bdd*",
        host="127.0.0.1",
        port="5432"
    )

# ========================== 🔐 AUTHENTIFICATION ==========================

@app.route('/login', methods=['POST'])
def login():
    """ Vérifie les identifiants de l'utilisateur et génère un token JWT """
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier si l'utilisateur existe
    cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 401

    hashed_password = user[0]

    # Vérifier le mot de passe avec bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
        return jsonify({"error": "Mot de passe incorrect"}), 401

    # Générer un token JWT
    token = jwt.encode(
        {"email": email, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify({"message": "Connexion réussie", "token": token}), 200

@app.route('/register', methods=['POST'])
def register():
    """ Enregistre un nouvel utilisateur avec mot de passe haché """
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier si l'email existe déjà
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email déjà utilisé"}), 400

    # Hacher le mot de passe avant stockage
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insérer l'utilisateur
    cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Utilisateur enregistré avec succès"}), 201

# ========================== 🔍 ROUTES EXISTANTES ==========================

@app.route('/saves', methods=['GET'])
def list_saves():
    """Liste toutes les sauvegardes disponibles."""
    saves = [f.replace('.json', '') for f in os.listdir(SAVE_DIR) if f.endswith('.json') and f != 'rsi_data.json']
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

@app.route('/rsi', methods=['GET'])
def get_all_rsi():
    """Retourne les données RSI de toutes les cryptos."""
    if os.path.exists(RSI_FILE):
        with open(RSI_FILE, 'r') as file:
            data = json.load(file)
        return jsonify(data)
    return jsonify({"error": "Aucune donnée RSI disponible."}), 404

@app.route('/rsi/<symbol>', methods=['GET'])
def get_rsi_for_symbol(symbol):
    """Retourne les données RSI pour une crypto spécifique."""
    if os.path.exists(RSI_FILE):
        with open(RSI_FILE, 'r') as file:
            data = json.load(file)
        if symbol in data:
            return jsonify(data[symbol])
    return jsonify({"error": f"RSI introuvable pour {symbol}."}), 404

# ========================== 🚀 LANCEMENT DU SERVEUR ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=('cert.pem', 'key.pem'))
