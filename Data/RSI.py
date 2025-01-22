import ccxt
import pandas as pd
import json
import os

RSI_FILE = "saves/rsi_data.json"

def fetch_ohlcv(exchange, symbol, timeframe='5m', limit=100):
    """Récupère les données OHLCV pour une crypto donnée."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_rsi(data, period=14):
    """Calcule le RSI à partir des prix de clôture."""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_all_rsi(exchange, symbols):
    rsi_data = {}
    for symbol in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=14)
            if len(ohlcv) < 14:
                print(f"Pas assez de données pour {symbol}")
                continue
            close_prices = [candle[4] for candle in ohlcv]
            rsi = calculate_rsi(close_prices)
            if rsi is not None and not (rsi != rsi):
                rsi_data[symbol] = {
                    "RSI": rsi,
                    "close": close_prices[-1],
                    "timestamp": exchange.iso8601(ohlcv[-1][0])
                }
        except Exception as e:
            print(f"Erreur lors du calcul du RSI pour {symbol}: {e}")
    return rsi_data

def save_rsi_data(data):
    """Sauvegarde les données RSI dans un fichier JSON."""
    with open(RSI_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def load_rsi_data():
    """Charge les données RSI depuis un fichier JSON."""
    if os.path.exists(RSI_FILE):
        with open(RSI_FILE, 'r') as file:
            return json.load(file)
    return {}
