import json
import os
import time
from pymongo import MongoClient

# Configuration via variables d'environnement
# C'est la bonne pratique Docker : on ne code pas les adresses en dur,
# on les récupère de l'environnement (défini dans docker-compose).
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
JSON_FILE_PATH = "/data/dataset.json"

def wait_for_mongo():
    """Tente de se connecter à Mongo plusieurs fois avant d'abandonner."""
    client = None
    for i in range(30):
        try:
            client = MongoClient(f"mongodb://{MONGO_HOST}:27017/")
            # Test simple pour voir si le serveur répond
            client.admin.command('ping')
            print("✅ Connexion à MongoDB réussie !")
            return client
        except Exception as e:
            print(f"⏳ En attente de MongoDB ({i}/30)...")
            time.sleep(2)
    raise Exception("Impossible de se connecter à MongoDB après 60 secondes.")

def load_data():
    client = wait_for_mongo()
    db = client["marmiton_db"]
    collection = db["recipes"]

    # 1. Lire le fichier JSON
    # Le fichier sera "monté" via Docker, le script le voit comme un fichier local.
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ Erreur : Le fichier {JSON_FILE_PATH} est introuvable.")
        return

    print(f"📖 Lecture du fichier {JSON_FILE_PATH}...")
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("❌ Erreur : Le format JSON attendu est une liste de recettes.")
        return

    print(f"📦 {len(data)} recettes trouvées.")

    # 2. Insérer dans Mongo
    # Stratégie simple : On vide la collection existante pour éviter les doublons lors des re-launch
    # Pour un système de prod, on ferait des "upserts" (mise à jour si existe, ajout sinon).
    count_before = collection.count_documents({})
    if count_before > 0:
        print(f"⚠️ Nettoyage de la base existante ({count_before} documents)...")
        collection.delete_many({})
    
    # insert_many est beaucoup plus rapide que d'insérer une par une
    if data:
        collection.insert_many(data)
        print(f"✅ {len(data)} recettes importées avec succès dans MongoDB !")
    else:
        print("⚠️ Aucune donnée à importer.")

    client.close()

if __name__ == "__main__":
    load_data()
