import time
import threading
import ccxt
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from Data.RSI import calculate_all_indicators, save_rsi_data
from colorama import Fore, Style
from Api import send_telegram_message
from binance.client import Client
import psycopg2

# 🔹 Charger les variables d'environnement
load_dotenv()

# 🔹 Dossiers de stockage
SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 🔹 Logging
logging.basicConfig(filename='bot_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ========================== 🔥 CONNEXION À LA BDD ==========================
def get_db_connection():
    """Connexion PostgreSQL"""
    return psycopg2.connect(
        dbname="crypto_users",
        user="crypto_admin",
        password="7102Bdd*",
        host="127.0.0.1",
        port="5432"
    )

# ========================== 🔥 FONCTIONS DE LOGGING ==========================
def print_log(message, level="INFO"):
    """Affiche des logs formatés avec timestamp et couleurs."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level == "INFO":
        print(f"{Fore.GREEN}[{now}] [INFO] {message}{Style.RESET_ALL}")
    elif level == "WARNING":
        print(f"{Fore.YELLOW}[{now}] [WARNING] {message}{Style.RESET_ALL}")
    elif level == "ERROR":
        print(f"{Fore.RED}[{now}] [ERROR] {message}{Style.RESET_ALL}")

# ========================== 🔥 GESTION DES CRYPTOS DANS LA BDD ==========================
def get_user_cryptos(user_email):
    """Récupère uniquement les cryptos activées pour un utilisateur depuis PostgreSQL."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT crypto_symbol FROM user_cryptos WHERE user_email = %s AND is_active = TRUE", (user_email,))
    cryptos = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return cryptos

# ========================== 🔥 GESTION DE BINANCE ==========================
def initialize_exchange():
    """Initialise l'API Binance avec les clés API provenant du .env"""
    api_key = os.getenv("BINANCE_TEST_API_KEY")
    api_secret = os.getenv("BINANCE_TEST_SECRET_KEY")

    if not api_key or not api_secret:
        print_log("❌ Erreur : Clés API Testnet non trouvées dans .env !", "ERROR")
        exit(1)

    print_log(f"🔑 Clés API Testnet utilisées : {api_key[:5]}****", "INFO")

    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},  
        })
        client = Client(api_key, api_secret, testnet=True)
        account_info = client.get_account()
        balances = account_info['balances']
        
        print_log("📊 Solde Binance Testnet :")
        for asset in balances:
            if float(asset['free']) > 0 or float(asset['locked']) > 0:  
                print_log(f"{asset['asset']}: {asset['free']} dispo, {asset['locked']} verrouillé")

        exchange.set_sandbox_mode(True)
        print_log("🔵 Mode sandbox activé (Testnet).", "INFO")

        return exchange
    except Exception as e:
        print_log(f"❌ Erreur d'initialisation Binance : {e}", "ERROR")
        exit(1)

def test_binance_connection(exchange):
    """Teste si Binance Testnet accepte les clés API."""
    try:
        balance = exchange.fetch_balance()
        print_log("✅ Connexion Binance Testnet OK (Solde récupéré).", "INFO")
    except Exception as e:
        print_log(f"❌ Erreur API Binance Testnet : {e}", "ERROR")

# ========================== 🔥 THREAD PRINCIPAL ==========================
def rsi_worker(exchange, user_email):
    """Thread pour analyser le RSI et exécuter des trades automatiquement."""
    
    print_log(f"🚀 Démarrage de l'analyse des cryptos pour {user_email}.")

    while True:
        try:
            symbols = get_user_cryptos(user_email)

            if not symbols:
                print_log(f"🚨 Aucun crypto suivi pour {user_email}.", "WARNING")
                time.sleep(60)  # Attendre avant de re-vérifier
                continue

            print_log(f"📊 Analyse des cryptos suivies : {symbols}")

            rsi_data = calculate_all_indicators(exchange, symbols)

            if not rsi_data:
                print_log("Aucune donnée récupérée, problème API ou cryptos invalides.", "WARNING")
                continue

            # 🔥 Stocker les résultats dans un fichier JSON
            with open(f"saves/{user_email}.json", "w") as file:
                json.dump({"user_email": user_email, "cryptos": rsi_data}, file, indent=4)

            print_log(f"✅ Données mises à jour pour {user_email}.")

        except ccxt.NetworkError as e:
            print_log(f"⚠️ Problème API : {e}, tentative de reconnexion...", "WARNING")
            time.sleep(10)
        except Exception as e:
            print_log(f"❌ Erreur dans rsi_worker() : {e}", "ERROR")

        time.sleep(300)  # Pause de 5 minutes avant la prochaine analyse

# ========================== 🚀 LANCEMENT DU BOT ==========================
if __name__ == "__main__":
    user_email = input("Entrez votre email Binance : ").strip().lower()
    
    if not user_email:
        print_log("❌ Aucun email fourni. Fermeture du programme.", "ERROR")
        exit(1)

    exchange = initialize_exchange()
    test_binance_connection(exchange)

    threading.Thread(target=rsi_worker, args=(exchange, user_email), daemon=True).start()

    print_log(f"Bot démarré pour {user_email}. Appuyez sur Ctrl+C pour quitter.")
    send_telegram_message(f"🚀 Bot démarré pour {user_email}. Analyse des cryptos en cours.")

    while True:
        time.sleep(1)
