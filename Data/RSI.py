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
    if len(data) < period:
        raise ValueError("Pas assez de données pour calculer le RSI")

    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1] if not rsi.isna().iloc[-1] else None


def calculate_all_rsi(exchange, symbols, timeframe='5m', period=14):
    results = {}
    for idx, symbol in enumerate(symbols):
        print(f"{idx + 1}/{len(symbols)} : Calcul du RSI pour {symbol}")
        try:
            df = fetch_ohlcv(exchange, symbol, timeframe, limit=period + 1)
            if len(df) < period + 1:
                raise ValueError(f"Pas assez de données pour {symbol}")

            df['RSI'] = calculate_rsi(df, period)
            results[symbol] = {
                'timestamp': pd.to_datetime(df['timestamp'].iloc[-1], unit='ms').isoformat(),
                'close': df['close'].iloc[-1],
                'RSI': df['RSI'].iloc[-1]  
}
        except Exception as e:
            print(f"Erreur pour {symbol} : {e}")
            results[symbol] = {'error': str(e)}
    return results

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
