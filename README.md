# Nomads Surfing - Système de Traitement des Factures

Ce projet permet d'automatiser le traitement des factures pour Nomads Surfing en extrayant les données des fichiers PDF et en générant un fichier Excel récapitulatif.

## 🚀 Fonctionnalités

- Extraction des données depuis des factures PDF (MEG et Internet)
- Génération d'un fichier Excel avec un format standardisé
- Interface web avec Streamlit pour un traitement facile
- API FastAPI pour le traitement backend
- Gestion des dates au format MM/DD/YYYY
- Calcul automatique des remises et TVA

## 📁 Structure du Projet

## 🛠 Installation

1. Créer un environnement virtuel :

```bash
python -m venv nomads_facturation
source nomads_facturation/bin/activate  # Linux/Mac
# ou
.\nomads_facturation\Scripts\activate   # Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## 💻 Utilisation

### Via l'interface Streamlit (Recommandé)

1. Démarrer l'API FastAPI :
```bash
uvicorn app:app --reload
```

2. Lancer l'interface Streamlit :
```bash
streamlit run streamlit_app.py
```

3. Accéder à l'interface via votre navigateur et télécharger vos factures PDF

### En ligne de commande

Pour traiter des factures directement :
```bash
python main.py
```

## 📋 Format des Données

### Types de Factures Supportés

1. Factures MEG
   - Numéro de facture format : "FAC00000XXX"
   - Date format : "DD/MM/YYYY"

2. Factures Internet
   - Numéro de facture format : "YYYY-XXXXX"
   - Date format : "DD mois YYYY"

### Format Excel de Sortie

Le fichier Excel généré contient les colonnes suivantes :
- Type-facture
- n°ordre
- Syst (MEG/Internet)
- N° Syst. (numéro de facture)
- Client
- Dates (format MM/DD/YYYY)
- Montants (HT, TTC, TVA)
- Remises
- Articles (jusqu'à 20 articles par facture)

## 🔍 Fonctionnement Détaillé

1. **Extraction du PDF** (`pdf_extractor.py`)
   - Utilisation de pdfplumber pour l'extraction du texte brut
   - Détection du type de facture (MEG/Internet)
   - Préservation de la mise en page pour une meilleure extraction

2. **Traitement des Données** (`billing_extractor.py`)
   - Utilisation de regex optimisés pour l'extraction des informations
   - Patterns spécifiques selon le type de facture :
     * MEG : extraction via patterns fixes (numéro client, montants...)
     * Internet : patterns adaptés au format e-commerce
   - Gestion intelligente des cas particuliers :
     * Fallback sur numéro de commande si pas de numéro de facture
     * Conversion automatique des dates françaises
     * Calcul des remises et TVA

3. **Génération Excel** (`create_invoice_excel.py`)
   - Création du fichier avec le format standardisé Nomads
   - Formatage automatique des cellules
   - Gestion des articles multiples (jusqu'à 20)
   - Conversion des dates au format MM/DD/YYYY

## ⚠️ Notes Importantes

- Les dates sont automatiquement converties au format MM/DD/YYYY
- Les remises sont déduites du total HT
- Le système gère jusqu'à 20 articles par facture
- Les montants sont arrondis à 2 décimales

## 🤝 Contribution

Pour contribuer au projet :
1. Fork du repository
2. Création d'une branche pour votre fonctionnalité
3. Commit de vos changements
4. Push sur votre fork
5. Création d'une Pull Request

## 📝 License

Ce projet est la propriété de Nomads Surfing.
