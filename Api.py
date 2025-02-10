from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import psycopg2
import bcrypt
import jwt
import datetime
from telegram import Bot
import asyncio
from binance.client import Client
from dotenv import load_dotenv

TELEGRAM_BOT_TOKEN = "8182679555:AAEisPOqAXbYMCIzCS0q42qV4NYorBePg38"
CHAT_ID = "7301678219"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

load_dotenv()


app = Flask(__name__)
CORS(app)
SECRET_KEY = "super_secret_key"

SAVE_DIR = "saves"
PROFILE_DIR = "profiles"
RSI_FILE = os.path.join(SAVE_DIR, "rsi_data.json")

# Vérifier que les dossiers existent
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# ========================== 🛠 BASE DE DONNÉES ==========================

def get_db_connection():
    """Connexion sécurisée à PostgreSQL"""
    try:
        conn = psycopg2.connect(
            dbname="crypto_users",
            user="crypto_admin",
            password="7102Bdd*",
            host="127.0.0.1",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        return None

# ========================== 🔐 AUTHENTIFICATION ==========================

@app.route('/login', methods=['POST'])
def login():
    """ Vérifie les identifiants et génère un token JWT """
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 401

    hashed_password = user[0]

    if not bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
        return jsonify({"error": "Mot de passe incorrect"}), 401

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
    if not conn:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email déjà utilisé"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insérer l'utilisateur
    cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Utilisateur enregistré avec succès"}), 201

# ========================== 👤 GESTION DES PROFILS & WALLETS ==========================

def load_profile(profile_name):
    """Charge un profil utilisateur"""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    if not os.path.exists(profile_path):
        return None

    with open(profile_path, 'r') as file:
        return json.load(file)

@app.route('/profiles', methods=['GET'])
def get_profiles():
    """Retourne la liste des profils disponibles"""
    profiles = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return jsonify({"profiles": profiles})

@app.route('/profile/<profile_name>', methods=['GET'])
def get_profile_data(profile_name):
    """Retourne les informations du profil"""
    profile = load_profile(profile_name)

    if profile is None:
        return jsonify({"error": "Profil introuvable"}), 404

    return jsonify(profile)

@app.route('/profile/<profile_name>/cryptos', methods=['GET'])
def get_cryptos(profile_name):
    """Retourne les cryptos suivies par un profil"""
    profile = load_profile(profile_name)

    if profile is None:
        return jsonify({"error": "Profil introuvable"}), 404

    return jsonify({"cryptos": profile.get("cryptos", [])})

@app.route('/account/wallet', methods=['GET'])
def get_wallet():
    api_key = os.getenv("BINANCE_TEST_API_KEY")
    api_secret = os.getenv("BINANCE_TEST_SECRET_KEY")

    if not api_key or not api_secret:
        return jsonify({"error": "Profil inconnu ou clés API manquantes"}), 400

    client = Client(api_key, api_secret, testnet=True)

    account_info = client.get_account()
    all_assets = account_info['balances']

    print("🔍 Liste complète des cryptos disponibles sur Binance Testnet:")
    for asset in all_assets:
        print(f"{asset['asset']} -> Free: {asset['free']}, Locked: {asset['locked']}")

    owned_assets = []
    for asset in all_assets:
        free_balance = float(asset['free'])
        locked_balance = float(asset['locked'])

        if free_balance > 0 or locked_balance > 0:  
            owned_assets.append({
                "asset": asset['asset'],
                "free": free_balance,
                "locked": locked_balance
            })

    print("✅ Cryptos détenues après filtrage:", owned_assets)

    return jsonify({"wallet": owned_assets}), 200

    
# ========================== 🔍 SUIVIES DES CRYPTOS PAR COMPTES ==========================

@app.route('/api/user/cryptos', methods=['POST'])
def add_crypto():
    data = request.json
    user_id = data.get("user_id")
    crypto_symbol = data.get("crypto_symbol")

    if not user_id or not crypto_symbol:
        return jsonify({"error": "User ID et crypto requis"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO user_cryptos (user_id, crypto_symbol) VALUES (%s, %s)", (user_id, crypto_symbol))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": f"{crypto_symbol} ajouté à la liste suivie"}), 201

@app.route('/api/user/cryptos/<int:user_id>', methods=['GET'])
def get_user_cryptos(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT crypto_symbol FROM user_cryptos WHERE user_id = %s", (user_id,))
    cryptos = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({"cryptos": [crypto[0] for crypto in cryptos]})


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

# ========================== 🤖Bot Telegram ==========================

async def send_telegram_message_async(message):
    """Envoie un message Telegram de manière asynchrone."""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Message envoyé : {message}")
    except Exception as e:
        print(f"Erreur lors de l'envoi du message Telegram : {e}")

def send_telegram_message(message):
    """Lance la coroutine de manière non bloquante dans l'event loop."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(send_telegram_message_async(message))  # Lancement en tâche de fond
    else:
        loop.run_until_complete(send_telegram_message_async(message))


# ========================== 🚀 LANCEMENT DU SERVEUR ==========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        ssl_context=(
            "/etc/letsencrypt/live/bot.crypteau.fr/fullchain.pem",
            "/etc/letsencrypt/live/bot.crypteau.fr/privkey.pem"
        )
    )
