# On part d'une version légère de Python
FROM python:3.9-slim

# On définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie des dépendances et installation
# On fait ça AVANT de copier le code source pour profiter du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du script Python
COPY main.py .

# Commande par défaut au lancement du conteneur
CMD ["python", "main.py"]
