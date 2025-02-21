# Image de base Python
FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers requirements
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création du dossier pour les fichiers temporaires
RUN mkdir -p temp_files && chmod 777 temp_files

# Exposition des ports
EXPOSE 8000 8501

# Script de démarrage
COPY start.sh .
RUN chmod +x start.sh

# Commande de démarrage
CMD ["./start.sh"]
