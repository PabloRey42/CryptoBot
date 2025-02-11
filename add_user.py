import requests
import json
import random
import time

# 🔹 URL de l'API
BASE_URL = "https://bot.crypteau.fr:5000"

# 🔹 Cryptos disponibles
CRYPTO_LIST = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]

# 🔹 Générer un email et mot de passe aléatoire
def generate_random_user():
    random_id = random.randint(1000, 9999)
    email = f"testuser{random_id}@crypteau.fr"
    password = "TestPassword123!"
    return email, password

# 🔹 Inscription d'un utilisateur
def register_user(email, password):
    url = f"{BASE_URL}/register"
    payload = {"email": email, "password": password}
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Utilisateur {email} créé avec succès !")
        return True
    else:
        print(f"❌ Erreur lors de l'inscription : {response.json()}")
        return False

# 🔹 Connexion pour récupérer le token JWT
def login_user(email, password):
    url = f"{BASE_URL}/login"
    payload = {"email": email, "password": password}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        token = response.cookies.get("token")
        print(f"🔑 Token JWT récupéré pour {email}")
        return token
    else:
        print(f"❌ Erreur de connexion : {response.json()}")
        return None

# 🔹 Ajouter une crypto au profil
def add_crypto_to_user(token, crypto):
    url = f"{BASE_URL}/profile/cryptos/add"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"crypto": crypto}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print(f"✅ Crypto {crypto} ajoutée avec succès !")
    else:
        print(f"❌ Erreur lors de l'ajout de la crypto : {response.json()}")

# 🔹 Script principal
def main():
    email, password = generate_random_user()

    # 1️⃣ Inscription
    if not register_user(email, password):
        return

    # 2️⃣ Connexion pour récupérer le token
    time.sleep(2)  # Pause pour éviter les erreurs de propagation
    token = login_user(email, password)
    if not token:
        return

    # 3️⃣ Ajouter des cryptos à l'utilisateur
    for crypto in random.sample(CRYPTO_LIST, 3):  # Ajoute 3 cryptos aléatoires
        add_crypto_to_user(token, crypto)
        time.sleep(1)

    print(f"🎉 Utilisateur {email} complètement créé avec des cryptos !")

if __name__ == "__main__":
    main()
