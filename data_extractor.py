import re
from typing import Dict, List
from datetime import datetime

def convert_to_float(value: str) -> float:
    """Convertit une chaîne en float en gérant les formats français"""
    try:
        clean_value = value.replace('€', '').replace(' ', '').strip()
        clean_value = clean_value.replace(',', '.')
        return float(clean_value)
    except (ValueError, AttributeError):
        return 0.0

def extract_articles_and_totals(text: str) -> Dict:
    """Extrait les articles et les totaux du texte"""
    articles = []
    totals = {}

    # Pattern pour les articles sous "Libellé"
    article_pattern = (
        r'ART(\d+)\s*-\s*([^\n]+?)\s*'  # Référence et description
        r'(\d+,\d+)\s*'                 # Quantité
        r'(\d+[\s\d]*,\d+)\s*€\s*'      # Prix unitaire
        r'(\d+,\d+)%\s*'                # Remise
        r'(\d+[\s\d]*,\d+)\s*€\s*'      # Montant HT
        r'(\d+,\d+)%'                   # TVA
    )

    for match in re.finditer(article_pattern, text, re.MULTILINE | re.DOTALL):
        try:
            prix_unitaire = match.group(4).replace(' ', '')
            montant_ht = match.group(6).replace(' ', '')

            articles.append({
                'reference': f"ART{match.group(1)}",
                'description': match.group(2).strip(),
                'quantite': float(match.group(3).replace(',', '.')),
                'prix_unitaire': float(prix_unitaire.replace(',', '.')),
                'remise': float(match.group(5).replace(',', '.')) / 100,
                'montant_ht': float(montant_ht.replace(',', '.')),
                'tva': float(match.group(7).replace(',', '.'))  # Déjà en pourcentage
            })
        except (IndexError, ValueError) as e:
            print(f"Erreur lors de l'extraction d'un article: {e}")
            continue

    # Pattern pour les totaux
    total_pattern = r'Total HT\s*([\d\s,]+)\s*€'
    for match in re.finditer(total_pattern, text, re.MULTILINE):
        try:
            total_ht = match.group(1).replace(' ', '')
            totals['total_ht'] = float(total_ht.replace(',', '.'))
        except (IndexError, ValueError) as e:
            print(f"Erreur lors de l'extraction du total HT: {e}")
            continue

    return {'articles': articles, 'totals': totals}

def extract_articles_from_text(text: str) -> List[Dict]:
    """Extrait les articles à partir du texte de la table"""
    articles = []

    # Pattern modifié pour accepter les chiffres dans la description
    article_pattern = (
        r'ART(\d+)\s*-\s*([^€]+?)\s+'    # Référence et description (accepte tout sauf €)
        r'(\d+,\d+)\s+'                  # Quantité
        r'(\d+[\s\d]*,\d+)\s*€\s+'       # Prix unitaire
        r'(\d+,\d+)%\s+'                 # Remise
        r'(\d+[\s\d]*,\d+)\s*€\s+'       # Montant HT
        r'(\d+,\d+)%'                    # TVA
    )

    for match in re.finditer(article_pattern, text, re.MULTILINE | re.DOTALL):
        try:
            # Nettoyage des espaces dans les nombres
            prix_unitaire = match.group(4).replace(' ', '')
            montant_ht = match.group(6).replace(' ', '')

            articles.append({
                'reference': f"ART{match.group(1)}",
                'description': match.group(2).strip(),
                'quantite': float(match.group(3).replace(',', '.')),
                'prix_unitaire': float(prix_unitaire.replace(',', '.')),
                'remise': float(match.group(5).replace(',', '.')) / 100,
                'montant_ht': float(montant_ht.replace(',', '.')),
                'tva': float(match.group(7).replace(',', '.'))  # Déjà en pourcentage
            })
        except (IndexError, ValueError) as e:
            print(f"Erreur lors de l'extraction d'un article: {e}")
            continue

    return articles

def extract_data(text: str, type: str = 'meg') -> dict:
    """Extrait les données structurées du texte selon le type de facture"""
    data = {
        'type': type,
        'articles': [],
        'TOTAL': {},
        'acomptes': {}
    }

    try:
        if type == 'meg':
            # Extraire les informations d'acompte
            acompte_match = re.search(r'Echéance\(s\)\s*Acompte\s*de\s*(\d+[\s\d]*,\d+)\s*€\s*au\s*(\d{2}/\d{2}/\d{4})', text)
            if acompte_match:
                montant_acompte = float(acompte_match.group(1).replace(' ', '').replace(',', '.'))
                date_acompte = acompte_match.group(2)
                # Convertir la date au format YYYY-MM-DD
                jour, mois, annee = date_acompte.split('/')
                date_acompte_iso = f"{annee}-{mois}-{jour}"

                data['acomptes'].update({
                    'montant': montant_acompte,
                    'date': date_acompte_iso
                })

            # Extraire le taux de TVA du détail TVA
            tva_match = re.search(r'Détail de la TVA.*?(\d{1,2}[,.]\d{2})%', text, re.DOTALL)
            taux_tva = float(tva_match.group(1).replace(',', '.')) if tva_match else None

            # Extraire les autres données MEG...
            # ... (code existant pour MEG)

            # Ajouter le taux de TVA aux articles
            for article in data['articles']:
                article['tva'] = taux_tva

        else:  # Internet
            # Extraire total HT et TTC pour calculer le taux de TVA
            total_ht_match = re.search(r'Sous-total\s+(\d+[,.]\d{2})\s*€', text)
            total_ttc_match = re.search(r'Total\s+(\d+[,.]\d{2})\s*€\s*\(dont\s+(\d+[,.]\d{2})\s*€\s*TVA\)', text)

            if total_ht_match and total_ttc_match:
                total_ht = float(total_ht_match.group(1).replace(',', '.'))
                total_ttc = float(total_ttc_match.group(1).replace(',', '.'))

                # Calculer le taux de TVA
                if total_ht > 0:
                    taux_tva = ((total_ttc / total_ht) - 1) * 100
                else:
                    taux_tva = 0

                # Ajouter aux données
                data['TOTAL'].update({
                    'total_ht': total_ht,
                    'total_ttc': total_ttc,
                    'taux_tva': round(taux_tva, 2)
                })

            # Extraire les autres données Internet...
            # ... (code existant pour Internet)

    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des données: {str(e)}")
        raise

    return data

def extract_articles(text: str, is_meg: bool) -> List[Dict]:
    """Extrait les articles du texte"""
    articles = []
    if is_meg:
        # Pattern pour les articles MEG basé sur le format tabulaire exact
        article_pattern = (
            r'ART(\d+)\s*-\s*([^\n]+?)\s*'  # Référence et description
            r'(\d+,\d+)\s*'                 # Quantité
            r'(\d+[\s\d]*,\d+)\s*€\s*'      # Prix unitaire
            r'(\d+,\d+)%\s*'                # Remise
            r'(\d+[\s\d]*,\d+)\s*€\s*'      # Montant HT
            r'(\d+,\d+)%'                   # TVA
        )

        for match in re.finditer(article_pattern, text, re.MULTILINE | re.DOTALL):
            try:
                # Nettoyage des espaces dans les nombres
                prix_unitaire = match.group(4).replace(' ', '')
                montant_ht = match.group(6).replace(' ', '')

                articles.append({
                    'reference': f"ART{match.group(1)}",
                    'description': match.group(2).strip(),
                    'quantite': float(match.group(3).replace(',', '.')),
                    'prix_unitaire': float(prix_unitaire.replace(',', '.')),
                    'remise': float(match.group(5).replace(',', '.')) / 100,
                    'montant_ht': float(montant_ht.replace(',', '.')),
                    'tva': float(match.group(7).replace(',', '.'))  # Déjà en pourcentage
                })
            except (IndexError, ValueError) as e:
                print(f"Erreur lors de l'extraction d'un article MEG: {e}")
                continue
    else:
        # Pattern pour les articles internet (inchangé)
        article_pattern = r'([A-Za-z0-9-]+(?:[^\n]+)?)\nUGS\s*:\s*([^\n]+)\n'
        for match in re.finditer(article_pattern, text, re.MULTILINE):
            try:
                articles.append({
                    'reference': match.group(2).strip(),
                    'description': match.group(1).strip(),
                    'quantite': 1,
                    'prix_unitaire': 0,
                    'remise': 0,
                    'montant_ht': 0,
                    'tva': 20.0
                })
            except (IndexError, ValueError) as e:
                print(f"Erreur lors de l'extraction d'un article: {e}")
                continue
    return articles
