import re
from typing import Dict

def convert_to_float(value: str) -> float:
    """Convertit une chaîne en float en gérant les formats français"""
    try:
        clean_value = value.replace('€', '').replace(' ', '').strip()
        clean_value = clean_value.replace(',', '.')
        return float(clean_value)
    except (ValueError, AttributeError):
        return 0.0

def extract_data(text: str, patterns: Dict) -> Dict:
    """Extrait les données structurées du texte"""

    # Extraction du type de facture (format 20.XX)
    type_facture_pattern = r'(?:^|\n)(?:20\.(?:0[1-9]|[1-9]\d))\b'
    type_facture = "type facture non renseigné"  # Valeur par défaut
    match = re.search(type_facture_pattern, text)
    if match:
        type_facture = match.group(0).strip()

    # Extraction des informations d'en-tête
    numero_pattern = r'N°\s*:\s*(FAC\d+)'
    date_pattern = r'Date\s*:\s*(\d{2}/\d{2}/\d{4})'
    client_pattern = r'N°\s*client\s*:\s*(CLT\d+)'

    # Pattern flexible pour le nom du client
    nom_client_pattern = r'(?:Monsieur|Madame|M\.|Mme\.)\s*([A-Za-zÀ-ÿ\s\-\']+?)(?:\n|$)|N°\s*client.*\n([A-Za-zÀ-ÿ\s\-\']+?)(?:\n|$)|N°\s*TVA.*\n([A-Z\s]+)(?:\n|$)'
    # Pattern alternatif pour chercher des noms ailleurs dans le document
    nom_alternatif_pattern = r'(?:[A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+)+)|(?:[A-Z]{2,}(?:\s+[A-Z][a-zÀ-ÿ]+)+)|(?:CITY\s+SURF)'

    numero_facture = ""
    date_facture = ""
    numero_client = ""
    nom_client = ""

    match = re.search(numero_pattern, text)
    if match:
        numero_facture = match.group(1)

    match = re.search(date_pattern, text)
    if match:
        date_facture = match.group(1)

    match = re.search(client_pattern, text)
    if match:
        numero_client = match.group(1)

    match = re.search(nom_client_pattern, text, re.MULTILINE)
    if match:
        # Prend le premier groupe non vide (avec ou sans civilité ou TVA)
        nom_client = (match.group(1) or match.group(2) or match.group(3)).strip()

    # Si le nom n'est pas trouvé ou contient des mots-clés à éviter ou contient "inconnu", cherche ailleurs
    mots_a_eviter = ["NOMADS", "SURFING", "TOTAL", "TTC", "TVA", "HT", "FACTURE", "CLIENT", "LIBELLÉ", "QTÉ", "MONTANT"]
    if (not nom_client or
        any(mot in nom_client.upper() for mot in mots_a_eviter) or
        "inconnu" in nom_client.lower()):
        matches = re.finditer(nom_alternatif_pattern, text, re.MULTILINE)
        for match in matches:
            potential_name = match.group(0).strip()
            # Évite les faux positifs
            if not any(mot in potential_name.upper() for mot in mots_a_eviter):
                nom_client = potential_name
                break

    # Pattern pour les articles dans le tableau
    article_pattern = r'([A-Za-z0-9-]+(?:[^\n]+)?)\nART(\d+)\s*-\n(\d+,\d+)\n(\d+,\d+)\s*€\n(\d+,\d+)%\n(\d+,\d+)\s*€\n(\d+,\d+)%'

    # Extraction des articles
    articles = []
    for match in re.finditer(article_pattern, text, re.MULTILINE):
        try:
            # Conversion des pourcentages en décimal (20% -> 0.20)
            remise = convert_to_float(match.group(5)) / 100
            tva = convert_to_float(match.group(7)) / 100

            articles.append({
                'reference': f"ART{match.group(2)}",
                'description': match.group(1).strip(),
                'quantite': convert_to_float(match.group(3)),
                'prix_unitaire': convert_to_float(match.group(4)),
                'remise': remise,
                'montant_ht': convert_to_float(match.group(6)),
                'tva': tva
            })
        except (IndexError, ValueError) as e:
            print(f"Erreur lors de l'extraction d'un article: {e}")
            continue

    # Extraction des totaux
    total_pattern = {
        'total_ht': r'Total HT\s*:?\s*([\d\s,]+)\s*€',
        'total_tva': r'TVA\s*:?\s*([\d\s,]+)\s*€',
        'total_ttc': r'Total TTC\s*:?\s*([\d\s,]+)\s*€'
    }

    totaux = {}
    for key, pattern in total_pattern.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            totaux[key] = convert_to_float(match.group(1))

    # Extraction du détail TVA
    detail_tva_pattern = r'(?P<type>Exonérée|Normale)\s*([\d,]+)\s*€\s*([\d,]+)%\s*([\d,]+)\s*€'
    detail_tva = []

    for match in re.finditer(detail_tva_pattern, text, re.MULTILINE):
        try:
            tva_type = "TVAexoneree" if match.group('type') == "Exonérée" else "TVAnormale"
            detail_tva.append({
                'type': tva_type,
                'base_ht': convert_to_float(match.group(2)),
                'taux': convert_to_float(match.group(3)),
                'montant': convert_to_float(match.group(4))
            })
        except (IndexError, ValueError) as e:
            print(f"Erreur lors de l'extraction du détail TVA: {e}")
            continue

    # Extraction du type de règlement
    reglement_pattern = r'Règlement\s*\n([^\n]+)'
    reglement = ""
    match = re.search(reglement_pattern, text)
    if match:
        reglement = match.group(1).strip()

    # Construction du résultat final
    data = {
        'type_facture': type_facture,
        'numero_facture': numero_facture,
        'date_facture': date_facture,
        'numero_client': numero_client,
        'nom_client': nom_client,
        'TOTAL': {
            'total_ht': totaux.get('total_ht', 0.0),
            'tva': totaux.get('total_tva', 0.0),
            'total_ttc': totaux.get('total_ttc', 0.0)
        },
        'nombre_articles': len(articles),
        'articles': articles,
        'detailTVA': detail_tva,
        'reglement': reglement
    }

    return data
