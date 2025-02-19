import re
from typing import Dict, List

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

def extract_data(extracted_data: Dict, patterns: Dict) -> Dict:
    """Extrait les données structurées du texte et des tables"""
    text = extracted_data['text']

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

    # Extraction des articles et des totaux
    extracted = extract_articles_and_totals(text)
    articles = extracted['articles']
    totals = extracted['totals']

    # Extraction des totaux
    total_pattern = {
        'total_tva': r'TVA\s*:?\s*([\d\s,]+)\s*€',
        'total_ttc': r'Total TTC\s*:?\s*([\d\s,]+)\s*€',
        'acompte': r'Acompte.*?HT\s*([\d\s,]+)\s*€'  # Pattern simplifié
    }

    totaux = {}
    for key, pattern in total_pattern.items():
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1)
            totaux[key] = convert_to_float(value)

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

    # Extraction du type de règlement (amélioration du pattern)
    reglement_pattern = r'(?:Règlement|Mode de règlement)\s*:?\s*([^\n]+)'
    reglement = "non renseigné"  # Valeur par défaut
    match = re.search(reglement_pattern, text, re.IGNORECASE)
    if match:
        reglement = match.group(1).strip().lower()
        # Normalisation du terme "chèque"
        if "cheque" in reglement or "chèque" in reglement:
            reglement = "cheque"

    # Extraction de la catégorie de vente
    categorie_pattern = r'Catégorie de vente\s*:?\s*([^\n]+)'
    categorie_vente = ""
    match = re.search(categorie_pattern, text, re.IGNORECASE)
    if match:
        categorie_vente = match.group(1).strip()

    # Extraction du commentaire
    commentaire_pattern = r'Commentaire\s*:?\s*([^\n]+)'
    commentaire = ""
    match = re.search(commentaire_pattern, text, re.IGNORECASE)
    if match:
        commentaire = match.group(1).strip()

    # Extraction du statut de paiement
    statut_pattern = r'Statut(?:\s+de)?\s+paiement\s*:?\s*([^\n]+)'
    statut_paiement = ""
    match = re.search(statut_pattern, text, re.IGNORECASE)
    if match:
        statut_paiement = match.group(1).strip()

    # Extraction des articles depuis le texte
    articles = extract_articles_from_text(text)

    # Construction du résultat final
    data = {
        'type_facture': type_facture,
        'numero_facture': numero_facture,
        'date_facture': date_facture,
        'numero_client': numero_client,
        'nom_client': nom_client,
        'reglement': reglement,
        'categorie_vente': categorie_vente,
        'commentaire': commentaire,
        'statut_paiement': statut_paiement,
        'TOTAL': {
            'total_ht': totals.get('total_ht', 0.0),
            'tva': totaux['total_tva'] if 'total_tva' in totaux else 0.0,
            'total_ttc': totaux['total_ttc'] if 'total_ttc' in totaux else 0.0,
            'acompte': totaux['acompte'] if 'acompte' in totaux else 0.0,
        },
        'detailTVA': detail_tva,
        'nombre_articles': len(articles),
        'articles': articles,
    }

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
