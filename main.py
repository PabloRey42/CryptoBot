import time
import threading
import ccxt
import json
import os
from Data.RSI import calculate_all_rsi, save_rsi_data

SAVE_DIR = "saves"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def initialize_exchange(mode="test"):
    """Initialise l'API Binance en fonction du mode choisi."""
    if mode == "real":
        return ccxt.binance({
            'apiKey': 'Nope',
            'secret': 'Nope',
            'enableRateLimit': True
        })
    elif mode == "test":
        exchange = ccxt.binance({
            'apiKey': 'o6pobrhqHu3fsYAs8mT5G8YmCFj0kSqzPXivNHstQ4Mt6O7pc3Pd8UN3ffJSRjYR',
            'secret': 'AMZyOsb6QT8T9mLc1xnG6Syx9JHJdS651w6Oi6axDPR98kMAAWXCKxkBlQIwMuvl',
            'enableRateLimit': True
        })
        exchange.set_sandbox_mode(True)
        return exchange
    else:
        raise ValueError("Mode invalide. Choisissez 'real' ou 'test'.")

def rsi_worker(exchange):
    """Thread pour calculer les RSI toutes les 5 minutes."""
    symbols = [market['symbol'] for market in exchange.load_markets().values() if market['quote'] == 'USDT']
    while True:
        try:
            print("Test")
            rsi_data = calculate_all_rsi(exchange, symbols)
            save_rsi_data(rsi_data)
            print(f"RSI mis à jour pour {len(rsi_data)} cryptos.")
        except Exception as e:
            print(f"Erreur dans le calcul des RSI : {e}")
        time.sleep(300)

if __name__ == "__main__":
    mode = input("Choisissez le mode ('real' ou 'test') : ").strip().lower()
    try:
        exchange = initialize_exchange(mode)

        threading.Thread(target=rsi_worker, args=(exchange,), daemon=True).start()
        print("Calcul des RSI en cours. Appuyez sur Ctrl+C pour quitter.")

        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Erreur : {e}")
