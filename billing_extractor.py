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
            'frais_expedition': 0.0,
            'type_expedition': "" if invoice_type == 'internet' else None,
            'remise': ''  # Ajout du champ remise
        }

        if invoice_type == 'internet':
            # Patterns plus précis pour factures internet
            total_pattern = r'Total\s+([\d\s]+[,.]?\d*)\s*€\s*\(dont\s+([\d\s]+[,.]?\d*)\s*€\s*TVA\)'
            expedition_pattern = r'Expédition\s+(?:([^€\n]*?)(?:(\d+[,.]?\d*)\s*€)?)?\s*(?:\(TTC\))?\s*(?:via\s*)?([^\n]*?)(?=\s*(?:Total|$))'

            # Extraction total TTC et TVA
            total_match = re.search(total_pattern, text, re.IGNORECASE)
            if total_match:
                amounts['total_ttc'] = self.convert_to_float(total_match.group(1))
                amounts['tva'] = self.convert_to_float(total_match.group(2))
                amounts['total_ht'] = amounts['total_ttc'] - amounts['tva']

            # Extraction frais et type d'expédition
            expedition_match = re.search(expedition_pattern, text, re.IGNORECASE)
            if expedition_match:
                if expedition_match.group(2):  # Si on a un montant
                    amounts['frais_expedition'] = self.convert_to_float(expedition_match.group(2))
                # Combine les parties du type d'expédition (avant et après le montant)
                type_expedition = ' '.join(filter(None, [
                    expedition_match.group(1),
                    expedition_match.group(3)
                ])).strip()
                if type_expedition:
                    amounts['type_expedition'] = type_expedition

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

        # Recherche d'une remise totale
        remise_pattern = r'Remise\s+(?:totale|globale)?\s*:?\s*(\d+[.,]?\d*)\s*[€%]'
        remise_match = re.search(remise_pattern, text, re.IGNORECASE)
        if remise_match:
            amounts['remise'] = self.convert_to_float(remise_match.group(1))

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
            code_pattern = r'UGS\s*:\s*([^\n]+)'
            current_code = ""

            # Ignore les lignes qui commencent par ces mots
            ignore_starts = ['UGS', 'Poids', 'Taille', 'Colori', 'Total', 'Sous-total', 'Expédition', 'En cas']

            for line in text.split('\n'):
                line = line.strip()

                # Ignore les lignes vides ou commençant par des mots à ignorer
                if not line or any(line.startswith(word) for word in ignore_starts):
                    if 'UGS' in line:
                        # Extraction du code UGS
                        match = re.search(code_pattern, line)
                        if match:
                            current_code = match.group(1).strip()
                    continue

                # Cherche un nombre (quantité) et un prix dans la ligne
                quantite_match = re.search(r'\s(\d+)\s+(\d+[,.]?\d*)\s*€', line)

                if quantite_match:
                    try:
                        description = line[:quantite_match.start()].strip()
                        quantite = int(quantite_match.group(1))
                        prix_unitaire = self.convert_to_float(quantite_match.group(2))

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
            'Réseau_Vente': "",  # Renommé de categorie_vente à Réseau_Vente
            'Type_Vente': "",  # Renommé de type_vente à Type_Vente
            'commentaire': "",
            'statut_paiement': "Payé" if invoice_type == 'internet' else "",
            'reglement': "carte bancaire" if invoice_type == 'internet' else "",
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
            'Réseau_Vente': r'20\.(?:0[1-9]|10)\.\d{2}',  # Pattern pour 20.XX.XX complet
            'Type_Vente': r'20\.(?:0[1-9]|10)',  # Pattern pour 20.XX uniquement
            'commentaire': r'Commentaire\s*:\s*([^\n]+)',
            'statut_paiement': r'Statut paiement\s*:\s*([^\n]+)',
            'reglement': r'Règlement\s*:?\s*([^\n]+)' if invoice_type == 'meg' else None
        }

        # Extraction des informations de base
        for key, pattern in patterns.items():
            if pattern:
                if key in ['Réseau_Vente', 'Type_Vente']:
                    # Recherche dans tout le texte
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        data[key] = match.group(0)
                else:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
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
