import ccxt
import pandas as pd
import json
import time
import os
import logging

# Fichier de sauvegarde des données RSI & MACD
RSI_FILE = "saves/rsi_data.json"

# Configuration du logging
logging.basicConfig(filename='rsi_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_ohlcv(exchange, symbol, timeframe='5m', limit=100):
    """Récupère les données OHLCV pour une crypto donnée."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données OHLCV pour {symbol}: {e}")
        return None

def calculate_rsi(data, period=14):
    """Calcule le RSI à partir des prix de clôture."""
    try:
        if len(data) < period:
            raise ValueError("Pas assez de données pour calculer le RSI")

        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        if rsi.isna().iloc[-1] or not (0 <= rsi.iloc[-1] <= 100):
            logging.warning(f"RSI invalide détecté : {rsi.iloc[-1]} pour les données suivantes : {data.tail()}")
            return None

        return rsi.iloc[-1]

    except Exception as e:
        logging.error(f"Erreur lors du calcul du RSI : {e}")
        return None

def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    """Calcule le MACD et la ligne de signal."""
    try:
        if len(data) < long_window:
            raise ValueError("Pas assez de données pour calculer le MACD")

        short_ema = data['close'].ewm(span=short_window, adjust=False).mean()
        long_ema = data['close'].ewm(span=long_window, adjust=False).mean()
        macd = short_ema - long_ema
        signal = macd.ewm(span=signal_window, adjust=False).mean()

        return macd.iloc[-1], signal.iloc[-1]

    except Exception as e:
        logging.error(f"Erreur lors du calcul du MACD : {e}")
        return None, None

def calculate_all_indicators(exchange, symbols, timeframe='1d', period=14):
    """Calcule le RSI et MACD pour toutes les cryptos spécifiées."""
    results = {}
    logging.info("Chargement des informations sur les marchés...")
    
    try:
        markets = exchange.load_markets()
    except Exception as e:
        logging.error(f"Erreur lors du chargement des marchés : {e}")
        return {}

    for idx, symbol in enumerate(symbols):
        logging.info(f"{idx + 1}/{len(symbols)} : Analyse des indicateurs pour {symbol}")

        if symbol not in markets or not markets[symbol]['active']:
            logging.warning(f"{symbol} n'existe pas ou est désactivée sur l'exchange. Ignoré.")
            results[symbol] = {'error': 'Paire inexistante ou inactive'}
            continue

        df = fetch_ohlcv(exchange, symbol, timeframe, limit=max(period + 1, 26))
        if df is None or df.empty:
            results[symbol] = {'error': 'Impossible de récupérer les données'}
            continue

        if df['volume'].sum() == 0 or df['close'].nunique() == 1:
            logging.warning(f"Volume nul ou absence de variation pour {symbol}. Crypto ignorée.")
            results[symbol] = {'error': 'Volume nul ou pas de variation'}
            continue

        existing_data = load_rsi_data()
        last_timestamp = df['timestamp'].iloc[-1].isoformat()

        if symbol in existing_data and existing_data[symbol].get('timestamp') == last_timestamp:
            logging.info(f"RSI et MACD déjà calculés pour {symbol}, aucune mise à jour nécessaire.")
            results[symbol] = existing_data[symbol]
            continue

        rsi_value = calculate_rsi(df, period)
        if rsi_value is None:
            results[symbol] = {'error': 'RSI non calculé'}
            continue

        macd, signal = calculate_macd(df)
        if macd is None or signal is None:
            results[symbol] = {'error': 'MACD non calculé'}
            continue

        results[symbol] = {
            'timestamp': last_timestamp,
            'close': df['close'].iloc[-1],
            'RSI': rsi_value,
            'MACD': macd,
            'MACD_Signal': signal
        }

    return results

def save_rsi_data(data):
    """Sauvegarde les données RSI/MACD dans un fichier JSON."""
    try:
        with open(RSI_FILE, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info("Données RSI/MACD sauvegardées avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des données RSI/MACD : {e}")

def load_rsi_data():
    """Charge les données RSI/MACD depuis un fichier JSON."""
    if os.path.exists(RSI_FILE):
        try:
            with open(RSI_FILE, 'r') as file:
                return json.load(file)
        except Exception as e:
            logging.error(f"Erreur lors du chargement des données RSI/MACD : {e}")
    return {}
