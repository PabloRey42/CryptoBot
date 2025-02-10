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

# 🔹 Charger les variables d'environnement
load_dotenv()

# 🔹 Dossiers de stockage
SAVE_DIR = "saves"
PROFILE_DIR = "profiles"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

# 🔹 Logging
logging.basicConfig(filename='bot_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# ========================== 🔥 GESTION DES PROFILS ==========================
def list_profiles():
    """Liste tous les profils disponibles."""
    profiles = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return profiles

def load_profile(profile_name):
    """Charge un profil utilisateur depuis un fichier JSON."""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    if not os.path.exists(profile_path):
        print_log(f"Profil '{profile_name}' introuvable.", "ERROR")
        return None

    with open(profile_path, 'r') as file:
        return json.load(file)

def save_profile(profile_name, profile_data):
    """Enregistre un profil utilisateur en JSON."""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    with open(profile_path, 'w') as file:
        json.dump(profile_data, file, indent=4)
    
    print_log(f"Profil '{profile_name}' enregistré avec succès.")

def select_profile():
    """Menu pour sélectionner ou créer un profil."""
    while True:
        profiles = list_profiles()

        print("\n===== Gestion des Profils =====")
        if profiles:
            print("Profils existants :")
            for i, profile in enumerate(profiles):
                print(f"{i+1}. {profile}")

        choice = input("\nSélectionnez un profil (ou appuyez sur Entrée pour utiliser le profil par défaut) : ").strip()

        if choice == "":
            return load_profile("default")  # Charge le profil par défaut

        elif choice.isdigit() and 1 <= int(choice) <= len(profiles):
            profile = load_profile(profiles[int(choice) - 1])

            if not profile:
                return None

            if not profile.get("cryptos") or profile["cryptos"] == [""]:
                print_log(f"Aucune crypto définie pour {profile['name']}, veuillez les ajouter.", "ERROR")
                return None

            return profile

        print("Choix invalide. Veuillez réessayer.")

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
            'options': {'defaultType': 'spot'},  # Obligatoire pour Testnet
        })

        # ✅ Activation du mode sandbox pour utiliser Binance Testnet
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
def rsi_worker(exchange, profile):
    """Thread pour calculer les RSI et MACD avec affichage en direct."""
    profile_name = profile["name"]
    profile_file = os.path.join("saves", f"{profile_name}.json")

    print_log(f"Début de l'analyse des cryptos pour le profil {profile_name}.")
    
    while True:
        try:
            symbols = profile["cryptos"]

            if not symbols:
                print_log("🚨 Aucune crypto définie, arrêt du bot.", "ERROR")
                return

            print_log(f"Récupération des données pour {len(symbols)} cryptos suivies...")

            rsi_data = calculate_all_indicators(exchange, symbols)

            if not rsi_data:
                print_log("Aucune donnée récupérée, problème API ou cryptos invalides.", "WARNING")
                continue

            market_data = {
                "profile": profile_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "cryptos": rsi_data
            }

            with open(profile_file, "w") as file:
                json.dump(market_data, file, indent=4)

            print_log(f"Données mises à jour pour {profile_name} ({len(rsi_data)} cryptos).")

        except ccxt.NetworkError as e:
            print_log(f"Problème API ({profile_name}) : {e}, tentative de reconnexion...", "WARNING")
            time.sleep(10)
        except Exception as e:
            print_log(f"Erreur dans rsi_worker ({profile_name}) : {e}", "ERROR")

        time.sleep(300)  # Pause de 5 minutes

# ========================== 🚀 LANCEMENT DU BOT ==========================
if __name__ == "__main__":
    profile = select_profile()
    
    if profile is None:
        print_log("❌ Aucun profil valide sélectionné. Fermeture du programme.", "ERROR")
        exit(1)

    exchange = initialize_exchange()
    test_binance_connection(exchange)

    threading.Thread(target=rsi_worker, args=(exchange, profile), daemon=True).start()

    print_log(f"Bot démarré avec le profil {profile['name']}. Appuyez sur Ctrl+C pour quitter.")
    send_telegram_message(f"Zebi y a {profile['name']} qui démarre le bot. Appel les Hendeks")

    while True:
        time.sleep(1)
