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
from binance.exceptions import BinanceAPIException
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps


app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://bot.crypteau.fr"], methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])
SECRET_KEY = "Secret_key_de_ouf_de_test"

limiter = Limiter(get_remote_address, app=app, default_limits=["100 per minute"])

TELEGRAM_BOT_TOKEN = "8182679555:AAEisPOqAXbYMCIzCS0q42qV4NYorBePg38"
CHAT_ID = "7301678219"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

load_dotenv()

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
@limiter.limit("100 per minute")
def login():
    """ Vérifie les identifiants et génère un token JWT sécurisé """
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500
    cursor = conn.cursor()

    cursor.execute("SELECT id, password FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 401

    user_id, hashed_password = user[0], user[1]

    if not bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
        return jsonify({"error": "Mot de passe incorrect"}), 401

    # ✅ Générer le JWT
    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
        SECRET_KEY,
        algorithm="HS256"
    )

    # ✅ Envoyer le token sous forme de cookie sécurisé
    response = jsonify({"message": "Connexion réussie", "user_id": user_id})
    response.set_cookie(
        "token", token,
        httponly=True, secure=True, samesite="None", max_age=7200, domain=".crypteau.fr"  # ⚠️ Ajoute `domain=".crypteau.fr"`
    )

    return response


@app.route('/check-auth', methods=['GET'])
def check_auth():
    """ Vérifie si un utilisateur est connecté grâce au token JWT stocké dans le cookie """
    token = request.cookies.get("token")

    if not token:
        return jsonify({"authenticated": False}), 401

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return jsonify({"authenticated": True, "user_id": decoded["user_id"]})
    except jwt.ExpiredSignatureError:
        return jsonify({"authenticated": False, "error": "Token expiré"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"authenticated": False, "error": "Token invalide"}), 401



@app.route('/logout', methods=['POST'])
def logout():
    """ Déconnecte l'utilisateur en supprimant le cookie JWT """
    response = jsonify({"message": "Déconnexion réussie"})
    response.set_cookie("token", "", expires=0, path="/")
    return response, 200



@app.route('/register', methods=['POST'])
def register():
    """ Enregistre un nouvel utilisateur et ajoute une crypto par défaut """
    data = request.json
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")  # 🔥 Si aucun rôle n'est spécifié, il sera "user"

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500
    cursor = conn.cursor()

    # Vérifier si l'email existe déjà
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email déjà utilisé"}), 400

    # Hacher le mot de passe avant stockage
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insérer l'utilisateur
    cursor.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s) RETURNING id", 
                   (email, hashed_password, role))
    user_id = cursor.fetchone()[0]

    # 🔹 Ajouter une crypto par défaut
    default_crypto = "BTC/USDT"
    cursor.execute("INSERT INTO user_cryptos (user_id, crypto_symbol, is_active) VALUES (%s, %s, TRUE)",
               (user_id, default_crypto))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Utilisateur enregistré avec succès", "role": role, "crypto": default_crypto}), 201

# ========================== 👤 GESTION DES PROFILS & WALLETS ==========================

def token_required(f):
    """Décorateur pour protéger les routes avec un token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 🔹 Vérifie l'Authorization Header en priorité
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        # 🔹 Si pas de token en header, tente de récupérer depuis les cookies
        if not token:
            token = request.cookies.get("token")  # 🔥 Ajoute cette ligne

        if not token:
            return jsonify({"error": "Token manquant"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = data.get("user_id")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token invalide"}), 401

        return f(user_id, *args, **kwargs)

    return decorated

@app.route('/profile/cryptos', methods=['GET'])
@token_required
def get_active_cryptos(user_email):
    """Retourne les cryptos activées pour l'utilisateur connecté."""
    print(f"🔍 Email extrait du token : {user_email}")  # Debugging
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT crypto_symbol FROM user_cryptos WHERE user_id = %s AND is_active = TRUE", (user_id,))
    cryptos = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify({"cryptos": cryptos})

@app.route('/profile/cryptos/add', methods=['POST'])
@token_required
def add_crypto(user_id):
    """Ajoute une crypto à la liste des cryptos suivies."""
    data = request.json
    crypto = data.get("crypto")

    if not crypto:
        return jsonify({"error": "Veuillez fournir une crypto."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user_cryptos WHERE user_id = %s AND crypto_symbol = %s", (user_id, crypto.upper()))
    existing_crypto = cursor.fetchone()

    if existing_crypto:
        cursor.execute("UPDATE user_cryptos SET is_active = TRUE WHERE user_id = %s AND crypto_symbol = %s", (user_id, crypto.upper()))
    else:
        cursor.execute("INSERT INTO user_cryptos (user_id, crypto_symbol, is_active) VALUES (%s, %s, TRUE)", (user_id, crypto.upper()))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"Crypto {crypto.upper()} ajoutée"}), 200


@app.route('/profile/cryptos/remove', methods=['POST'])
@token_required
def remove_crypto(user_id):  # ✅ Remplace user_email par user_id
    """Désactive une crypto suivie."""
    data = request.json
    crypto = data.get("crypto")

    if not crypto:
        return jsonify({"error": "Veuillez fournir une crypto."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user_cryptos WHERE user_id = %s AND crypto_symbol = %s AND is_active = TRUE", 
                   (user_id, crypto.upper()))
    existing_crypto = cursor.fetchone()

    if not existing_crypto:
        return jsonify({"error": f"Crypto {crypto.upper()} non trouvée ou déjà désactivée."}), 404

    cursor.execute("UPDATE user_cryptos SET is_active = FALSE WHERE user_id = %s AND crypto_symbol = %s", 
                   (user_id, crypto.upper()))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": f"Crypto {crypto.upper()} désactivée"}), 200




def load_profile(profile_name):
    """Charge un profil utilisateur"""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    if not os.path.exists(profile_path):
        return None

    with open(profile_path, 'r') as file:
        return json.load(file)
       
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """ Récupère les informations de l'utilisateur connecté """
    token = request.cookies.get("token")  # Récupère le token JWT du cookie

    if not token:
        return jsonify({"error": "Non authentifié"}), 401

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded["user_id"]

        conn = get_db_connection()
        cur = conn.cursor()

        # 🔹 Récupérer `role` depuis la base de données
        cur.execute("SELECT id, email, name, surname, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        # 🔥 Debugging : afficher les données de l'utilisateur dans les logs
        print("User data from DB:", user)

        return jsonify({
            "user_id": user[0],
            "email": user[1],
            "name": user[2],
            "surname": user[3],
            "role": user[4]
        })
    
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 401



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
    user_id = request.user_id
    print(f"🔐 Accès au wallet pour l'utilisateur {user_id}")
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



@app.route('/account/reset', methods=['PUT'])
def reset_wallet():
    """ Réinitialise le portefeuille en vendant tous les actifs disponibles """
    
    api_key = os.getenv("BINANCE_TEST_API_KEY")
    api_secret = os.getenv("BINANCE_TEST_SECRET_KEY")
    
    if not api_key or not api_secret:
        return jsonify({"error": "Clés API manquantes"}), 400

    client = Client(api_key, api_secret, testnet=True)

    TRADING_PAIRS = ["BTC", "BNB", "ETH", "USDT"] 

    try:
        account_info = client.get_account()
    except BinanceAPIException as e:
        return jsonify({"error": f"Erreur API Binance: {str(e)}"}), 500

    owned_assets = [
        {
            "asset": asset['asset'],
            "free": float(asset['free'])
        }
        for asset in account_info['balances']
        if float(asset['free']) > 0 
    ]

    if not owned_assets:
        return jsonify({"message": "Aucun actif à vendre"}), 200

    results = []
    
    for asset in owned_assets:
        symbol = None
        for pair in TRADING_PAIRS:
            test_symbol = f"{asset['asset']}{pair}"
            try:
                symbol_info = client.get_symbol_info(test_symbol)
                if symbol_info:  # Vérifie si la paire existe
                    symbol = test_symbol
                    break
            except BinanceAPIException:
                continue

        if symbol:
            try:
                lot_size_info = client.get_symbol_info(symbol)['filters']
                min_qty = None
                for filter in lot_size_info:
                    if filter['filterType'] == 'LOT_SIZE':
                        min_qty = float(filter['minQty'])
                        break

                if min_qty and asset['free'] < min_qty:
                    print(f"⚠️ Quantité insuffisante pour vendre {asset['asset']} ({asset['free']} < {min_qty})")
                    results.append({"asset": asset['asset'], "status": "non vendu (quantité insuffisante)"})
                    continue  # Passe à l'actif suivant

                print(f"🔴 Vente de {asset['free']} {asset['asset']} sur la paire {symbol}")
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=round(asset['free'] - (asset['free'] * 0.001), 8)  # Ajustement pour éviter les erreurs
                )
                print(f"✅ Ordre exécuté : {order['orderId']}")
                results.append({"asset": asset['asset'], "status": "vendu", "order_id": order['orderId']})

            except BinanceAPIException as e:
                print(f"⚠️ Erreur lors de la vente de {asset['asset']} : {e}")
                results.append({"asset": asset['asset'], "status": "erreur", "error": str(e)})
        else:
            print(f"❌ Impossible de vendre {asset['asset']} : Aucune paire trouvée")
            results.append({"asset": asset['asset'], "status": "non vendu (paire introuvable)"})

    return jsonify({"message": "Processus terminé", "results": results}), 200

    
# ========================== 🔍 SUIVIES DES CRYPTOS PAR COMPTES ==========================

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
