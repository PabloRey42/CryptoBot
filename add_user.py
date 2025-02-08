import psycopg2
import bcrypt

# Connexion à PostgreSQL
conn = psycopg2.connect(
    dbname="crypto_users",
    user="crypto_admin",
    password="7102Bdd*",
    host="localhost"
)
cursor = conn.cursor()

# Demande les informations de l'utilisateur
email = input("Email: ")
password = input("Mot de passe: ")

# Hacher le mot de passe avec bcrypt
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Ajouter l'utilisateur à la base de données
cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
conn.commit()

print("Utilisateur ajouté avec succès.")

# Fermer la connexion
cursor.close()
conn.close()
