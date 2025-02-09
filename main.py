import time
import threading
import ccxt
import json
import os
import logging
from dotenv import load_dotenv
from Data.RSI import calculate_all_indicators, save_rsi_data

load_dotenv()

SAVE_DIR = "saves"
PROFILE_DIR = "profiles"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
if not os.path.exists(PROFILE_DIR):
    os.makedirs(PROFILE_DIR)

logging.basicConfig(filename='bot_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def list_profiles():
    """Liste tous les profils disponibles."""
    profiles = [f.replace(".json", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return profiles

def load_profile(profile_name):
    """Charge un profil utilisateur depuis un fichier JSON."""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    if not os.path.exists(profile_path):
        print(f"Profil '{profile_name}' introuvable.")
        return None

    with open(profile_path, 'r') as file:
        return json.load(file)

def save_profile(profile_name, profile_data):
    """Enregistre un profil utilisateur en JSON."""
    profile_path = os.path.join(PROFILE_DIR, f"{profile_name}.json")
    
    with open(profile_path, 'w') as file:
        json.dump(profile_data, file, indent=4)
    
    logging.info(f"Profil '{profile_name}' enregistré avec succès.")

def create_profile():
    """Crée un nouveau profil utilisateur."""
    profile_name = input("Nom du nouveau profil : ").strip()

    if not profile_name:
        print("Le nom du profil ne peut pas être vide.")
        return None

    profiles = list_profiles()
    if profile_name in profiles:
        print("Ce profil existe déjà.")
        return None

    api_key = input("Entrez votre clé API Binance : ")
    api_secret = input("Entrez votre secret API Binance : ")

    wallet = {}
    cryptos = input("Entrez les cryptos à suivre (ex: BTC/USDT, ETH/USDT) : ").strip().split(",")

    profile_data = {
        "name": profile_name,
        "wallet": wallet,
        "api_key": api_key,
        "api_secret": api_secret,
        "cryptos": [crypto.strip() for crypto in cryptos]
    }

    save_profile(profile_name, profile_data)
    return profile_data

def select_profile():
    """Menu pour sélectionner ou créer un profil."""
    while True:
        profiles = list_profiles()

        print("\n===== Gestion des Profils =====")
        if profiles:
            print("Profils existants :")
            for i, profile in enumerate(profiles):
                print(f"{i+1}. {profile}")

        print("\n0. Créer un nouveau profil")
        choice = input("Sélectionnez un profil (ou 0 pour en créer un) : ").strip()

        if choice == "0":
            create_profile()
            select_profile()
        elif choice.isdigit() and 1 <= int(choice) <= len(profiles):
            return load_profile(profiles[int(choice) - 1])

        print("Choix invalide. Veuillez réessayer.")

def initialize_exchange(api_key, api_secret):
    """Initialise l'API Binance avec les clés du profil sélectionné."""
    try:
        return ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
    except Exception as e:
        logging.critical(f"Erreur critique lors de l'initialisation de l'exchange : {e}")
        exit(1)

def rsi_worker(exchange, profile):
    """Thread pour calculer les RSI et MACD et stocker les données de manière structurée."""
    profile_name = profile["name"]
    profile_file = os.path.join(SAVE_DIR, f"{profile_name}.json")
    
    logging.info(f"Début de l'analyse des cryptos pour le profil {profile_name}.")

    while True:
        try:
            # Chargement des cryptos du profil
            symbols = profile["cryptos"]
            rsi_data = calculate_all_indicators(exchange, symbols)

            if not rsi_data:
                logging.warning(f"Aucune donnée récupérée pour {profile_name}.")
                continue

            # Ajout du timestamp et structuration des données
            market_data = {
                "profile": profile_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "cryptos": rsi_data
            }

            # Sauvegarde des données sous forme de fichier JSON
            with open(profile_file, "w") as file:
                json.dump(market_data, file, indent=4)
            
            logging.info(f"Données mises à jour pour {profile_name} : {len(rsi_data)} cryptos.")

        except ccxt.NetworkError as e:
            logging.warning(f"Problème API ({profile_name}) : {e}, tentative de reconnexion...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"Erreur dans rsi_worker ({profile_name}) : {e}")

        time.sleep(300)  # Pause de 5 minutes

if __name__ == "__main__":
    profile = select_profile()
    
    if profile is None:
        print("Aucun profil valide sélectionné. Fermeture du programme.")
        exit(1)

    exchange = initialize_exchange(profile["api_key"], profile["api_secret"])
    
    threading.Thread(target=rsi_worker, args=(exchange, profile), daemon=True).start()
    
    logging.info(f"Bot démarré avec le profil {profile['name']}. Appuyez sur Ctrl+C pour quitter.")
    
    while True:
        time.sleep(1)
