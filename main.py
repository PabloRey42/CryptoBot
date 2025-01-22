import ccxt
import json
import os

SAVE_DIR = "saves"  # Répertoire pour stocker les sauvegardes

# Créer le répertoire si nécessaire
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def initialize_exchange(mode="test"):
    """Initialise l'API Binance en fonction du mode choisi."""
    if mode == "real":
        return ccxt.binance({
    'apiKey': 'X87Mh6f21pB3S0G5EcnJqrQVz2sgfIhviAiVpJnVEVPqtlDLewXNKmO9tLJNh5R5',
    'secret': 'An80LcOV6QwNjqVWGwuP8GmHahxJi7RRRMZUtm7odgIOm1oGQVuZKv2PXUlHMNrz',
    'enableRateLimit': True
        })
    elif mode == "test":
        exchange = ccxt.binance({
    'apiKey': 'o6pobrhqHu3fsYAs8mT5G8YmCFj0kSqzPXivNHstQ4Mt6O7pc3Pd8UN3ffJSRjYR',
    'secret': 'AMZyOsb6QT8T9mLc1xnG6Syx9JHJdS651w6Oi6axDPR98kMAAWXCKxkBlQIwMuvl',
    'enableRateLimit': True
        })
        exchange.set_sandbox_mode(True)  # Activer le mode sandbox pour le test
        return exchange
    else:
        raise ValueError("Mode invalide. Choisissez 'real' ou 'test'.")

def setup_test_portfolio():
    """Permet à l'utilisateur de configurer un portefeuille fictif."""
    print("Configurez votre portefeuille fictif pour le mode test.")
    portfolio = {}
    while True:
        crypto = input("Nom de la crypto (ex: BTC, ETH, USDT) ou 'stop' pour terminer : ").upper()
        if crypto == "STOP":
            break
        amount = float(input(f"Quantité de {crypto} : "))
        portfolio[crypto] = amount
    return portfolio

def list_saves():
    """Liste toutes les sauvegardes disponibles."""
    saves = [f.replace('.json', '') for f in os.listdir(SAVE_DIR) if f.endswith('.json')]
    if not saves:
        raise FileNotFoundError("Aucune sauvegarde disponible.")
    return saves

def save_portfolio(data, save_name):
    """Sauvegarde un portefeuille fictif dans un fichier JSON."""
    filename = os.path.join(SAVE_DIR, f"{save_name}.json")
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Sauvegarde créée : {filename}")

def load_portfolio(save_name):
    """Charge un portefeuille fictif depuis un fichier JSON."""
    filename = os.path.join(SAVE_DIR, f"{save_name}.json")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Aucune sauvegarde trouvée pour : {save_name}")
    with open(filename, "r") as file:
        return json.load(file)

def fetch_bot_info(exchange, test_portfolio=None):
    """Récupère et retourne les informations principales du bot."""
    if test_portfolio:
        balance = test_portfolio  # Utiliser le portefeuille fictif en mode test
    else:
        balance = exchange.fetch_balance()['total']

    server_time = exchange.fetch_time()
    return {
        "balance": balance,
        "server_time": server_time,
        "status": "connected"
    }

# Choisir le mode au lancement
mode = input("Choisissez le mode ('real' ou 'test') : ").strip().lower()
try:
    # Initialisation de l'API Binance
    exchange = initialize_exchange(mode)

    # Synchroniser l'horloge avec Binance
    exchange.load_time_difference()

    # Si mode test, demander une sauvegarde ou en créer une nouvelle
    test_portfolio = None
    if mode == "test":
        action = input("Voulez-vous charger une sauvegarde existante ('load') ou en créer une nouvelle ('new') ? ").strip().lower()
        if action == "load":
            saves = list_saves()
            print("Sauvegardes disponibles :")
            for idx, save in enumerate(saves):
                print(f"{idx + 1}. {save}")
            choice = int(input("Choisissez une sauvegarde (entrez le numéro) : ")) - 1
            if choice < 0 or choice >= len(saves):
                raise ValueError("Choix invalide.")
            save_name = saves[choice]
            test_portfolio = load_portfolio(save_name)
            print(f"Sauvegarde chargée : {save_name}")
        elif action == "new":
            test_portfolio = setup_test_portfolio()
            save_name = input("Entrez un nom pour cette sauvegarde : ").strip()
            save_portfolio(test_portfolio, save_name)
        else:
            raise ValueError("Action invalide. Choisissez 'load' ou 'new'.")

    # Récupérer les informations
    bot_info = fetch_bot_info(exchange, test_portfolio)

    # Afficher les informations
    print("Informations du bot :")
    print(json.dumps(bot_info, indent=4))

except Exception as e:
    print(f"Erreur : {e}")
