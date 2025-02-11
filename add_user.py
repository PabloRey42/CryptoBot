import requests
import json
import time

# 🔹 URL de l'API
BASE_URL = "https://bot.crypteau.fr:5000"

# 🔹 Cryptos disponibles
CRYPTO_LIST = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]

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

# 🔹 Menu interactif
def main():
    print("\n🎉 Bienvenue dans le script de création d'utilisateur 🎉\n")

    # 1️⃣ Demander un email et un mot de passe
    email = input("📧 Entrez l'email du nouvel utilisateur : ").strip()
    password = input("🔒 Entrez le mot de passe : ").strip()

    # 2️⃣ Inscription
    if not register_user(email, password):
        return

    # 3️⃣ Connexion pour récupérer le token
    time.sleep(2)  # Pause pour éviter les erreurs de propagation
    token = login_user(email, password)
    if not token:
        return

    # 4️⃣ Ajouter des cryptos
    print("\n📊 Cryptos disponibles :")
    for i, crypto in enumerate(CRYPTO_LIST, 1):
        print(f"{i}. {crypto}")

    chosen_cryptos = []
    while True:
        choice = input("\n✅ Sélectionnez une crypto (1-5) ou appuyez sur Entrée pour terminer : ").strip()
        if choice == "":
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(CRYPTO_LIST):
            crypto = CRYPTO_LIST[int(choice) - 1]
            if crypto not in chosen_cryptos:
                chosen_cryptos.append(crypto)
                print(f"✔️ {crypto} ajoutée à votre liste.")
            else:
                print(f"⚠️ {crypto} est déjà sélectionnée.")
        else:
            print("❌ Sélection invalide, essayez encore.")

    # 5️⃣ Ajouter les cryptos choisies
    for crypto in chosen_cryptos:
        add_crypto_to_user(token, crypto)
        time.sleep(1)

    print(f"\n🎉 Utilisateur {email} complètement créé avec les cryptos sélectionnées !")

if __name__ == "__main__":
    main()
