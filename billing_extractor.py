import re
from datetime import datetime
from typing import Dict, List

class InvoiceExtractor:
    def __init__(self):
        """
        Initialise l'extracteur
        """
        pass  # Plus besoin des credentials Google Cloud

    def extract_amounts(self, text: str, invoice_type: str) -> Dict:
        """
        Extrait les montants selon le type de facture
        """
        amounts = {
            'total_ttc': 0.0,
            'total_ht': 0.0,
            'tva': 0.0,
            'frais_expedition': 0.0
        }

        if invoice_type == 'internet':
            # Patterns plus précis pour factures internet
            sous_total_pattern = r'Sous-total\s+([\d\s]+[,.]?\d*)\s*€'
            total_pattern = r'Total\s+([\d\s]+[,.]?\d*)\s*€\s*\(dont\s+([\d\s]+[,.]?\d*)\s*€\s*TVA\)'
            expedition_pattern = r'Expédition\s+([^€\n]*?)(?:(\d+[,.]?\d*)\s*€)?(?:\s*\(TTC\)|\s*$)'

            # Extraction du sous-total
            sous_total_match = re.search(sous_total_pattern, text, re.IGNORECASE)
            if sous_total_match:
                amounts['total_ht'] = self.convert_to_float(sous_total_match.group(1))

            # Extraction total TTC et TVA
            total_match = re.search(total_pattern, text, re.IGNORECASE)
            if total_match:
                amounts['total_ttc'] = self.convert_to_float(total_match.group(1))
                amounts['tva'] = self.convert_to_float(total_match.group(2))

            # Extraction frais d'expédition
            expedition_match = re.search(expedition_pattern, text, re.IGNORECASE)
            if expedition_match and expedition_match.group(2):
                amounts['frais_expedition'] = self.convert_to_float(expedition_match.group(2))

        elif invoice_type == 'meg':
            # Patterns pour facture MEG
            total_ht_pattern = r'Total HT\s+([\d\s]+[,.]?\d*)\s*€'
            tva_pattern = r'TVA\s+([\d\s]+[,.]?\d*)\s*€'
            total_ttc_pattern = r'Total TTC\s+([\d\s]+[,.]?\d*)\s*€'
            acompte_pattern = r'Acompte\(s\) reçu\(s\) HT\s+([\d\s]+[,.]?\d*)\s*€'

            # Extraction total HT
            total_ht_match = re.search(total_ht_pattern, text)
            if total_ht_match:
                amounts['total_ht'] = self.convert_to_float(total_ht_match.group(1))

            # Extraction TVA
            tva_match = re.search(tva_pattern, text)
            if tva_match:
                amounts['tva'] = self.convert_to_float(tva_match.group(1))

            # Extraction total TTC
            total_ttc_match = re.search(total_ttc_pattern, text)
            if total_ttc_match:
                amounts['total_ttc'] = self.convert_to_float(total_ttc_match.group(1))

            # Extraction acompte
            acompte_match = re.search(acompte_pattern, text)
            if acompte_match:
                amounts['acompte'] = self.convert_to_float(acompte_match.group(1))

        return amounts

    def convert_to_float(self, amount_str: str) -> float:
        """
        Convertit une chaîne de montant en float
        """
        return float(amount_str.replace(',', '.').replace(' ', ''))

    def detect_invoice_type(self, text: str) -> str:
        """
        Détecte le type de facture basé sur son contenu
        UGS en majuscule indique une facture internet
        Sinon c'est une facture MEG
        """
        # Recherche plus précise pour les factures internet
        internet_indicators = [
            "UGS",
            "N° de commande",
            "Date de commande",
            "Livraison gratuite"
        ]

        if any(indicator in text for indicator in internet_indicators):
            return "internet"
        return "meg"

    def extract_articles(self, text: str, invoice_type: str) -> List[Dict]:
        """
        Extrait les articles selon le type de facture
        """
        articles = []

        if invoice_type == 'internet':
            # Pattern simplifié pour articles internet
            # Capture la ligne entière et extrait les nombres ensuite
            article_pattern = r'([^\n]+?)(?:\n|$)'
            code_pattern = r'UGS\s*:\s*([^\n]+)'

            current_code = ""
            for line in text.split('\n'):
                if 'UGS' in line:
                    # Extraction du code UGS
                    match = re.search(code_pattern, line)
                    if match:
                        current_code = match.group(1).strip()
                    continue

                # Ignore les lignes non pertinentes
                if any(x in line for x in ['Poids', 'Taille', 'Colori', 'Total', 'Sous-total', 'Expédition']):
                    continue

                # Cherche un nombre (quantité) et un prix dans la ligne
                quantite_match = re.search(r'\b(\d+)\b', line)
                prix_match = re.search(r'(\d+[,.]?\d*)\s*€', line)

                if quantite_match and prix_match:
                    try:
                        description = line[:quantite_match.start()].strip()
                        quantite = int(quantite_match.group(1))
                        prix_unitaire = self.convert_to_float(prix_match.group(1))

                        articles.append({
                            'reference': current_code,
                            'description': description,
                            'quantite': quantite,
                            'prix_unitaire': prix_unitaire,
                            'montant_ht': 0.0,  # Par défaut
                            'tva': 0.0,         # Par défaut
                            'remise': 0.0       # Par défaut
                        })
                        current_code = ""  # Réinitialise le code pour le prochain article
                    except (ValueError, IndexError) as e:
                        print(f"Erreur lors de l'extraction d'un article internet: {e}")
                        continue

        elif invoice_type == 'meg':
            # Pattern pour les articles MEG (code existant)
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
                        'tva': float(match.group(7).replace(',', '.'))
                    })
                except (IndexError, ValueError) as e:
                    print(f"Erreur lors de l'extraction d'un article MEG: {e}")
                    continue

        return articles

    def extract_invoice_data(self, text: str) -> Dict:
        """
        Extrait les données structurées du texte de la facture
        """
        # Détection du type de facture
        invoice_type = self.detect_invoice_type(text)

        # Structure de base des données
        data = {
            'type': invoice_type,
            'articles': [],
            'nombre_articles': 0,
            'TOTAL': {
                'total_ttc': 0.0,
                'total_ht': 0.0,
                'tva': 0.0,
                'frais_expedition': 0.0
            },
            'categorie_vente': "",
            'commentaire': "",
            'statut_paiement': "",
            'reglement': "carte bancaire" if invoice_type == 'internet' else "",  # Valeur par défaut pour internet
            'numero_client': "",
            'client_name': ""
        }

        # Patterns adaptés selon le type de facture
        patterns = {
            'numero_facture': (
                r'N° de commande\s*:\s*(\d+)' if invoice_type == 'internet'
                else r'N°\s*:\s*([A-Z0-9-]+)'
            ),
            'date': (
                r'Date de commande\s*:\s*(\d{2}/\d{2}/\d{4})' if invoice_type == 'internet'
                else r'Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})'
            ),
            'numero_client': r'N°\s*client\s*:\s*(CLT\d+)',
            'client_name': (
                r'FACTURE\s+([^\n]+?)\s+N° de commande' if invoice_type == 'internet'
                else r'(?:N°\s*client\s*:[^\n]+\n)(?:(?:Monsieur|Madame|M\.|Mme\.)\s*)?([A-Za-zÀ-ÿ\s\-\']+?)(?:\n|$)'
            ),
            'categorie_vente': r'Catégorie de vente\s*:\s*([^\n]+)',
            'commentaire': r'Commentaire\s*:\s*([^\n]+)',
            'statut_paiement': r'Statut paiement\s*:\s*([^\n]+)',
            'reglement': r'Règlement\s*:?\s*([^\n]+)' if invoice_type == 'meg' else None  # Pattern uniquement pour MEG
        }

        # Extraction des informations de base
        for key, pattern in patterns.items():
            if pattern:  # Vérifie si le pattern existe (pour éviter d'extraire le règlement des factures internet)
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Normalisation du règlement uniquement pour MEG
                    if key == 'reglement' and invoice_type == 'meg' and ('cheque' in value.lower() or 'chèque' in value.lower()):
                        value = 'cheque'
                    data[key] = value

        # Extraction des articles
        articles = self.extract_articles(text, invoice_type)
        data['articles'] = articles
        data['nombre_articles'] = len(articles)

        # Extraction des montants
        amounts = self.extract_amounts(text, invoice_type)
        data['TOTAL'].update(amounts)

        # Formatage de la date
        if 'date' in data:
            try:
                date_obj = datetime.strptime(data['date'], '%d/%m/%Y')
                data['date'] = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    date_obj = datetime.strptime(data['date'], '%d-%m-%Y')
                    data['date'] = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass

        return {
            "invoice_data": data,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # ... rest of the existing code ...
